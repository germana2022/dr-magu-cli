from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import get_close_matches
from pathlib import Path
from typing import Any

from dr_magu.commands.context import CommandContext
from dr_magu.commands.processor import CommandProcessor
from dr_magu.commands.registry import registry
from dr_magu.config import load_config
from dr_magu.result import ToolResult
from dr_magu.tui.models import TuiSettings
from dr_magu.sessions.manager import SessionManager
from dr_magu.scanner.models import RepositoryScan
from dr_magu.scanner.writers import write_latest_scan
from dr_magu.sessions.models import SessionMetadata
from dr_magu.tui_history import SessionCommandHistory



def _short_session_id(session_id: str) -> str:
    """Return a compact session label for terminal tables."""
    parts = session_id.split("-")
    if len(parts) >= 2 and len(parts[1]) == 6:
        return f"{parts[1][:2]}:{parts[1][2:4]}:{parts[1][4:6]}"
    return session_id[-8:]


def _format_command_count(command_count: int) -> str:
    """Return a readable command count label."""
    return "1 command" if command_count == 1 else f"{command_count} commands"


def _format_relative_time(timestamp: str, now: datetime | None = None) -> str:
    """Convert an ISO timestamp into a compact relative time label."""
    if not timestamp:
        return "unknown"
    current = now or datetime.now(timezone.utc)
    try:
        value = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return timestamp
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    delta = current - value.astimezone(timezone.utc)
    seconds = int(delta.total_seconds())
    if seconds < 0:
        return "just now"
    if seconds < 60:
        return "just now" if seconds < 5 else f"{seconds}s ago"
    minutes = seconds // 60
    if minutes < 60:
        return "1 min ago" if minutes == 1 else f"{minutes} min ago"
    hours = minutes // 60
    if hours < 24:
        return "1 hour ago" if hours == 1 else f"{hours} hours ago"
    days = hours // 24
    if days < 7:
        return "1 day ago" if days == 1 else f"{days} days ago"
    return value.strftime("%Y-%m-%d")


def _format_status(status: str) -> str:
    """Return an explicit status label that does not rely on color alone."""
    labels = {
        "active": "● Active",
        "closed": "○ Closed",
        "deleted": "× Deleted",
    }
    return labels.get(status, status)


def _format_duration_ms(duration_ms: object) -> str:
    """Return a compact duration label for workflow observability."""
    if duration_ms is None:
        return ""
    try:
        value = int(duration_ms)
    except (TypeError, ValueError):
        return str(duration_ms)
    if value < 1000:
        return f"{value} ms"
    return f"{value / 1000:.2f} s"


@dataclass(frozen=True)
class TuiSettings:
    """Settings used to start the Dr Magu Terminal UI."""

    workspace_path: str
    version: str = "1.1.4"


def _build_context(workspace_path: str) -> CommandContext:
    return CommandContext(
        workspace_path=workspace_path,
        output_format="human",
        config=load_config(),
    )


def run_tui(workspace_path: str) -> None:
    """Start the Textual Terminal UI.

    Textual is imported lazily so the non-TUI CLI remains lightweight and testable.
    """
    try:
        from textual.app import App, ComposeResult
        from textual.containers import Container, Horizontal, Vertical
        from textual.events import Key
        from textual.screen import ModalScreen
        from textual.widgets import Button, DataTable, Footer, Header, Input, Label, RichLog, Static
    except ModuleNotFoundError as exc:  # pragma: no cover - only triggered without optional runtime dependency
        missing = exc.name or "textual"
        raise RuntimeError(
            f"Missing dependency '{missing}'. Install the project with TUI dependencies: pip install -e ."
        ) from exc

    settings = TuiSettings(workspace_path=str(Path(workspace_path).resolve()))
    processor = CommandProcessor(registry)
    context = _build_context(settings.workspace_path)
    history = SessionCommandHistory()
    session_manager = SessionManager(settings.workspace_path)
    session_metadata = session_manager.get_or_start_current()

    class SessionManagerScreen(ModalScreen[SessionMetadata | None]):
        """Modal popup for managing persistent sessions from inside the TUI."""

        BINDINGS = [
            ("escape", "cancel", "Cancel"),
            ("a", "add_session", "Add"),
            ("d", "delete_session", "Delete"),
            ("enter", "resume_selected", "Resume"),
        ]

        CSS = """
        SessionManagerScreen {
            align: center middle;
        }

        #session-modal {
            width: 96;
            height: 30;
            border: round #38bdf8;
            background: #0f172a;
            padding: 1 2;
        }

        #session-title {
            color: #22d3ee;
            text-style: bold;
            margin-bottom: 0;
        }

        #session-hint {
            color: #94a3b8;
            margin-bottom: 1;
        }

        #session-search {
            height: 3;
            border: round #334155;
            background: #020617;
            color: #e2e8f0;
            margin-bottom: 1;
        }

        #session-table {
            height: 1fr;
            margin: 0 0 1 0;
        }

        #session-actions {
            height: 3;
            align-horizontal: center;
        }

        Button {
            margin: 0 1;
            min-width: 14;
        }

        #delete-session {
            margin-left: 4;
        }
        """

        def __init__(self, current_session_id: str) -> None:
            super().__init__()
            self.current_session_id = current_session_id
            self.search_text = ""

        def compose(self) -> ComposeResult:
            with Container(id="session-modal"):
                yield Static("Sessions", id="session-title")
                yield Static(
                    "Enter=Resume | A=Add new session | D=Soft delete selected | Esc=Close",
                    id="session-hint",
                )
                yield Input(placeholder="Search sessions by id or status...", id="session-search")
                table = DataTable(id="session-table")
                table.cursor_type = "row"
                yield table
                with Horizontal(id="session-actions"):
                    yield Button("▶ Resume", id="resume-session", variant="primary")
                    yield Button("＋ Add", id="add-session", variant="success")
                    yield Button("✖ Delete", id="delete-session", variant="error")
                    yield Button("↩ Cancel", id="cancel-session")

        def on_mount(self) -> None:
            self._load_table()
            self.query_one("#session-table", DataTable).focus()

        def on_input_changed(self, event: Input.Changed) -> None:
            if event.input.id != "session-search":
                return
            self.search_text = event.value.strip().lower()
            self._load_table()

        def _load_table(self) -> None:
            table = self.query_one("#session-table", DataTable)
            table.clear(columns=True)
            table.add_columns("", "Session", "Status", "History", "Updated", "Full ID")

            sessions = [metadata for metadata in session_manager.list() if self._matches_search(metadata)]
            for metadata in sessions:
                current_marker = "★" if metadata.id == self.current_session_id else ""
                table.add_row(
                    current_marker,
                    _short_session_id(metadata.id),
                    _format_status(metadata.status),
                    _format_command_count(metadata.command_count),
                    _format_relative_time(metadata.updated_at),
                    metadata.id,
                    key=metadata.id,
                )

        def _matches_search(self, metadata: SessionMetadata) -> bool:
            if not self.search_text:
                return True
            searchable = " ".join(
                [
                    metadata.id,
                    _short_session_id(metadata.id),
                    metadata.status,
                    str(metadata.command_count),
                    _format_relative_time(metadata.updated_at),
                ]
            ).lower()
            return self.search_text in searchable

        def _selected_session_id(self) -> str | None:
            table = self.query_one("#session-table", DataTable)
            if table.row_count == 0:
                return None
            key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
            return str(key.value) if key is not None else None

        def action_cancel(self) -> None:
            self.dismiss(None)

        def action_add_session(self) -> None:
            metadata = session_manager.start()
            self.dismiss(metadata)

        def action_resume_selected(self) -> None:
            session_id = self._selected_session_id()
            if not session_id:
                return
            try:
                metadata = session_manager.resume(session_id)
            except ValueError:
                return
            self.dismiss(metadata)

        def action_delete_session(self) -> None:
            session_id = self._selected_session_id()
            if not session_id:
                return
            session_manager.delete(session_id)
            if session_id == self.current_session_id:
                self.current_session_id = ""
            self._load_table()

        def on_button_pressed(self, event: Button.Pressed) -> None:
            if event.button.id == "resume-session":
                self.action_resume_selected()
            elif event.button.id == "add-session":
                self.action_add_session()
            elif event.button.id == "delete-session":
                self.action_delete_session()
            elif event.button.id == "cancel-session":
                self.action_cancel()

    class DrMaguTui(App):
        """OpenCode-inspired terminal interface for Dr Magu."""

        TITLE = "Dr Magu"
        SUB_TITLE = "AI Agent Platform"
        BINDINGS = [
            ("ctrl+c", "quit", "Quit"),
            ("ctrl+l", "clear_console", "Clear"),
            ("f1", "show_help", "Help"),
            ("f2", "show_commands", "Commands"),
            ("f3", "open_sessions", "Sessions"),
            ("f5", "show_status", "Status"),
        ]

        CSS = """
        Screen {
            background: #0b1020;
            color: #e6edf3;
        }

        Header {
            background: #111827;
            color: #93c5fd;
            text-style: bold;
        }

        Footer {
            background: #111827;
            color: #9ca3af;
        }

        #root {
            height: 1fr;
        }

        #main-layout {
            height: 1fr;
        }

        #console-panel {
            width: 1fr;
            border: round #3b82f6;
            padding: 1;
            background: #0f172a;
        }

        #sidebar {
            width: 36;
            border: round #475569;
            padding: 1;
            background: #111827;
        }

        #input-panel {
            height: 4;
            border: round #22c55e;
            padding: 0 1;
            background: #020617;
        }

        #command-row {
            height: 1;
            width: 1fr;
        }

        #command-label {
            width: 12;
            color: #22c55e;
            text-style: bold;
            background: #020617;
        }

        #prompt-input {
            width: 1fr;
            height: 1;
            color: #f8fafc;
            background: #111827;
            border: none;
            padding: 0 1;
        }

        #prompt-input:focus {
            color: #ffffff;
            background: #1f2937;
            border: none;
        }

        #prompt-input > .input--placeholder {
            color: #64748b;
            text-style: italic;
        }

        .sidebar-title {
            color: #38bdf8;
            text-style: bold;
        }

        .sidebar-section {
            color: #a78bfa;
            text-style: bold;
        }

        .muted {
            color: #94a3b8;
        }
        """

        def __init__(self) -> None:
            super().__init__()
            self.session_metadata = session_metadata

        def compose(self) -> ComposeResult:
            yield Header(show_clock=True)
            with Vertical(id="root"):
                with Horizontal(id="main-layout"):
                    with Container(id="console-panel"):
                        yield RichLog(id="console", wrap=True, highlight=True, markup=True)
                    with Container(id="sidebar"):
                        yield Static("Dr Magu", classes="sidebar-title")
                        yield Label(f"Version: v{settings.version}")
                        yield Static("\nSession", classes="sidebar-section")
                        yield Label(f"ID: {session_metadata.id}", id="session-id")
                        yield Label(f"Status: {session_metadata.status}", id="session-status")
                        yield Label(f"Commands: {session_metadata.command_count}", id="session-commands")
                        yield Static("\nWorkspace", classes="sidebar-section")
                        yield Label(settings.workspace_path)
                        yield Static("\nProvider", classes="sidebar-section")
                        yield Label("opencode / deepseek-v4-flash")
                        yield Static("\nQuick Commands", classes="sidebar-section")
                        yield Label("/help     /commands")
                        yield Label("/status   /scan")
                        yield Label("/context  /workflow")
                        yield Label("/brain    /agents")
                        yield Label("/clear    /session")
                        yield Label("fl        gs        gd")
                        yield Static("\nHistory", classes="sidebar-section")
                        yield Label("↑ previous command")
                        yield Label("↓ next command")
                        yield Static("\nShortcuts", classes="sidebar-section")
                        yield Label("F1 Help | F2 Commands")
                        yield Label("F3 Sessions | F5 Status")
                with Container(id="input-panel"):
                    with Horizontal(id="command-row"):
                        yield Label("Command ›", id="command-label")
                        yield Input(
                            placeholder="Type a command... Use ↑/↓ for session history. Examples: /status, fl, gs, gd",
                            id="prompt-input",
                        )
            yield Footer()

        def on_mount(self) -> None:
            log = self.query_one("#console", RichLog)
            log.write("[bold cyan]Welcome to Dr Magu v1.1.1[/]")
            log.write(
                "[dim]Workspace-aware Terminal UI with persistent sessions, command history, and deterministic repository scanning, context generation, workflow execution, and Brain context loading.[/]"
            )
            self._write_separator(log)
            log.write("[bold]Try:[/] /help, /commands, /session, /scan, /context, /wf repository.context, /brain, /agents")
            log.write("[dim]Use Arrow Up and Arrow Down to navigate commands executed in this TUI session.[/]")
            log.write(f"[dim]Persistent session:[/] {session_metadata.id}")
            self.query_one("#prompt-input", Input).focus()

        def on_key(self, event: Key) -> None:
            if not self.query_one("#prompt-input", Input).has_focus:
                return

            if event.key == "up":
                previous_command = history.previous()
                if previous_command is not None:
                    self._set_input_value(previous_command)
                    event.stop()
                return

            if event.key == "down":
                next_command = history.next()
                if next_command is not None:
                    self._set_input_value(next_command)
                    event.stop()
                return

        def _set_input_value(self, value: str) -> None:
            prompt_input = self.query_one("#prompt-input", Input)
            prompt_input.value = value
            prompt_input.cursor_position = len(value)

        def on_unmount(self) -> None:
            session_manager.record_event(self.session_metadata.id, "tui.closed")

        def action_clear_console(self) -> None:
            self.query_one("#console", RichLog).clear()

        def action_show_help(self) -> None:
            self._render_help(self.query_one("#console", RichLog))

        def action_show_commands(self) -> None:
            self._render_commands(self.query_one("#console", RichLog))

        def action_show_status(self) -> None:
            log = self.query_one("#console", RichLog)
            self._execute_and_render("git.status", log)

        def action_open_sessions(self) -> None:
            self.push_screen(SessionManagerScreen(self.session_metadata.id), self._handle_session_selection)

        def _handle_session_selection(self, metadata: SessionMetadata | None) -> None:
            if metadata is None:
                self.query_one("#prompt-input", Input).focus()
                return
            self.session_metadata = metadata
            self._update_session_sidebar(metadata)
            log = self.query_one("#console", RichLog)
            log.write(f"[bold cyan]Current session:[/] {metadata.id}")
            self.query_one("#prompt-input", Input).focus()

        def on_input_submitted(self, event: Input.Submitted) -> None:
            raw_value = event.value.strip()
            event.input.value = ""
            if not raw_value:
                return

            history.add(raw_value)

            log = self.query_one("#console", RichLog)
            self._write_command_header(raw_value, log)
            self._handle_input(raw_value, log)

        def _handle_input(self, raw_value: str, log: RichLog) -> None:
            command = raw_value.strip()

            if command in {"/exit", ":q", "quit", "exit"}:
                self.exit()
                return

            if command in {"/clear", "clear", "cls"}:
                log.clear()
                return

            if command in {"/help", "help", "?"}:
                self._render_help(log)
                return

            if command in {"/commands", "commands"}:
                self._render_commands(log)
                return

            if command in {"/session", "/sessions", "session", "sessions", "ss"}:
                self.action_open_sessions()
                return

            if command in {"/status", "status"}:
                self._execute_and_render("git.status", log)
                return

            if command in {"/scan", "scan", "rs"}:
                self._execute_and_render("repo.scan", log)
                return

            if command in {"/context", "context", "cg"}:
                self._execute_and_render("context.generate", log)
                return

            if command in {"/context --refresh", "context --refresh", "cg --refresh"}:
                self._execute_and_render("context.generate --refresh true", log)
                return

            if command in {"/workflows", "workflows"}:
                self._execute_and_render("workflow.list", log)
                return

            if command in {"/runtime", "runtime", "ri"}:
                self._execute_and_render("runtime.inspect", log)
                return

            if command in {"/brain", "brain", "bc"}:
                self._execute_and_render("brain.context", log)
                return

            if command in {"/control", "control", "cc", "dashboard"}:
                self._execute_and_render("control.center", log)
                return

            if command.startswith("/control-plugin "):
                self._execute_and_render("control.plugin " + command.removeprefix("/control-plugin ").strip(), log)
                return

            if command in {"/agents", "agents", "al"}:
                self._execute_and_render("agent.list", log)
                return

            if command in {"/tools", "tools", "tl"}:
                self._execute_and_render("tools.list", log)
                return

            if command in {"/permissions", "permissions", "ps"}:
                self._execute_and_render("permissions.show", log)
                return

            if command in {"/agent", "agent", "ar"}:
                self._execute_and_render("agent.run repository-analyzer", log)
                return

            if command.startswith("/agent "):
                self._execute_and_render("agent.run " + command.removeprefix("/agent ").strip(), log)
                return

            if command.startswith("/agent-show "):
                self._execute_and_render("agent.show " + command.removeprefix("/agent-show ").strip(), log)
                return

            if command.startswith("/agent-validate "):
                self._execute_and_render("agent.validate " + command.removeprefix("/agent-validate ").strip(), log)
                return

            if command.startswith("/agent-enable "):
                self._execute_and_render("agent.enable " + command.removeprefix("/agent-enable ").strip(), log)
                return

            if command.startswith("/agent-disable "):
                self._execute_and_render("agent.disable " + command.removeprefix("/agent-disable ").strip(), log)
                return

            if command.startswith("/agent-delete "):
                self._execute_and_render("agent.delete " + command.removeprefix("/agent-delete ").strip(), log)
                return

            if command in {"/workflow-runs", "workflow-runs", "wr"}:
                self._execute_and_render("workflow.runs", log)
                return

            if command in {"/workflow-last", "workflow-last", "wl"}:
                self._execute_and_render("workflow.last", log)
                return

            if command in {"/workflow", "/wf", "workflow", "wf"}:
                self._execute_and_render("workflow.run repository.context", log)
                return

            if command.startswith("/wf "):
                self._execute_and_render("workflow.run " + command.removeprefix("/wf ").strip(), log)
                return

            if command.startswith("/workflow "):
                self._execute_and_render("workflow.run " + command.removeprefix("/workflow ").strip(), log)
                return

            if command.startswith("/") and not command.startswith("/run "):
                command = command[1:]

            original_command = command
            explicit_command = raw_value.strip().startswith("/") or command.startswith("run ") or command.startswith("/run ")

            if command.startswith("run "):
                command = command.removeprefix("run ").strip()
            elif command.startswith("/run "):
                command = command.removeprefix("/run ").strip()

            if not explicit_command:
                first_token = command.split(maxsplit=1)[0] if command else ""
                try:
                    registry.get(first_token)
                except Exception:
                    safe_prompt = original_command.replace('"', '\\"')
                    self._execute_and_render(f'brain.ask "{safe_prompt}"', log)
                    return

            self._execute_and_render(command, log)

        def _execute_and_render(self, command_line: str, log: RichLog) -> None:
            result = processor.execute_line(command_line, context)
            if result.success and result.tool == "repo.scan" and result.data:
                output_path = write_latest_scan(context.workspace_path, RepositoryScan.model_validate(result.data))
                result.data["scan_file"] = str(output_path)
            updated_session = session_manager.record_command(self.session_metadata.id, command_line, result)
            self._update_session_sidebar(updated_session)
            self._render_result(result, command_line, log)

        def _update_session_sidebar(self, metadata: SessionMetadata) -> None:
            self.query_one("#session-id", Label).update(f"ID: {metadata.id}")
            self.query_one("#session-status", Label).update(f"Status: {metadata.status}")
            self.query_one("#session-commands", Label).update(f"Commands: {metadata.command_count}")

        def _render_help(self, log: RichLog) -> None:
            log.write("[bold cyan]Dr Magu TUI Commands[/]")
            rows = [
                ("/help", "Show this help."),
                ("/commands", "List registered internal commands."),
                ("/status or status", "Show Git workspace status."),
                ("/scan, scan, rs", "Scan the workspace and persist latest scan metadata."),
                ("/context, cg", "Generate deterministic project context files."),
                ("/workflows", "List registered deterministic workflows."),
                ("/runtime, ri", "Inspect runtime context for the future Orchestrator Brain."),
                ("/brain, bc", "Load Brain context with commands, workflows, agents, tools, permissions, session, workspace, and model defaults."),
                ("/control, cc", "Open the Control Center dashboard across plugins, agents, workflows, tools, permissions, schedules, and Brain."),
                ("/control-plugin <id>", "Show plugin impact and dependency details."),
                ("/agents, al", "List configured agents with resolved model configuration."),
                ("/agent <id>", "Run a configured agent. Defaults to repository-analyzer."),
                ("/tools, tl", "List formal tool registry entries."),
                ("/permissions, ps", "Show effective permission context."),
                ("/workflow-runs, wr", "List recent workflow runs."),
                ("/workflow-last, wl", "Show the latest workflow run detail."),
                ("/wf <name>", "Run a registered workflow. Defaults to repository.context."),
                ("/session, ss", "Open the persistent session manager popup."),
                ("/run <command>", "Execute an internal command."),
                ("fl, gs, gd", "Quick aliases for files.list, git.status, git.diff."),
                ("Arrow Up", "Show previous command from the current TUI session."),
                ("Arrow Down", "Show next command from the current TUI session."),
                ("/clear", "Clear console."),
                ("/plugins", "List discovered local plugins."),
                ("/exit", "Exit the TUI."),
            ]
            for command, description in rows:
                log.write(f"  [bold magenta]{command:<20}[/] [white]{description}[/]")

        def _render_commands(self, log: RichLog) -> None:
            log.write("[bold cyan]Registered Commands[/]")
            current_category = ""
            for command in registry.list_commands():
                if command.category != current_category:
                    current_category = command.category
                    log.write(f"\n[bold purple]{current_category.upper()}[/]")
                aliases = f"[dim] aliases: {', '.join(command.aliases)}[/]" if command.aliases else ""
                log.write(f"  [cyan]{command.name:<14}[/] {command.description} {aliases}")

        @staticmethod
        def _write_command_header(raw_value: str, log: RichLog) -> None:
            timestamp = datetime.now().strftime("%H:%M:%S")
            log.write(f"\n[dim]{'─' * 72}[/]")
            log.write(f"[dim]{timestamp}[/] [bold green]>[/] [white]{raw_value}[/]")

        @staticmethod
        def _write_separator(log: RichLog) -> None:
            log.write(f"[dim]{'─' * 72}[/]")

        def _render_result(self, result: ToolResult, command_line: str, log: RichLog) -> None:
            timestamp = datetime.now().strftime("%H:%M:%S")
            status_icon = "✓" if result.success else "✗"
            status_color = "green" if result.success else "red"
            log.write(f"[dim]{timestamp}[/] [{status_color}]{status_icon} {result.tool}[/]")

            if result.errors:
                self._render_errors(result, command_line, log)
                return

            if not result.data:
                log.write("[dim]No output.[/]")
                return

            renderer = {
                "files.list": self._render_files_list,
                "files.read": self._render_files_read,
                "git.status": self._render_git_status,
                "git.diff": self._render_git_diff,
                "search.code": self._render_search_code,
                "shell.run": self._render_shell_run,
                "repo.scan": self._render_repo_scan,
                "context.generate": self._render_project_context,
                "context.show": self._render_project_context,
                "context.path": self._render_context_path,
                "workflow.list": self._render_workflow_list,
                "workflow.show": self._render_workflow_show,
                "workflow.run": self._render_workflow_run,
                "workflow.runs": self._render_workflow_runs,
                "workflow.run.show": self._render_workflow_run_show,
                "workflow.last": self._render_workflow_run_show,
                "runtime.inspect": self._render_runtime_inspect,
                "brain.context": self._render_brain_context,
                "agent.list": self._render_agent_list,
                "agent.show": self._render_agent_show,
                "agent.run": self._render_agent_run,
                "agent.validate": self._render_agent_validate,
                "agent.add": self._render_agent_mutation,
                "agent.update": self._render_agent_mutation,
                "agent.enable": self._render_agent_mutation,
                "agent.disable": self._render_agent_mutation,
                "agent.delete": self._render_agent_mutation,
                "tools.list": self._render_tools_list,
                "permissions.show": self._render_permissions_show,
                "plugin.list": self._render_plugin_list,
                "plugin.show": self._render_plugin_show,
                "plugin.validate": self._render_plugin_validate,
                "control.center": self._render_control_center,
                "control.plugin": self._render_control_plugin,
            }.get(result.tool, self._render_generic_data)

            renderer(result.data, log)

            if result.metadata.get("duration_ms") is not None:
                log.write(f"[dim]Duration: {result.metadata['duration_ms']} ms[/]")

        def _render_errors(self, result: ToolResult, command_line: str, log: RichLog) -> None:
            for error in result.errors:
                log.write(f"[red]error:[/] {error}")

            attempted = command_line.split(maxsplit=1)[0].lstrip("/") if command_line else ""
            suggestions = self._suggest_commands(attempted)
            if suggestions:
                log.write(f"[yellow]Did you mean:[/] {', '.join(suggestions)}")

        @staticmethod
        def _suggest_commands(attempted: str) -> list[str]:
            if not attempted:
                return []
            names: list[str] = []
            for command in registry.list_commands():
                names.append(command.name)
                names.extend(command.aliases)
            return get_close_matches(attempted, names, n=3, cutoff=0.45)

        @staticmethod
        def _render_files_list(data: dict[str, Any], log: RichLog) -> None:
            workspace = data.get("workspace")
            files = data.get("files", []) or []
            count = data.get("count", len(files))

            log.write(f"[bold]Workspace:[/] [dim]{workspace}[/]")
            log.write(f"[bold]Files[/] [dim]({count})[/]")

            for file_name in files[:120]:
                icon = "📄"
                suffix = str(file_name).replace("\\", "/")
                if "/" in suffix:
                    icon = "├─"
                log.write(f"  [dim]{icon}[/] {suffix}")

            remaining = int(count) - min(len(files), 120)
            if remaining > 0:
                log.write(f"[dim]... {remaining} more files. Use files.list --max-files <n> to show more.[/]")

        @staticmethod
        def _render_files_read(data: dict[str, Any], log: RichLog) -> None:
            path = data.get("path", "")
            content = data.get("content", "")
            truncated = data.get("truncated", False)
            log.write(f"[bold]File:[/] {path}")
            log.write("[dim]Content[/]")
            log.write(str(content))
            if truncated:
                log.write("[yellow]Output truncated. Increase --max-chars to read more.[/]")

        @staticmethod
        def _render_git_status(data: dict[str, Any], log: RichLog) -> None:
            stdout = data.get("stdout")
            stderr = data.get("stderr")
            return_code = data.get("return_code")

            if stdout:
                log.write("[bold]status[/]")
                log.write(str(stdout))
            else:
                log.write("[green]Working tree is clean or Git returned no status output.[/]")

            if stderr:
                log.write("[bold red]stderr[/]")
                log.write(str(stderr))
            if return_code is not None:
                log.write(f"[bold]return_code:[/] {return_code}")

        @staticmethod
        def _render_git_diff(data: dict[str, Any], log: RichLog) -> None:
            diff = data.get("diff") or data.get("stdout") or ""
            if not diff:
                log.write("[green]No git diff detected.[/]")
                return
            log.write(str(diff))

        @staticmethod
        def _render_search_code(data: dict[str, Any], log: RichLog) -> None:
            results = data.get("results", []) or []
            query = data.get("query", "")
            log.write(f"[bold]Search:[/] {query}")
            if not results:
                log.write("[yellow]No matches found.[/]")
                return
            for item in results[:80]:
                if isinstance(item, dict):
                    path = item.get("path", "")
                    line = item.get("line", "")
                    text = item.get("text", "")
                    log.write(f"  [cyan]{path}:{line}[/] {text}")
                else:
                    log.write(f"  [cyan]{item}[/]")

        @staticmethod
        def _render_shell_run(data: dict[str, Any], log: RichLog) -> None:
            stdout = data.get("stdout", "")
            stderr = data.get("stderr", "")
            return_code = data.get("return_code")
            if stdout:
                log.write("[bold]stdout[/]")
                log.write(str(stdout))
            if stderr:
                log.write("[bold red]stderr[/]")
                log.write(str(stderr))
            if return_code is not None:
                log.write(f"[bold]return_code:[/] {return_code}")

        @staticmethod
        def _render_repo_scan(data: dict[str, Any], log: RichLog) -> None:
            log.write("[bold cyan]Repository Scan Summary[/]")
            log.write(f"[bold]Workspace:[/] {data.get('workspace_path', '')}")
            log.write(f"[bold]Project:[/] {data.get('project_name', '')}")
            log.write(f"[bold]Type:[/] {data.get('project_type', '')}")
            log.write(f"[bold]Primary Language:[/] {data.get('primary_language') or 'unknown'}")

            for label, key in (
                ("Languages", "languages"),
                ("Frameworks", "frameworks"),
                ("Package Managers", "package_managers"),
                ("Build Tools", "build_tools"),
                ("Test Frameworks", "test_frameworks"),
                ("Capabilities", "capabilities"),
            ):
                values = data.get(key, []) or []
                log.write(f"[bold]{label}:[/] {', '.join(values) if values else 'none detected'}")

            log.write(f"[bold]Files:[/] {data.get('file_count', 0)}")
            important_files = data.get("important_files", []) or []
            if important_files:
                log.write("[bold]Important Files[/]")
                for item in important_files[:20]:
                    log.write(f"  [cyan]{item.get('path', '')}[/] [dim]{item.get('reason', '')}[/]")
            if data.get("scan_file"):
                log.write(f"[bold green]Scan written:[/] {data.get('scan_file')}")


        @staticmethod
        def _render_project_context(data: dict[str, Any], log: RichLog) -> None:
            log.write("[bold cyan]Project Context[/]")
            log.write(f"[bold]Workspace:[/] {data.get('workspace_path', '')}")
            log.write(f"[bold]Project:[/] {data.get('project_name', '')}")
            log.write(f"[bold]Type:[/] {data.get('project_type', '')}")
            log.write(f"[bold]Primary Language:[/] {data.get('primary_language') or 'unknown'}")

            for label, key in (
                ("Languages", "languages"),
                ("Frameworks", "frameworks"),
                ("Capabilities", "capabilities"),
            ):
                values = data.get(key, []) or []
                log.write(f"[bold]{label}:[/] {', '.join(values) if values else 'none detected'}")

            context_dir = data.get("context_dir")
            if context_dir:
                log.write(f"[bold green]Context directory:[/] {context_dir}")

            generated_files = data.get("generated_files", []) or []
            if generated_files:
                log.write("[bold]Generated Files[/]")
                for item in generated_files:
                    log.write(f"  [cyan]{item.get('name', '')}[/] [dim]{item.get('path', '')}[/]")

        @staticmethod
        def _render_context_path(data: dict[str, Any], log: RichLog) -> None:
            log.write("[bold cyan]Project Context Path[/]")
            log.write(f"[bold]Workspace:[/] {data.get('workspace_path', '')}")
            log.write(f"[bold]Context directory:[/] {data.get('context_dir', '')}")
            log.write(f"[bold]Exists:[/] {data.get('exists', False)}")


        @staticmethod
        def _render_workflow_list(data: dict[str, Any], log: RichLog) -> None:
            log.write("[bold cyan]Registered Workflows[/]")
            workflows = data.get("workflows", []) or []
            if not workflows:
                log.write("[yellow]No workflows registered.[/]")
                return
            for workflow in workflows:
                requires_llm = "yes" if workflow.get("requires_llm") else "no"
                aliases = ", ".join(workflow.get("aliases", []) or [])
                log.write(
                    f"  [cyan]{workflow.get('name', '')}[/] "
                    f"[dim]{workflow.get('workflow_type', '')} | requires LLM: {requires_llm} | aliases: {aliases}[/]"
                )
                log.write(f"    {workflow.get('description', '')}")

        @staticmethod
        def _render_workflow_show(data: dict[str, Any], log: RichLog) -> None:
            log.write("[bold cyan]Workflow[/]")
            log.write(f"[bold]Name:[/] {data.get('name', '')}")
            log.write(f"[bold]Type:[/] {data.get('workflow_type', '')}")
            log.write(f"[bold]Requires LLM:[/] {data.get('requires_llm', False)}")
            log.write(f"[bold]Description:[/] {data.get('description', '')}")
            aliases = data.get("aliases", []) or []
            if aliases:
                log.write(f"[bold]Aliases:[/] {', '.join(aliases)}")

        @staticmethod
        def _render_workflow_run(data: dict[str, Any], log: RichLog) -> None:
            log.write("[bold cyan]Workflow Run[/]")
            log.write(f"[bold]Run ID:[/] {data.get('run_id', '')}")
            log.write(f"[bold]Workflow:[/] {data.get('workflow', '')}")
            log.write(f"[bold]Workspace:[/] {data.get('workspace_path', '')}")
            if data.get("duration_ms") is not None:
                log.write(f"[bold]Duration:[/] {_format_duration_ms(data.get('duration_ms'))}")
            if data.get("scan_path"):
                log.write(f"[bold green]Scan:[/] {data.get('scan_path')}")
            if data.get("context_path"):
                log.write(f"[bold green]Context:[/] {data.get('context_path')}")
            generated_files = data.get("generated_files", []) or []
            if generated_files:
                log.write("[bold]Generated Files[/]")
                for path in generated_files:
                    log.write(f"  [cyan]{path}[/]")
            for key in ("run_file", "state_file", "events_file"):
                if data.get(key):
                    log.write(f"[bold]{key.replace('_', ' ').title()}:[/] {data[key]}")

        @staticmethod
        def _render_workflow_runs(data: dict[str, Any], log: RichLog) -> None:
            log.write("[bold cyan]Workflow Runs[/]")
            runs = data.get("runs", []) or []
            if not runs:
                log.write("[yellow]No workflow runs found.[/]")
                return
            for run in runs[:50]:
                duration = _format_duration_ms(run.get("duration_ms"))
                completed = run.get("completed_at") or "running"
                log.write(
                    f"  [cyan]{run.get('id', '')}[/] "
                    f"{run.get('workflow', '')} [{run.get('status', '')}] "
                    f"[dim]{duration} | {completed}[/]"
                )

        @staticmethod
        def _render_workflow_run_show(data: dict[str, Any], log: RichLog) -> None:
            log.write("[bold cyan]Workflow Run Details[/]")
            run = data.get("run", {}) or {}
            state = data.get("state", {}) or {}
            log.write(f"[bold]Run ID:[/] {run.get('id', '')}")
            log.write(f"[bold]Workflow:[/] {run.get('workflow', '')}")
            log.write(f"[bold]Status:[/] {run.get('status', '')}")
            if run.get("duration_ms") is not None:
                log.write(f"[bold]Duration:[/] {_format_duration_ms(run.get('duration_ms'))}")
            if state.get("context_path"):
                log.write(f"[bold]Context:[/] {state.get('context_path')}")
            generated_files = state.get("generated_files", []) or []
            if generated_files:
                log.write("[bold]Generated Files[/]")
                for path in generated_files:
                    log.write(f"  [cyan]{path}[/]")
            events = (data.get("events", []) or [])[-10:]
            if events:
                log.write("[bold]Recent Events[/]")
                for event in events:
                    duration = _format_duration_ms(event.get("duration_ms"))
                    log.write(
                        f"  [dim]{event.get('type', '')}[/] "
                        f"{event.get('node', '')} "
                        f"[dim]{duration}[/] "
                        f"{event.get('message', '') or ''}"
                    )

        @staticmethod
        def _render_runtime_inspect(data: dict[str, Any], log: RichLog) -> None:
            workspace = data.get("workspace", {}) or {}
            session = data.get("session", {}) or {}
            summary = data.get("summary", {}) or {}

            log.write("[bold cyan]Runtime Introspection[/]")
            log.write(f"[bold]Workspace:[/] {workspace.get('path', '')}")
            log.write(f"[bold]Workspace exists:[/] {workspace.get('exists', False)}")
            log.write(f"[bold]Git repository:[/] {workspace.get('is_git_repository', False)}")
            log.write(f"[bold]Current session:[/] {session.get('id') or 'none'}")
            log.write(
                "[bold]Inventory:[/] "
                f"{summary.get('command_count', 0)} commands, "
                f"{summary.get('workflow_count', 0)} workflows, "
                f"{summary.get('tool_count', 0)} tools, "
                f"{summary.get('agent_count', 0)} agents"
            )
            log.write(f"[bold]Brain ready:[/] {summary.get('brain_ready', False)}")

            commands = data.get("commands", []) or []
            if commands:
                log.write("\n[bold purple]Commands[/]")
                for command in commands[:40]:
                    aliases = command.get("aliases", []) or []
                    alias_label = f" [dim]({', '.join(aliases)})[/]" if aliases else ""
                    log.write(f"  [cyan]{command.get('name', '')}[/] {alias_label}")

            workflows = data.get("workflows", []) or []
            if workflows:
                log.write("\n[bold purple]Workflows[/]")
                for workflow in workflows:
                    log.write(
                        f"  [cyan]{workflow.get('name', '')}[/] "
                        f"[dim]{workflow.get('workflow_type', '')} | llm={workflow.get('requires_llm', False)}[/]"
                    )


        @staticmethod
        def _render_brain_context(data: dict[str, Any], log: RichLog) -> None:
            summary = data.get("summary", {}) or {}
            default_model = data.get("default_model", {}) or {}
            log.write("[bold cyan]Brain Context[/]")
            log.write(f"[bold]Commands:[/] {summary.get('command_count', 0)}")
            log.write(f"[bold]Workflows:[/] {summary.get('workflow_count', 0)}")
            log.write(f"[bold]Tools:[/] {summary.get('tool_count', 0)}")
            log.write(f"[bold]Agents:[/] {summary.get('agent_count', 0)}")
            log.write(f"[bold]Default Provider:[/] {default_model.get('provider', '')}")
            log.write(f"[bold]Default Model:[/] {default_model.get('model', '')}")
            log.write(f"[bold]Temperature:[/] {default_model.get('temperature', '')}")
            log.write(f"[bold]API Key Configured:[/] {default_model.get('api_key_configured', False)}")
            log.write(f"[bold]LLM Calls Enabled:[/] {summary.get('llm_calls_enabled', False)}")

        @staticmethod
        def _render_agent_list(data: dict[str, Any], log: RichLog) -> None:
            agents = data.get("agents", []) or []
            log.write("[bold cyan]Configured Agents[/]")
            if not agents:
                log.write("[yellow]No agents configured.[/]")
                return
            for agent in agents:
                model = agent.get("model", {}) or {}
                log.write(
                    f"  [cyan]{agent.get('id', '')}[/] "
                    f"[dim]{agent.get('workflow', '')} | enabled={agent.get('enabled', False)} | deleted={agent.get('deleted', False)} | source={agent.get('source', '')} | plugin={agent.get('plugin_id', '') or ''} | model={model.get('model', '')}[/]"
                )
                log.write(f"    {agent.get('description', '')}")

        @staticmethod
        def _render_agent_show(data: dict[str, Any], log: RichLog) -> None:
            model = data.get("model", {}) or {}
            log.write("[bold cyan]Agent[/]")
            for key in ("id", "name", "role", "workflow", "enabled", "deleted", "requires_llm", "source", "plugin_id", "description"):
                log.write(f"[bold]{key.replace('_', ' ').title()}:[/] {data.get(key, '')}")
            log.write(f"[bold]Model:[/] {model.get('provider', '')}/{model.get('model', '')} temp={model.get('temperature', '')}")
            log.write(f"[bold]Model Source:[/] {model.get('source', '')}")

        @staticmethod
        def _render_agent_run(data: dict[str, Any], log: RichLog) -> None:
            agent = data.get("agent", {}) or {}
            workflow_result = data.get("workflow_result", {}) or {}
            log.write("[bold cyan]Agent Run[/]")
            log.write(f"[bold]Agent:[/] {agent.get('id', '')}")
            log.write(f"[bold]Workflow:[/] {agent.get('workflow', '')}")
            log.write(f"[bold]Workflow Success:[/] {data.get('workflow_success', False)}")
            if workflow_result.get("run_id"):
                log.write(f"[bold]Workflow Run ID:[/] {workflow_result.get('run_id')}")
            if workflow_result.get("context_path"):
                log.write(f"[bold green]Context:[/] {workflow_result.get('context_path')}")


        @staticmethod
        def _render_agent_mutation(data: dict[str, Any], log: RichLog) -> None:
            agent = data.get("agent", {}) or {}
            log.write("[bold cyan]Agent Updated[/]")
            for key in ("id", "name", "enabled", "deleted", "source", "plugin_id", "workflow"):
                log.write(f"[bold]{key.replace('_', ' ').title()}:[/] {agent.get(key, '')}")
            if data.get("store_path"):
                log.write(f"[bold green]Store:[/] {data.get('store_path')}")

        @staticmethod
        def _render_agent_validate(data: dict[str, Any], log: RichLog) -> None:
            agent = data.get("agent", {}) or {}
            valid = data.get("valid", False)
            color = "green" if valid else "red"
            log.write(f"[bold cyan]Agent Validation[/] [{color}]{valid}[/]")
            log.write(f"[bold]Agent:[/] {agent.get('id', '')}")
            log.write(f"[bold]Workflow:[/] {agent.get('workflow', '')}")
            for error in data.get("errors", []) or []:
                log.write(f"[red]error:[/] {error}")

        @staticmethod
        def _render_tools_list(data: dict[str, Any], log: RichLog) -> None:
            log.write("[bold cyan]Formal Tool Registry[/]")
            for tool in (data.get("tools", []) or [])[:80]:
                log.write(
                    f"  [cyan]{tool.get('name', '')}[/] "
                    f"[dim]{tool.get('category', '')} | read_only={tool.get('read_only', True)} | approval={tool.get('requires_approval', False)}[/]"
                )

        @staticmethod
        def _render_permissions_show(data: dict[str, Any], log: RichLog) -> None:
            log.write("[bold cyan]Permission Context[/]")
            for key, value in data.items():
                log.write(f"[bold]{key.replace('_', ' ').title()}:[/] {value}")


        @staticmethod
        def _render_plugin_list(data: dict[str, Any], log: RichLog) -> None:
            log.write("[bold cyan]Plugin Registry[/]")
            plugins = data.get("plugins", []) or []
            if not plugins:
                log.write("[yellow]No plugins discovered.[/]")
                return
            for plugin in plugins[:80]:
                provides = plugin.get("provides", {}) or {}
                log.write(
                    f"  [cyan]{plugin.get('id', '')}[/] "
                    f"[dim]enabled={plugin.get('enabled', False)} | domain={plugin.get('domain', '')} | "
                    f"agents={len(provides.get('agents', []) or [])} | workflows={len(provides.get('workflows', []) or [])} | "
                    f"tools={len(provides.get('tools', []) or [])}[/]"
                )
                description = plugin.get("description", "")
                if description:
                    log.write(f"    {description}")

        @staticmethod
        def _render_plugin_show(data: dict[str, Any], log: RichLog) -> None:
            log.write("[bold cyan]Plugin[/]")
            for key in ("id", "name", "version", "enabled", "domain", "description", "path"):
                log.write(f"[bold]{key.replace('_', ' ').title()}:[/] {data.get(key, '')}")
            provides = data.get("provides", {}) or {}
            for key in ("agents", "workflows", "tools", "commands", "schedules"):
                values = provides.get(key, []) or []
                log.write(f"[bold]{key.title()}[/] [dim]({len(values)})[/]")
                for value in values:
                    log.write(f"  - {value}")

        @staticmethod
        def _render_plugin_validate(data: dict[str, Any], log: RichLog) -> None:
            log.write("[bold cyan]Plugin Validation[/]")
            log.write(f"[bold]Valid:[/] {data.get('valid', False)}")
            for result in data.get("results", []) or []:
                log.write(f"  [cyan]{result.get('plugin_id', '')}[/] valid={result.get('valid', False)}")
                for error in result.get("errors", []) or []:
                    log.write(f"    [red]error:[/] {error}")
                for warning in result.get("warnings", []) or []:
                    log.write(f"    [yellow]warning:[/] {warning}")


        @staticmethod
        def _render_control_center(data: dict[str, Any], log: RichLog) -> None:
            log.write("[bold cyan]Dr Magu Control Center[/]")
            log.write(f"[bold]Workspace:[/] {data.get('workspace_path', '')}")
            log.write("[bold purple]Areas[/]")
            for section in data.get("sections", []) or []:
                enabled = section.get("enabled_count")
                enabled_label = "" if enabled is None else f" | enabled={enabled}"
                log.write(
                    f"  [cyan]{section.get('name', ''):<12}[/] "
                    f"[dim]count={section.get('count', 0)}{enabled_label} | status={section.get('status', '')}[/]"
                )
                description = section.get("description", "")
                if description:
                    log.write(f"    {description}")

            plugins = data.get("plugins", []) or []
            if plugins:
                log.write("[bold purple]Plugin Impact[/]")
                for plugin in plugins:
                    log.write(
                        f"  [cyan]{plugin.get('plugin_id', '')}[/] "
                        f"[dim]enabled={plugin.get('enabled', False)} | domain={plugin.get('domain', '')} | "
                        f"health={plugin.get('status', '')} | agents={len(plugin.get('agents', []) or [])} | "
                        f"workflows={len(plugin.get('workflows', []) or [])} | tools={len(plugin.get('tools', []) or [])}[/]"
                    )

            brain = data.get("brain", {}) or {}
            summary = brain.get("summary", {}) or {}
            log.write("[bold purple]Brain Readiness[/]")
            for key in ("brain_ready", "llm_configured", "default_provider", "default_model", "llm_calls_enabled"):
                log.write(f"  [bold]{key.replace('_', ' ').title()}:[/] {summary.get(key, '')}")

            schedules = data.get("schedules", {}) or {}
            log.write(f"[bold purple]Schedules[/] {schedules.get('status', 'reserved')} - {schedules.get('message', '')}")

        @staticmethod
        def _render_control_plugin(data: dict[str, Any], log: RichLog) -> None:
            log.write("[bold cyan]Plugin Control Center Detail[/]")
            for key in ("plugin_id", "name", "enabled", "domain", "status"):
                log.write(f"[bold]{key.replace('_', ' ').title()}:[/] {data.get(key, '')}")
            for key in ("agents", "workflows", "tools", "commands", "schedules"):
                values = data.get(key, []) or []
                log.write(f"[bold purple]{key.title()}[/] [dim]({len(values)})[/]")
                for value in values:
                    log.write(f"  - {value}")
            for warning in data.get("warnings", []) or []:
                log.write(f"[yellow]warning:[/] {warning}")
            for error in data.get("errors", []) or []:
                log.write(f"[red]error:[/] {error}")

        @staticmethod
        def _render_generic_data(data: dict[str, Any], log: RichLog) -> None:
            for key, value in data.items():
                if isinstance(value, list):
                    log.write(f"[bold]{key}[/] [dim]({len(value)})[/]")
                    for item in value[:80]:
                        log.write(f"  - {item}")
                    if len(value) > 80:
                        log.write(f"[dim]... {len(value) - 80} more[/]")
                else:
                    log.write(f"[bold]{key}[/]: {value}")

    DrMaguTui().run()

# v0.10.0: AI Orchestrator Brain routes natural language prompts through dr_magu.brain.

# v0.11.0: Intent Router classifies natural-language prompts before planning/execution.

# v0.12.0: Web Research Plugin adds research.search for research-oriented prompts.

# v0.16.0: Scheduler Runtime adds persisted schedule lifecycle operations and run-once execution.

# v0.17.0: Software Development Platform adds SDLC agents plus Git/Shell/Filesystem tool foundations.

# v0.18.0: Website Builder Workflow integrates research, SDLC agents, HITL and reports.

# v0.19.0: Workflow Engine Foundation adds state, context, history and runner primitives.

# v0.20.0: Workflow Runtime & History adds inspect, cancel, retry, resume and export operations.

# v0.22.0: Platform Stabilization adds v1.0.0 readiness checks.

# v1.1.0: Execution Runtime Layer adds plans, permissions, filesystem, terminal and git runtimes.

# v1.1.1: Conversational Brain Foundation routes unknown natural-language TUI input through brain.ask.

# v1.1.2: LLM Runtime Integration enables default-model chat through brain.ask for general chat.

# v1.1.3: OpenCode Provider Compatibility Fix adds provider-compatible headers for LLM runtime requests.

# v1.1.4: LLM Response Sanitization hides raw provider payloads during normal chat rendering.

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
from dr_magu.sessions.manager import SessionManager
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


@dataclass(frozen=True)
class TuiSettings:
    """Settings used to start the Dr Magu Terminal UI."""

    workspace_path: str
    version: str = "0.5.2"


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
                        yield Label("not configured")
                        yield Static("\nQuick Commands", classes="sidebar-section")
                        yield Label("/help     /commands")
                        yield Label("/status   /clear")
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
            log.write("[bold cyan]Welcome to Dr Magu v0.5.2[/]")
            log.write(
                "[dim]Improved Terminal UI with persistent sessions, in-memory navigation history, readable output, aliases, and suggestions.[/]"
            )
            self._write_separator(log)
            log.write("[bold]Try:[/] /help, /commands, /session, /status, fl, gs, gd")
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

            if command.startswith("/") and not command.startswith("/run "):
                command = command[1:]

            if command.startswith("run "):
                command = command.removeprefix("run ").strip()
            elif command.startswith("/run "):
                command = command.removeprefix("/run ").strip()

            self._execute_and_render(command, log)

        def _execute_and_render(self, command_line: str, log: RichLog) -> None:
            result = processor.execute_line(command_line, context)
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
                ("/session, ss", "Open the persistent session manager popup."),
                ("/run <command>", "Execute an internal command."),
                ("fl, gs, gd", "Quick aliases for files.list, git.status, git.diff."),
                ("Arrow Up", "Show previous command from the current TUI session."),
                ("Arrow Down", "Show next command from the current TUI session."),
                ("/clear", "Clear console."),
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

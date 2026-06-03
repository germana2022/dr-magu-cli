from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from difflib import get_close_matches
from typing import Any

from dr_magu.commands.context import CommandContext
from dr_magu.commands.processor import CommandProcessor
from dr_magu.commands.registry import registry
from dr_magu.config import load_config
from dr_magu.result import ToolResult


@dataclass(frozen=True)
class TuiSettings:
    """Settings used to start the Dr Magu Terminal UI."""

    workspace_path: str
    version: str = "0.4.1"


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
        from textual.widgets import Footer, Header, Input, Label, RichLog, Static
    except ModuleNotFoundError as exc:  # pragma: no cover - only triggered without optional runtime dependency
        missing = exc.name or "textual"
        raise RuntimeError(
            f"Missing dependency '{missing}'. Install the project with TUI dependencies: pip install -e ."
        ) from exc

    settings = TuiSettings(workspace_path=str(Path(workspace_path).resolve()))
    processor = CommandProcessor(registry)
    context = _build_context(settings.workspace_path)

    class DrMaguTui(App):
        """OpenCode-inspired terminal interface for Dr Magu."""

        TITLE = "Dr Magu"
        SUB_TITLE = "AI Agent Platform"
        BINDINGS = [
            ("ctrl+c", "quit", "Quit"),
            ("ctrl+l", "clear_console", "Clear"),
            ("f1", "show_help", "Help"),
            ("f2", "show_commands", "Commands"),
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

        def compose(self) -> ComposeResult:
            yield Header(show_clock=True)
            with Vertical(id="root"):
                with Horizontal(id="main-layout"):
                    with Container(id="console-panel"):
                        yield RichLog(id="console", wrap=True, highlight=True, markup=True)
                    with Container(id="sidebar"):
                        yield Static("Dr Magu", classes="sidebar-title")
                        yield Label(f"Version: v{settings.version}")
                        yield Label("Session: local")
                        yield Static("\nWorkspace", classes="sidebar-section")
                        yield Label(settings.workspace_path)
                        yield Static("\nProvider", classes="sidebar-section")
                        yield Label("not configured")
                        yield Static("\nQuick Commands", classes="sidebar-section")
                        yield Label("/help     /commands")
                        yield Label("/status   /clear")
                        yield Label("fl        gs        gd")
                        yield Static("\nShortcuts", classes="sidebar-section")
                        yield Label("F1 Help | F2 Commands | F5 Status")
                with Container(id="input-panel"):
                    with Horizontal(id="command-row"):
                        yield Label("Command ›", id="command-label")
                        yield Input(
                            placeholder="Type a command... Examples: /status, fl, gs, gd, /run git.status",
                            id="prompt-input",
                        )
            yield Footer()

        def on_mount(self) -> None:
            log = self.query_one("#console", RichLog)
            log.write("[bold cyan]Welcome to Dr Magu v0.4.1[/]")
            log.write("[dim]Improved Terminal UI with a visible command input area, readable output, aliases, and suggestions.[/]")
            self._write_separator(log)
            log.write("[bold]Try:[/] /help, /commands, /status, fl, gs, gd")
            self.query_one("#prompt-input", Input).focus()

        def action_clear_console(self) -> None:
            self.query_one("#console", RichLog).clear()

        def action_show_help(self) -> None:
            self._render_help(self.query_one("#console", RichLog))

        def action_show_commands(self) -> None:
            self._render_commands(self.query_one("#console", RichLog))

        def action_show_status(self) -> None:
            log = self.query_one("#console", RichLog)
            self._execute_and_render("git.status", log)

        def on_input_submitted(self, event: Input.Submitted) -> None:
            raw_value = event.value.strip()
            event.input.value = ""
            if not raw_value:
                return

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
            self._render_result(result, command_line, log)

        def _render_help(self, log: RichLog) -> None:
            log.write("[bold cyan]Dr Magu TUI Commands[/]")
            rows = [
                ("/help", "Show this help."),
                ("/commands", "List registered internal commands."),
                ("/status or status", "Show Git workspace status."),
                ("/run <command>", "Execute an internal command."),
                ("fl, gs, gd", "Quick aliases for files.list, git.status, git.diff."),
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
            for key in ("branch", "status", "workspace"):
                if key in data:
                    log.write(f"[bold]{key.title()}:[/] {data[key]}")

            for key, value in data.items():
                if key in {"branch", "status", "workspace"}:
                    continue
                log.write(f"[bold]{key.replace('_', ' ').title()}:[/] {value}")

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

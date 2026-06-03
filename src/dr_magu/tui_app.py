from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from dr_magu.commands.context import CommandContext
from dr_magu.commands.processor import CommandProcessor
from dr_magu.commands.registry import registry
from dr_magu.config import load_config


@dataclass(frozen=True)
class TuiSettings:
    """Settings used to start the Dr Magu Terminal UI."""

    workspace_path: str
    version: str = "0.3.0"


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
        ]

        CSS = """
        Screen {
            background: #0f111a;
            color: #f8f8f2;
        }

        #root {
            height: 1fr;
        }

        #main-layout {
            height: 1fr;
        }

        #console-panel {
            width: 1fr;
            border: round #6c71c4;
            padding: 1;
        }

        #sidebar {
            width: 34;
            border: round #44475a;
            padding: 1;
            background: #151722;
        }

        #input-panel {
            height: 3;
            border: round #50fa7b;
            padding: 0 1;
        }

        #prompt-input {
            width: 1fr;
        }

        .sidebar-title {
            color: #8be9fd;
            text-style: bold;
        }

        .hint {
            color: #bd93f9;
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
                        yield Label(f"Workspace:\n{settings.workspace_path}")
                        yield Label("Provider: not configured")
                        yield Label("Session: local")
                        yield Static("\nCommands", classes="sidebar-title")
                        yield Label("/help")
                        yield Label("/commands")
                        yield Label("/status")
                        yield Label("/run git.status")
                        yield Label("/clear")
                        yield Label("/exit")
                with Container(id="input-panel"):
                    yield Input(placeholder="Type /help, /commands, /run git.status, or a command...", id="prompt-input")
            yield Footer()

        def on_mount(self) -> None:
            log = self.query_one("#console", RichLog)
            log.write("[bold cyan]Welcome to Dr Magu v0.3.0[/]")
            log.write("Terminal UI foundation for local command processing.")
            log.write("[purple]Try:[/] /help, /commands, /status, /run files.list .")
            self.query_one("#prompt-input", Input).focus()

        def on_input_submitted(self, event: Input.Submitted) -> None:
            raw_value = event.value.strip()
            event.input.value = ""
            if not raw_value:
                return

            log = self.query_one("#console", RichLog)
            log.write(f"[bold green]>[/] {raw_value}")
            self._handle_input(raw_value, log)

        def _handle_input(self, raw_value: str, log: RichLog) -> None:
            if raw_value in {"/exit", ":q", "quit"}:
                self.exit()
                return

            if raw_value == "/clear":
                log.clear()
                return

            if raw_value == "/help":
                log.write("[bold cyan]Dr Magu TUI Commands[/]")
                log.write("/help                  Show help")
                log.write("/commands              List registered commands")
                log.write("/status                Show workspace status")
                log.write("/run <command>         Execute an internal command")
                log.write("/clear                 Clear console")
                log.write("/exit                  Exit the TUI")
                return

            if raw_value == "/commands":
                for command in registry.list_commands():
                    aliases = f" aliases: {', '.join(command.aliases)}" if command.aliases else ""
                    log.write(f"[cyan]{command.name}[/] - {command.description}{aliases}")
                return

            if raw_value == "/status":
                result = processor.execute("git.status", {}, context)
                self._render_result(result, log)
                return

            if raw_value.startswith("/run "):
                command_line = raw_value.removeprefix("/run ").strip()
                result = processor.execute_line(command_line, context)
                self._render_result(result, log)
                return

            # Convenience mode: allow direct internal commands without /run.
            result = processor.execute_line(raw_value, context)
            self._render_result(result, log)

        @staticmethod
        def _render_result(result, log: RichLog) -> None:
            timestamp = datetime.now().strftime("%H:%M:%S")
            status = "[green]success[/]" if result.success else "[red]failed[/]"
            log.write(f"[{timestamp}] {result.tool}: {status}")

            if result.errors:
                for error in result.errors:
                    log.write(f"[red]error:[/] {error}")

            if result.data:
                data = result.data
                if isinstance(data, dict):
                    for key, value in data.items():
                        log.write(f"[bold]{key}[/]: {value}")
                else:
                    log.write(str(data))

    DrMaguTui().run()

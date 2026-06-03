from __future__ import annotations

from dr_magu.commands.definitions import CommandDefinition
from dr_magu.commands.context import CommandContext
from dr_magu.result import ToolResult
from dr_magu.tools.file_tools import list_files, read_file
from dr_magu.tools.git_tools import git_diff, git_status
from dr_magu.tools.search_tools import search_code
from dr_magu.tools.shell_tools import run_shell
from dr_magu.scanner.repository_scanner import scan_repository


def _get_str(args: dict[str, object], key: str, default: str) -> str:
    value = args.get(key, default)
    return str(value)


def _get_int(args: dict[str, object], key: str, default: int) -> int:
    value = args.get(key, default)
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def handle_files_list(args: dict[str, object], context: CommandContext) -> ToolResult:
    return list_files(
        context.workspace_path,
        target_path=_get_str(args, "path", "."),
        max_files=_get_int(args, "max_files", 500),
    )


def handle_files_read(args: dict[str, object], context: CommandContext) -> ToolResult:
    return read_file(
        context.workspace_path,
        file_path=_get_str(args, "path", ""),
        max_chars=_get_int(args, "max_chars", 20000),
    )


def handle_search_code(args: dict[str, object], context: CommandContext) -> ToolResult:
    return search_code(
        context.workspace_path,
        query=_get_str(args, "query", ""),
        target_path=_get_str(args, "path", "."),
        max_results=_get_int(args, "max_results", 100),
    )


def handle_git_status(args: dict[str, object], context: CommandContext) -> ToolResult:
    return git_status(context.workspace_path)


def handle_git_diff(args: dict[str, object], context: CommandContext) -> ToolResult:
    return git_diff(context.workspace_path)


def handle_shell_run(args: dict[str, object], context: CommandContext) -> ToolResult:
    blocked_patterns = context.config.get("blocked_shell_patterns", [])
    return run_shell(
        context.workspace_path,
        command=_get_str(args, "command", ""),
        blocked_patterns=list(blocked_patterns),
        timeout_seconds=_get_int(args, "timeout_seconds", 120),
    )


def handle_repo_scan(args: dict[str, object], context: CommandContext) -> ToolResult:
    return scan_repository(
        context.workspace_path,
        max_files=_get_int(args, "max_files", 5000),
    )


class CommandRegistry:
    """In-memory registry used by both direct CLI commands and the run processor."""

    def __init__(self) -> None:
        self._commands: dict[str, CommandDefinition] = {}
        self._aliases: dict[str, str] = {}

    def register(self, command: CommandDefinition) -> None:
        self._commands[command.name] = command
        for alias in command.aliases:
            self._aliases[alias] = command.name

    def get(self, name: str) -> CommandDefinition:
        resolved_name = self._aliases.get(name, name)
        if resolved_name not in self._commands:
            available = ", ".join(sorted(self._commands))
            raise KeyError(f"Unknown command '{name}'. Available commands: {available}")
        return self._commands[resolved_name]

    def list_commands(self) -> list[CommandDefinition]:
        return sorted(self._commands.values(), key=lambda item: item.name)


registry = CommandRegistry()

registry.register(CommandDefinition(
    name="files.list",
    aliases=["fl"],
    description="List files inside the workspace.",
    category="files",
    handler=handle_files_list,
))
registry.register(CommandDefinition(
    name="files.read",
    aliases=["fr"],
    description="Read a text file from the workspace.",
    category="files",
    handler=handle_files_read,
))
registry.register(CommandDefinition(
    name="search.code",
    aliases=["sc"],
    description="Search text across source files.",
    category="search",
    handler=handle_search_code,
))
registry.register(CommandDefinition(
    name="git.status",
    aliases=["gs"],
    description="Show git status for the workspace.",
    category="git",
    handler=handle_git_status,
))
registry.register(CommandDefinition(
    name="git.diff",
    aliases=["gd"],
    description="Show git diff for the workspace.",
    category="git",
    handler=handle_git_diff,
))
registry.register(CommandDefinition(
    name="shell.run",
    aliases=["sh"],
    description="Run a shell command inside the workspace.",
    category="shell",
    handler=handle_shell_run,
))

registry.register(CommandDefinition(
    name="repo.scan",
    aliases=["scan", "rs"],
    description="Scan the workspace and detect repository metadata.",
    category="repository",
    handler=handle_repo_scan,
))

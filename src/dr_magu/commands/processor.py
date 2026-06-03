from __future__ import annotations

import shlex

from dr_magu.commands.context import CommandContext
from dr_magu.commands.registry import CommandRegistry, registry as default_registry
from dr_magu.result import ToolResult


class CommandProcessor:
    """Processes command names and arguments through the command registry."""

    def __init__(self, registry: CommandRegistry | None = None) -> None:
        self.registry = registry or default_registry

    def execute(self, command_name: str, args: dict[str, object] | None, context: CommandContext) -> ToolResult:
        try:
            command = self.registry.get(command_name)
            return command.handler(args or {}, context)
        except Exception as exc:
            return ToolResult(success=False, tool=command_name, errors=[str(exc)])

    def execute_line(self, command_line: str, context: CommandContext) -> ToolResult:
        try:
            parsed = self.parse_line(command_line)
            return self.execute(parsed["command_name"], parsed["args"], context)
        except Exception as exc:
            return ToolResult(success=False, tool="command.run", errors=[str(exc)])

    @staticmethod
    def parse_line(command_line: str) -> dict[str, object]:
        tokens = shlex.split(command_line)
        if not tokens:
            raise ValueError("Command line cannot be empty.")

        command_name = tokens[0]
        args: dict[str, object] = {}
        positional: list[str] = []
        index = 1

        while index < len(tokens):
            token = tokens[index]
            if token.startswith("--"):
                key = token[2:].replace("-", "_")
                if index + 1 >= len(tokens) or tokens[index + 1].startswith("--"):
                    args[key] = True
                    index += 1
                else:
                    args[key] = tokens[index + 1]
                    index += 2
            else:
                positional.append(token)
                index += 1

        if command_name == "files.read" and positional:
            args.setdefault("path", positional[0])
        elif command_name == "files.list" and positional:
            args.setdefault("path", positional[0])
        elif command_name == "search.code":
            if positional:
                args.setdefault("query", positional[0])
            if len(positional) > 1:
                args.setdefault("path", positional[1])
        elif command_name == "shell.run" and positional:
            args.setdefault("command", " ".join(positional))
        elif command_name in {"repo.scan", "scan"}:
            if positional:
                args.setdefault("path", positional[0])
        elif command_name in {"context.generate", "context", "cg"}:
            if positional and positional[0] in {"--refresh", "refresh"}:
                args.setdefault("refresh", True)
        else:
            if positional:
                args.setdefault("value", " ".join(positional))

        return {"command_name": command_name, "args": args}

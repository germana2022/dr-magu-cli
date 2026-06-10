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
        elif command_name in {"workflow.run", "wr", "wf"}:
            if positional:
                args.setdefault("name", positional[0])
            else:
                args.setdefault("name", "repository.context")
        elif command_name in {"workflow.show", "ws"}:
            if positional:
                args.setdefault("name", positional[0])
        elif command_name in {"workflow.run.show", "wshow"}:
            if positional:
                args.setdefault("run_id", positional[0])
        elif command_name in {"brain.ask", "brain.chat", "ask", "chat"}:
            if positional:
                args.setdefault("prompt", " ".join(positional))
        elif command_name in {"router.route", "route", "cr.route", "router.execute", "route.execute", "cr.exec"}:
            if positional:
                args.setdefault("prompt", " ".join(positional))
        elif command_name in {"multiagent.plan", "ma.plan", "agents.plan", "multiagent.run", "ma.run", "agents.run"}:
            if positional:
                args.setdefault("name", positional[0])
        elif command_name in {"factory.plan", "software.factory.plan", "sf.plan", "factory.run", "software.factory.run", "sf.run"}:
            if positional:
                args.setdefault("idea", " ".join(positional))
        elif command_name in {"healing.plan", "heal.plan", "selfheal.plan", "healing.run", "heal.run", "selfheal.run"}:
            if positional:
                args.setdefault("command", " ".join(positional))
        elif command_name in {"os.dispatch", "dispatch"}:
            if positional:
                args.setdefault("command", " ".join(positional))
        elif command_name in {"factory.stage", "sf.stage"}:
            if positional:
                args.setdefault("idea", " ".join(positional))
        elif command_name in {"llm.chat", "llm", "model.chat"}:
            if positional:
                args.setdefault("prompt", " ".join(positional))
        elif command_name in {"mcp.call"}:
            if positional:
                args.setdefault("query", " ".join(positional))
        elif command_name in {"website.analyze", "site.analyze", "web.analyze"}:
            if positional:
                args.setdefault("url", " ".join(positional))
        elif command_name in {"repository.read", "repo.read", "github.repository"}:
            if positional:
                args.setdefault("repository", " ".join(positional))
        elif command_name in {"filesystem.search", "mcp.fs.search"}:
            if positional:
                args.setdefault("path", " ".join(positional))
        elif command_name in {"web.search", "brave.search"}:
            if positional:
                args.setdefault("query", " ".join(positional))
        elif command_name in {"agent.show", "agent.run", "agent.validate", "agent.enable", "agent.disable", "agent.delete", "as", "ar", "av", "ae", "ad", "ax"}:
            if positional:
                args.setdefault("id", positional[0])
        elif command_name in {"agent.add", "aa"}:
            if positional:
                args.setdefault("file", positional[0])
        elif command_name in {"agent.update", "au"}:
            if positional:
                args.setdefault("id", positional[0])
            if len(positional) > 1:
                args.setdefault("file", positional[1])
        else:
            if positional:
                args.setdefault("value", " ".join(positional))

        return {"command_name": command_name, "args": args}

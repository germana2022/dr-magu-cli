from __future__ import annotations

from pydantic import BaseModel, Field

from dr_magu.commands.registry import registry


class ToolDefinition(BaseModel):
    """Formal tool metadata exposed to the Brain Context Loader."""

    name: str
    category: str
    description: str
    command: str
    aliases: list[str] = Field(default_factory=list)
    read_only: bool = True
    requires_approval: bool = False


_TOOL_CATEGORIES = {"files", "git", "search", "shell", "repository", "context", "workflow", "runtime", "agent", "brain", "tools", "permissions"}
_MUTATING_TOOLS = {"shell.run", "agent.run", "workflow.run"}


class ToolRegistry:
    """Formal registry that derives tool capabilities from command metadata."""

    def list_tools(self) -> list[ToolDefinition]:
        tools: list[ToolDefinition] = []
        for command in registry.list_commands():
            if command.category not in _TOOL_CATEGORIES:
                continue
            tools.append(ToolDefinition(
                name=command.name,
                category=command.category,
                description=command.description,
                command=command.name,
                aliases=list(command.aliases),
                read_only=command.name not in _MUTATING_TOOLS,
                requires_approval=command.requires_approval,
            ))
        return tools

    def as_result_data(self) -> dict[str, object]:
        tools = [tool.model_dump() for tool in self.list_tools()]
        return {"tools": tools, "count": len(tools)}

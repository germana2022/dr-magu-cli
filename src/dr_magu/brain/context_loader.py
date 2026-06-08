from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dr_magu.agents.registry import AgentRegistry
from dr_magu.brain.model_config import ModelConfigLoader
from dr_magu.commands.registry import registry
from dr_magu.plugins.registry import PluginRegistry
from dr_magu.tools.registry import ToolRegistry
from dr_magu.result import ToolResult


@dataclass(frozen=True)
class BrainContextSnapshot:
    """Runtime snapshot consumed by the AI Orchestrator Brain."""

    summary: dict[str, Any]
    workspace: dict[str, Any]
    commands: list[dict[str, Any]]
    tools: list[dict[str, Any]]
    agents: list[dict[str, Any]]
    plugins: list[dict[str, Any]]
    workflows: list[dict[str, Any]] = field(default_factory=list)
    permissions: dict[str, Any] = field(default_factory=dict)
    default_model: dict[str, Any] = field(default_factory=dict)
    safety: dict[str, Any] = field(default_factory=dict)
    available_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "workspace": self.workspace,
            "commands": self.commands,
            "tools": self.tools,
            "agents": self.agents,
            "plugins": self.plugins,
            "workflows": self.workflows,
            "permissions": self.permissions,
            "default_model": self.default_model,
            "safety": self.safety,
            "available_actions": self.available_actions,
        }


class BrainContextLoader:
    """Load runtime context for the Brain without reading arbitrary files."""

    def __init__(self, workspace_path: str | Path = ".", config: dict[str, Any] | None = None):
        self.workspace_path = Path(workspace_path).resolve()
        self.config = config or {}

    def load(self) -> BrainContextSnapshot:
        commands = [
            {
                "name": command.name,
                "description": command.description,
                "category": command.category,
                "aliases": list(command.aliases),
            }
            for command in registry.list_commands()
        ]

        tools = [
            {
                "name": tool.name,
                "description": tool.description,
                "category": tool.category,
                "risk_level": getattr(tool, "risk_level", "unknown"),
            }
            for tool in ToolRegistry().list_tools()
        ]

        agents = [
            {
                "id": agent.id,
                "name": agent.name,
                "workflow": agent.workflow,
                "enabled": agent.enabled,
                "plugin_id": agent.plugin_id,
                "requires_llm": agent.requires_llm,
            }
            for agent in AgentRegistry(self.workspace_path).list()
        ]

        plugins = [
            {
                "id": plugin.id,
                "name": plugin.name,
                "enabled": plugin.enabled,
                "domain": plugin.domain,
                "agents": list(plugin.provides.agents),
                "workflows": list(plugin.provides.workflows),
                "tools": list(plugin.provides.tools),
            }
            for plugin in PluginRegistry(self.workspace_path).list()
        ]

        default_model = ModelConfigLoader(self.workspace_path).default_model().to_dict()

        available_actions = [
            "repo.scan",
            "context.generate",
            "workflow.run repository.context",
            "agent.run repository-analyzer",
            "brain.context",
        ]

        summary = {
            "brain_ready": True,
            "command_count": len(commands),
            "tool_count": len(tools),
            "agent_count": len(agents),
            "plugin_count": len(plugins),
            "default_model": default_model.get("model"),
        }

        return BrainContextSnapshot(
            summary=summary,
            workspace={
                "path": str(self.workspace_path),
                "exists": self.workspace_path.exists(),
                "is_directory": self.workspace_path.is_dir(),
            },
            commands=commands,
            tools=tools,
            agents=agents,
            plugins=plugins,
            default_model=default_model,
            safety={
                "llm_is_planner_only": True,
                "plan_validation_required": True,
                "direct_tool_execution_by_llm": False,
            },
            available_actions=available_actions,
        )

    def load_context(self) -> BrainContextSnapshot:
        return self.load()

    def load_result(self) -> ToolResult:
        """Return a command-friendly ToolResult payload."""
        return ToolResult(success=True, tool="brain.context", data=self.load().to_dict())


def load_brain_context(workspace_path: str | None = None) -> dict[str, Any]:
    """Load a dictionary context for planner-oriented code."""
    return BrainContextLoader(workspace_path or ".").load().to_dict()

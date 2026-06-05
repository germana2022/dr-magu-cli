from __future__ import annotations

from pathlib import Path

from dr_magu.agents.registry import AgentRegistry
from dr_magu.brain.model_config import ModelConfigLoader
from dr_magu.brain.models import BrainContextSnapshot
from dr_magu.config import load_config
from dr_magu.result import ToolResult
from dr_magu.runtime.inspector import RuntimeInspector
from dr_magu.security.permission_context import PermissionContextReader
from dr_magu.tools.registry import ToolRegistry
from dr_magu.plugins.registry import PluginRegistry


class BrainContextLoader:
    """Loads the complete local architecture context for the Orchestrator Brain.

    This class does not call an LLM. It prepares the structured inventory that a
    future prompt planner will send to the default Brain model.
    """

    def __init__(self, workspace_path: str | Path, config: dict | None = None) -> None:
        self.workspace_path = str(Path(workspace_path).resolve())
        self.config = config if config is not None else load_config()

    def load(self) -> BrainContextSnapshot:
        runtime = RuntimeInspector(self.workspace_path, config=self.config).inspect()
        default_model = ModelConfigLoader(self.workspace_path).default_model()
        agent_registry = AgentRegistry(self.workspace_path)
        agents = [agent.model_dump() for agent in agent_registry.list()]
        tools = [tool.model_dump(mode="json") for tool in ToolRegistry().list_tools()]
        permissions = PermissionContextReader(self.config).read()
        plugins = [plugin.model_dump() for plugin in PluginRegistry(self.workspace_path).list()]

        snapshot = BrainContextSnapshot(
            workspace=runtime.workspace.model_dump(),
            session=runtime.session.model_dump(),
            commands=[command.model_dump() for command in runtime.commands],
            workflows=[workflow.model_dump() for workflow in runtime.workflows],
            tools=tools,
            permissions=permissions.model_dump(),
            agents=agents,
            plugins=plugins,
            default_model=default_model.model_dump(),
            summary={
                "command_count": len(runtime.commands),
                "workflow_count": len(runtime.workflows),
                "tool_count": len(tools),
                "agent_count": len(agents),
                "plugin_count": len(plugins),
                "enabled_plugin_count": len([plugin for plugin in plugins if plugin.get("enabled")]),
                "brain_ready": True,
                "llm_configured": default_model.api_key_configured,
                "default_provider": default_model.provider,
                "default_model": default_model.model,
                "llm_calls_enabled": False,
                "contract_version": "0.9.4",
                "tool_contracts_enabled": True,
                "brain_plan_schema_enabled": True,
                "plan_validator_enabled": True,
            },
            contracts={
                "tool_contracts_enabled": True,
                "brain_plan_schema_enabled": True,
                "plan_validator_enabled": True,
                "permission_policy_schema_enabled": True,
            },
        )
        return snapshot

    def load_result(self) -> ToolResult:
        return ToolResult(success=True, tool="brain.context", data=self.load().model_dump(mode="json"))

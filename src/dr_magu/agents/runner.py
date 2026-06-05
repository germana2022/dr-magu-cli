from __future__ import annotations

from pathlib import Path

from dr_magu.agents.manager import AgentManager
from dr_magu.agents.registry import AgentRegistry
from dr_magu.result import ToolResult
from dr_magu.workflows.runner import WorkflowRunner


class AgentRunner:
    """Runs and manages configured agents.

    v0.9.2 keeps agent execution deterministic. Agent lifecycle operations are
    stored as workspace-level overrides so plugin files remain untouched.
    """

    def __init__(self, workspace_path: str | Path) -> None:
        self.workspace_path = str(Path(workspace_path).resolve())
        self.registry = AgentRegistry(self.workspace_path)
        self.manager = AgentManager(self.workspace_path)

    def list_agents(self, include_disabled: bool = True, include_deleted: bool = False) -> ToolResult:
        agents = [agent.model_dump() for agent in self.registry.list(include_disabled=include_disabled, include_deleted=include_deleted)]
        return ToolResult(success=True, tool="agent.list", data={"agents": agents, "count": len(agents)})

    def show_agent(self, agent_id: str) -> ToolResult:
        agent = self.registry.get(agent_id, include_deleted=True)
        return ToolResult(success=True, tool="agent.show", data=agent.model_dump())

    def validate_agent(self, agent_id: str) -> ToolResult:
        return self.manager.validate(agent_id)

    def enable_agent(self, agent_id: str) -> ToolResult:
        return self.manager.enable(agent_id)

    def disable_agent(self, agent_id: str) -> ToolResult:
        return self.manager.disable(agent_id)

    def delete_agent(self, agent_id: str) -> ToolResult:
        return self.manager.delete(agent_id)

    def add_agent_from_file(self, file_path: str | Path) -> ToolResult:
        return self.manager.add_from_file(file_path)

    def update_agent_from_file(self, agent_id: str, file_path: str | Path) -> ToolResult:
        return self.manager.update_from_file(agent_id, file_path)

    def run_agent(self, agent_id: str) -> ToolResult:
        agent = self.registry.get(agent_id)
        if agent.deleted:
            return ToolResult(success=False, tool="agent.run", errors=[f"Agent '{agent.id}' is deleted."])
        if not agent.enabled:
            return ToolResult(success=False, tool="agent.run", errors=[f"Agent '{agent.id}' is disabled."])
        workflow_result = WorkflowRunner(self.workspace_path).run(agent.workflow)
        data = {
            "agent": agent.model_dump(),
            "workflow_result": workflow_result.data or {},
            "workflow_success": workflow_result.success,
        }
        if not workflow_result.success:
            return ToolResult(success=False, tool="agent.run", data=data, errors=workflow_result.errors)
        return ToolResult(success=True, tool="agent.run", data=data)

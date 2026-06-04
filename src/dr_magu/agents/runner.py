from __future__ import annotations

from pathlib import Path

from dr_magu.agents.registry import AgentRegistry
from dr_magu.result import ToolResult
from dr_magu.workflows.runner import WorkflowRunner


class AgentRunner:
    """Runs configured agents by dispatching their bound workflow.

    v0.9.0 does not call an LLM. Agent execution is deterministic and delegates
    to the existing workflow runtime. LLM configuration is resolved and exposed
    as metadata so v0.10.0 can plug in the actual planner/executor safely.
    """

    def __init__(self, workspace_path: str | Path) -> None:
        self.workspace_path = str(Path(workspace_path).resolve())
        self.registry = AgentRegistry(self.workspace_path)

    def list_agents(self) -> ToolResult:
        agents = [agent.model_dump() for agent in self.registry.list()]
        return ToolResult(success=True, tool="agent.list", data={"agents": agents, "count": len(agents)})

    def show_agent(self, agent_id: str) -> ToolResult:
        agent = self.registry.get(agent_id)
        return ToolResult(success=True, tool="agent.show", data=agent.model_dump())

    def run_agent(self, agent_id: str) -> ToolResult:
        agent = self.registry.get(agent_id)
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

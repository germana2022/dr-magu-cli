from __future__ import annotations

from pathlib import Path

from dr_magu.agents.manager import AgentManager
from dr_magu.agents.registry import AgentRegistry
from dr_magu.agents.runtime import AgentRuntime
from dr_magu.result import ToolResult


class AgentRunner:
    """Runs and manages configured agents.

    v2.6.0 promotes the earlier registry/delegation layer into an operational
    Agent Runtime with create/run/status/stop/context/history capabilities.
    Existing add/update/enable/disable/delete commands continue to use
    workspace-level overrides so plugin files remain untouched.
    """

    def __init__(self, workspace_path: str | Path) -> None:
        self.workspace_path = str(Path(workspace_path).resolve())
        self.registry = AgentRegistry(self.workspace_path)
        self.manager = AgentManager(self.workspace_path)
        self.runtime = AgentRuntime(self.workspace_path)

    def list_agents(self, include_disabled: bool = True, include_deleted: bool = False) -> ToolResult:
        agents = [agent.model_dump() for agent in self.registry.list(include_disabled=include_disabled, include_deleted=include_deleted)]
        return ToolResult(success=True, tool="agent.list", data={"agents": agents, "count": len(agents)})

    def show_agent(self, agent_id: str) -> ToolResult:
        agent = self.registry.get(agent_id, include_deleted=True)
        return ToolResult(success=True, tool="agent.show", data=agent.model_dump())

    def create_agent(
        self,
        agent_id: str,
        *,
        name: str | None = None,
        role: str = "general",
        workflow: str = "research-brief",
        description: str = "",
        capabilities: list[str] | None = None,
        skills: list[str] | None = None,
        aliases: list[str] | None = None,
        requires_llm: bool = False,
    ) -> ToolResult:
        return self.runtime.create(
            agent_id,
            name=name,
            role=role,
            workflow=workflow,
            description=description,
            capabilities=capabilities,
            skills=skills,
            aliases=aliases,
            requires_llm=requires_llm,
        )

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

    def run_agent(self, agent_id: str, prompt: str = "", *, dry_run: bool = False) -> ToolResult:
        return self.runtime.run(agent_id, prompt=prompt, dry_run=dry_run)

    def stop_agent(self, agent_id: str, reason: str = "Manual stop requested.") -> ToolResult:
        return self.runtime.stop(agent_id, reason=reason)

    def status_agent(self, agent_id: str) -> ToolResult:
        return self.runtime.status(agent_id)

    def history(self, agent_id: str | None = None, limit: int = 20) -> ToolResult:
        return self.runtime.history(agent_id=agent_id, limit=limit)

    def context(self, agent_id: str) -> ToolResult:
        return self.runtime.context(agent_id)

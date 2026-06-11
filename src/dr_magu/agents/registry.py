from __future__ import annotations

from pathlib import Path

from dr_magu.agents.loader import AgentConfigLoader
from dr_magu.agents.models import AgentDefinition, ResolvedAgentDefinition
from dr_magu.brain.model_config import ModelConfigLoader, ModelResolver


class AgentRegistry:
    """Dynamic agent registry loaded from YAML configuration."""

    def __init__(self, workspace_path: str | Path) -> None:
        self.workspace_path = Path(workspace_path).resolve()
        self.default_model = ModelConfigLoader(self.workspace_path).default_model()
        self.model_resolver = ModelResolver(self.default_model)
        self._agents = AgentConfigLoader(self.workspace_path).load()

    def list(self, include_disabled: bool = True, include_deleted: bool = False) -> list[ResolvedAgentDefinition]:
        agents = self._agents
        if not include_disabled:
            agents = [agent for agent in agents if agent.enabled]
        if not include_deleted:
            agents = [agent for agent in agents if not agent.deleted]
        return [self._resolve(agent) for agent in agents]

    def get(self, agent_id: str, include_deleted: bool = False) -> ResolvedAgentDefinition:
        for agent in self._agents:
            if agent.deleted and not include_deleted:
                continue
            names = {agent.id, *agent.aliases}
            if agent_id in names:
                return self._resolve(agent)
        available = ", ".join(sorted(agent.id for agent in self._agents if include_deleted or not agent.deleted)) or "none"
        raise KeyError(f"Unknown agent '{agent_id}'. Available agents: {available}")

    def _resolve(self, agent: AgentDefinition) -> ResolvedAgentDefinition:
        return ResolvedAgentDefinition(
            id=agent.id,
            name=agent.name,
            description=agent.description,
            role=agent.role,
            workflow=agent.workflow,
            enabled=agent.enabled,
            deleted=agent.deleted,
            requires_llm=agent.requires_llm,
            capabilities=list(agent.capabilities),
            skills=list(getattr(agent, "skills", []) or []),
            aliases=list(agent.aliases),
            model=self.model_resolver.resolve(agent.model),
            plugin_id=agent.plugin_id,
            source=agent.source,
        )

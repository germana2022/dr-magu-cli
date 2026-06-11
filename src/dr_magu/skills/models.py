from __future__ import annotations

from pydantic import BaseModel, Field


class SkillDefinition(BaseModel):
    """Reusable capability bundle that can be attached to one or more agents."""

    id: str
    name: str
    description: str
    category: str
    capabilities: list[str] = Field(default_factory=list)
    commands: list[str] = Field(default_factory=list)
    mcp_servers: list[str] = Field(default_factory=list)
    workflows: list[str] = Field(default_factory=list)
    compatible_roles: list[str] = Field(default_factory=list)
    requires_llm: bool = False
    risk_level: str = "low"
    enabled: bool = True


class AgentSkillBinding(BaseModel):
    """Persisted skill binding for an agent."""

    agent_id: str
    skills: list[str] = Field(default_factory=list)

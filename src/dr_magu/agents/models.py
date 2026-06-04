from __future__ import annotations

from pydantic import BaseModel, Field

from dr_magu.brain.models import ResolvedModelConfig


class AgentDefinition(BaseModel):
    """Declarative agent definition loaded from config/agents.yaml."""

    id: str
    name: str
    description: str
    role: str
    workflow: str
    enabled: bool = True
    requires_llm: bool = False
    capabilities: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)
    model: dict[str, object] = Field(default_factory=dict)


class ResolvedAgentDefinition(BaseModel):
    """Agent definition with model fallback resolved against the Brain default."""

    id: str
    name: str
    description: str
    role: str
    workflow: str
    enabled: bool
    requires_llm: bool
    capabilities: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)
    model: ResolvedModelConfig

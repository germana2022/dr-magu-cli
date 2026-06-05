from __future__ import annotations

from pydantic import BaseModel, Field

from dr_magu.brain.models import ResolvedModelConfig


class AgentDefinition(BaseModel):
    """Declarative agent definition loaded from plugins, project config, or workspace config."""

    id: str
    name: str
    description: str
    role: str
    workflow: str
    enabled: bool = True
    deleted: bool = False
    requires_llm: bool = False
    capabilities: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)
    model: dict[str, object] = Field(default_factory=dict)
    plugin_id: str | None = None
    source: str = "project"


class ResolvedAgentDefinition(BaseModel):
    """Agent definition with model fallback resolved against the Brain default."""

    id: str
    name: str
    description: str
    role: str
    workflow: str
    enabled: bool
    deleted: bool = False
    requires_llm: bool
    capabilities: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)
    model: ResolvedModelConfig
    plugin_id: str | None = None
    source: str = "project"

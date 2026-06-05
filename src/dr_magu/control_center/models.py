from __future__ import annotations

from pydantic import BaseModel, Field


class ControlCenterSection(BaseModel):
    """Summary section displayed by the Dr Magu Control Center."""

    name: str
    count: int = 0
    enabled_count: int | None = None
    status: str = "available"
    description: str = ""


class PluginImpact(BaseModel):
    """Plugin impact summary across agents, workflows, tools, commands, and schedules."""

    plugin_id: str
    name: str
    enabled: bool
    domain: str = "general"
    status: str = "healthy"
    agents: list[str] = Field(default_factory=list)
    workflows: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    commands: list[str] = Field(default_factory=list)
    schedules: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class ControlCenterDashboard(BaseModel):
    """Aggregated dashboard consumed by CLI, TUI, and the future Brain UI."""

    workspace_path: str
    sections: list[ControlCenterSection] = Field(default_factory=list)
    plugins: list[PluginImpact] = Field(default_factory=list)
    brain: dict = Field(default_factory=dict)
    permissions: dict = Field(default_factory=dict)
    schedules: dict = Field(default_factory=dict)

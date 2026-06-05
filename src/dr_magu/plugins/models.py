from __future__ import annotations

from pydantic import BaseModel, Field


class PluginProvides(BaseModel):
    """Resources declared by a plugin manifest."""

    agents: list[str] = Field(default_factory=list)
    workflows: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    commands: list[str] = Field(default_factory=list)
    schedules: list[str] = Field(default_factory=list)


class PluginPermissionPolicy(BaseModel):
    """Permission policy summary declared by a plugin."""

    shell: str = "restricted"
    write_files: str = "approval_required"
    delete_files: str = "blocked"
    git_push: str = "blocked"
    external_network: str = "restricted"


class PluginDefinition(BaseModel):
    """Normalized plugin manifest loaded from plugin.yaml."""

    id: str
    name: str
    version: str = "0.1.0"
    enabled: bool = True
    description: str = ""
    domain: str = "general"
    path: str = ""
    provides: PluginProvides = Field(default_factory=PluginProvides)
    permissions: PluginPermissionPolicy = Field(default_factory=PluginPermissionPolicy)
    validation_errors: list[str] = Field(default_factory=list)


class PluginValidationResult(BaseModel):
    """Validation result for a local plugin."""

    plugin_id: str
    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

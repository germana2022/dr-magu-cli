from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class WorkspaceRuntimeInfo(BaseModel):
    """Runtime metadata about the selected workspace."""

    path: str
    exists: bool
    is_directory: bool
    is_git_repository: bool
    dr_magu_path: str
    has_dr_magu_directory: bool


class SessionRuntimeInfo(BaseModel):
    """Runtime metadata about the current persistent session."""

    id: str | None = None
    status: str | None = None
    command_count: int = 0
    event_count: int = 0
    updated_at: str | None = None


class CommandRuntimeInfo(BaseModel):
    """Serializable command metadata for brain context loading."""

    name: str
    category: str
    description: str
    aliases: list[str] = Field(default_factory=list)
    requires_workspace: bool = True
    requires_approval: bool = False


class WorkflowRuntimeInfo(BaseModel):
    """Serializable workflow metadata for brain context loading."""

    name: str
    description: str
    workflow_type: str
    requires_llm: bool = False
    aliases: list[str] = Field(default_factory=list)


class ToolRuntimeInfo(BaseModel):
    """Tool capability metadata exposed through formal contracts."""

    name: str
    category: str
    description: str
    command: str
    aliases: list[str] = Field(default_factory=list)
    read_only: bool = True
    requires_approval: bool = False
    risk_level: str = "low"
    permission_mode: str = "allowed"
    background_allowed: bool = True
    interactive_only: bool = False
    input_schema: list[dict[str, Any]] = Field(default_factory=list)
    output_schema: list[dict[str, Any]] = Field(default_factory=list)


class PermissionRuntimeInfo(BaseModel):
    """Effective runtime permission summary."""

    file_read: bool = False
    file_write: bool = False
    file_delete: bool = False
    shell_run: bool = False
    git_status: bool = False
    git_diff: bool = False
    git_commit: bool = False
    git_push: bool = False
    blocked_shell_patterns: list[str] = Field(default_factory=list)
    policies: dict[str, Any] = Field(default_factory=dict)
    default_policy_mode: str = "allowed"


class RuntimeContextSnapshot(BaseModel):
    """Unified runtime snapshot consumed by the future Orchestrator Brain."""

    workspace: WorkspaceRuntimeInfo
    session: SessionRuntimeInfo
    commands: list[CommandRuntimeInfo] = Field(default_factory=list)
    workflows: list[WorkflowRuntimeInfo] = Field(default_factory=list)
    tools: list[ToolRuntimeInfo] = Field(default_factory=list)
    permissions: PermissionRuntimeInfo
    agents: list[dict[str, Any]] = Field(default_factory=list)
    plugins: list[dict[str, Any]] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)
    contracts: dict[str, Any] = Field(default_factory=dict)

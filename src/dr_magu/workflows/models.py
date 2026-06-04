from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

WorkflowStatus = Literal["pending", "running", "completed", "failed"]


def utc_now_iso() -> str:
    """Return the current UTC timestamp in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat()


def new_run_id() -> str:
    """Return a compact workflow run id suitable for file-system paths."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"{timestamp}-{uuid4().hex[:6]}"


class WorkflowDefinition(BaseModel):
    """Registered workflow metadata."""

    name: str
    description: str
    workflow_type: str = "deterministic"
    requires_llm: bool = False
    aliases: list[str] = Field(default_factory=list)


class WorkflowEvent(BaseModel):
    """Append-only workflow execution event."""

    timestamp: str = Field(default_factory=utc_now_iso)
    type: str
    workflow: str | None = None
    run_id: str | None = None
    node: str | None = None
    message: str | None = None
    duration_ms: int | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class WorkflowRunMetadata(BaseModel):
    """Persisted workflow run metadata."""

    id: str
    workflow: str
    session_id: str | None = None
    workspace_path: str
    status: WorkflowStatus = "pending"
    started_at: str = Field(default_factory=utc_now_iso)
    completed_at: str | None = None
    error: str | None = None
    duration_ms: int | None = None


class RepositoryContextWorkflowState(BaseModel):
    """State produced by the repository.context workflow."""

    workflow: str = "repository.context"
    workspace_path: str
    session_id: str | None = None
    scan_path: str | None = None
    context_path: str | None = None
    generated_files: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

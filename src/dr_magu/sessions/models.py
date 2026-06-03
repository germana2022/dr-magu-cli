from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

SessionStatus = Literal["active", "closed", "deleted"]


def utc_now_iso() -> str:
    """Return the current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


class SessionMetadata(BaseModel):
    """Persistent metadata for a Dr Magu workspace session."""

    id: str
    workspace_path: str
    created_at: str
    updated_at: str
    status: SessionStatus = "active"
    command_count: int = 0
    event_count: int = 0


class CommandRecord(BaseModel):
    """Safe command execution metadata persisted in commands.jsonl.

    Full stdout, file contents, prompts, and secrets are intentionally not stored
    in this version. The record only captures operational metadata.
    """

    timestamp: str = Field(default_factory=utc_now_iso)
    command: str
    tool: str
    success: bool
    duration_ms: int | None = None


class EventRecord(BaseModel):
    """Session event persisted in events.jsonl."""

    timestamp: str = Field(default_factory=utc_now_iso)
    type: str
    details: dict[str, Any] = Field(default_factory=dict)

from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field


OutputFormat = Literal["human", "json"]


class CommandContext(BaseModel):
    """Execution context shared by every command handler."""

    workspace_path: str = "."
    output_format: OutputFormat = "human"
    config: dict[str, Any] = Field(default_factory=dict)
    session_id: str | None = None

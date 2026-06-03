from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    success: bool
    tool: str
    data: dict[str, Any] | None = None
    errors: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

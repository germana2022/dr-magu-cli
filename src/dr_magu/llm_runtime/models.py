from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class LLMMessage:
    """Chat message passed to an LLM provider."""

    role: str
    content: str

    def to_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass(frozen=True)
class LLMResponse:
    """Normalized LLM response."""

    content: str
    provider: str
    model: str
    success: bool = True
    error: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "content": self.content,
            "provider": self.provider,
            "model": self.model,
            "success": self.success,
            "error": self.error,
            "raw": self.raw,
            "created_at": self.created_at,
        }

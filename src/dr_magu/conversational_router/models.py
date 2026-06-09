from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RoutedCommand:
    """Natural-language command routing result."""

    intent: str
    command: str | None
    confidence: float
    reason: str
    extracted: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "command": self.command,
            "confidence": self.confidence,
            "reason": self.reason,
            "extracted": self.extracted,
        }

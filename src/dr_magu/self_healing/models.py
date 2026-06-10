from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class HealingPolicy:
    """Policy controlling retry, fallback, and escalation."""

    max_retries: int = 1
    fallback_command: str | None = None
    escalate_on_failure: bool = True
    approval_required: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_retries": self.max_retries,
            "fallback_command": self.fallback_command,
            "escalate_on_failure": self.escalate_on_failure,
            "approval_required": self.approval_required,
        }


@dataclass(frozen=True)
class HealingAttempt:
    """Single self-healing execution attempt."""

    index: int
    command: str
    status: str
    tool: str
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "command": self.command,
            "status": self.status,
            "tool": self.tool,
            "errors": self.errors,
        }


@dataclass(frozen=True)
class HealingReport:
    """Self-healing execution report."""

    command: str
    success: bool
    status: str
    attempts: list[HealingAttempt]
    policy: HealingPolicy
    escalated: bool = False
    fallback_used: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "command": self.command,
            "success": self.success,
            "status": self.status,
            "attempts": [attempt.to_dict() for attempt in self.attempts],
            "policy": self.policy.to_dict(),
            "escalated": self.escalated,
            "fallback_used": self.fallback_used,
            "created_at": self.created_at,
        }

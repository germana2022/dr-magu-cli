from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


STATUS_PASS = "pass"
STATUS_WARN = "warn"
STATUS_FAIL = "fail"


@dataclass(frozen=True)
class StabilizationCheck:
    """Single platform stabilization check result."""

    name: str
    status: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "message": self.message,
            "details": self.details,
        }


@dataclass(frozen=True)
class StabilizationReport:
    """Aggregated platform stabilization report."""

    version: str
    status: str
    checks: list[StabilizationCheck]

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "status": self.status,
            "checks": [check.to_dict() for check in self.checks],
        }

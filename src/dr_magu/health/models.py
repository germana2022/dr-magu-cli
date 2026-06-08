from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class HealthCheckResult:
    name: str
    status: str
    message: str
    details: dict = field(default_factory=dict)


@dataclass(frozen=True)
class HealthReport:
    status: str
    checks: list[HealthCheckResult]

    @property
    def passed(self) -> bool:
        return self.status == "healthy"

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "checks": [
                {
                    "name": check.name,
                    "status": check.status,
                    "message": check.message,
                    "details": check.details,
                }
                for check in self.checks
            ],
        }

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any
from uuid import uuid4


SCHEDULE_ENABLED = "enabled"
SCHEDULE_DISABLED = "disabled"
SCHEDULE_DELETED = "deleted"


@dataclass(frozen=True)
class ScheduledTask:
    """A persisted scheduled task definition."""

    id: str
    name: str
    command: str
    cron: str
    timezone: str = "UTC"
    enabled: bool = True
    status: str = SCHEDULE_ENABLED
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str | None = None
    last_run_at: str | None = None
    next_run_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def create(name: str, command: str, cron: str, timezone_name: str = "UTC", description: str = "") -> "ScheduledTask":
        task = ScheduledTask(
            id=uuid4().hex[:12],
            name=name,
            command=command,
            cron=cron,
            timezone=timezone_name,
            description=description,
        )
        return task.with_next_run()

    def with_next_run(self) -> "ScheduledTask":
        return self.update(next_run_at=estimate_next_run(self.cron))

    def update(self, **changes: Any) -> "ScheduledTask":
        payload = self.to_dict()
        payload.update(changes)
        payload["updated_at"] = datetime.now(timezone.utc).isoformat()
        return ScheduledTask.from_dict(payload)

    def mark_run(self) -> "ScheduledTask":
        now = datetime.now(timezone.utc).isoformat()
        return self.update(last_run_at=now, next_run_at=estimate_next_run(self.cron))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "command": self.command,
            "cron": self.cron,
            "timezone": self.timezone,
            "enabled": self.enabled,
            "status": self.status,
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_run_at": self.last_run_at,
            "next_run_at": self.next_run_at,
            "metadata": self.metadata,
        }

    @staticmethod
    def from_dict(payload: dict[str, Any]) -> "ScheduledTask":
        return ScheduledTask(
            id=str(payload["id"]),
            name=str(payload["name"]),
            command=str(payload["command"]),
            cron=str(payload["cron"]),
            timezone=str(payload.get("timezone") or "UTC"),
            enabled=bool(payload.get("enabled", True)),
            status=str(payload.get("status") or SCHEDULE_ENABLED),
            description=str(payload.get("description") or ""),
            created_at=str(payload.get("created_at") or datetime.now(timezone.utc).isoformat()),
            updated_at=payload.get("updated_at"),
            last_run_at=payload.get("last_run_at"),
            next_run_at=payload.get("next_run_at"),
            metadata=dict(payload.get("metadata") or {}),
        )


def estimate_next_run(cron: str) -> str:
    """Estimate a conservative next run timestamp for common cron expressions.

    This is not a full cron parser. It provides deterministic scheduling metadata
    for the runtime foundation and can be replaced by a full cron engine later.
    """
    now = datetime.now(timezone.utc)
    normalized = " ".join(cron.strip().split())

    if normalized.startswith("@hourly"):
        return (now + timedelta(hours=1)).isoformat()
    if normalized.startswith("@daily"):
        return (now + timedelta(days=1)).isoformat()
    if normalized.startswith("@weekly"):
        return (now + timedelta(weeks=1)).isoformat()

    parts = normalized.split()
    if len(parts) == 5:
        minute, hour, day, month, weekday = parts
        if minute.startswith("*/"):
            try:
                interval = max(1, int(minute[2:]))
                return (now + timedelta(minutes=interval)).isoformat()
            except ValueError:
                pass
        if hour == "*" and day == "*" and month == "*" and weekday == "*":
            return (now + timedelta(hours=1)).isoformat()
        if day == "*" and month == "*" and weekday == "*":
            return (now + timedelta(days=1)).isoformat()

    return (now + timedelta(days=1)).isoformat()

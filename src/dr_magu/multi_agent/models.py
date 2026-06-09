from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class AgentTask:
    """Single agent task inside an orchestration."""

    agent_id: str
    command: str
    description: str = ""
    depends_on: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "command": self.command,
            "description": self.description,
            "depends_on": self.depends_on,
        }


@dataclass(frozen=True)
class OrchestrationPlan:
    """Resolved multi-agent orchestration plan."""

    name: str
    mode: str
    tasks: list[AgentTask]
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "mode": self.mode,
            "tasks": [task.to_dict() for task in self.tasks],
            "created_at": self.created_at,
        }

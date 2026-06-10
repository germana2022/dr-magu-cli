from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class FactoryStage:
    """A stage in the autonomous software factory."""

    id: str
    title: str
    command: str
    description: str
    artifact_name: str
    depends_on: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "command": self.command,
            "description": self.description,
            "artifact_name": self.artifact_name,
            "depends_on": self.depends_on,
        }


@dataclass(frozen=True)
class FactoryPlan:
    """End-to-end software factory plan."""

    name: str
    idea: str
    stages: list[FactoryStage]
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "idea": self.idea,
            "stages": [stage.to_dict() for stage in self.stages],
            "created_at": self.created_at,
        }

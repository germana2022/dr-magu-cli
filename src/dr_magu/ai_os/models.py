from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class OSCapability:
    """A capability exposed by the AI Operating System layer."""

    id: str
    name: str
    command: str
    layer: str
    description: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "command": self.command,
            "layer": self.layer,
            "description": self.description,
        }


@dataclass(frozen=True)
class OSState:
    """AI OS state snapshot."""

    version: str
    layers: list[str]
    capabilities: list[OSCapability]
    health: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "layers": self.layers,
            "capabilities": [capability.to_dict() for capability in self.capabilities],
            "health": self.health,
            "created_at": self.created_at,
        }

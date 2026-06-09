from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class WorkflowContext:
    """Mutable context shared between workflow steps."""

    values: dict[str, Any] = field(default_factory=dict)

    def set(self, key: str, value: Any) -> None:
        self.values[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self.values.get(key, default)

    def to_dict(self) -> dict[str, Any]:
        return dict(self.values)

    @staticmethod
    def from_dict(payload: dict[str, Any]) -> "WorkflowContext":
        return WorkflowContext(values=dict(payload or {}))

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


ACTION_PENDING = "pending"
ACTION_APPROVED = "approved"
ACTION_RUNNING = "running"
ACTION_COMPLETED = "completed"
ACTION_FAILED = "failed"
ACTION_BLOCKED = "blocked"

PLAN_PENDING = "pending"
PLAN_APPROVED = "approved"
PLAN_RUNNING = "running"
PLAN_COMPLETED = "completed"
PLAN_FAILED = "failed"
PLAN_BLOCKED = "blocked"


@dataclass(frozen=True)
class ExecutionAction:
    """Single execution action."""

    type: str
    target: str = ""
    command: str = ""
    content: str = ""
    message: str = ""
    requires_approval: bool = False
    status: str = ACTION_PENDING
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "target": self.target,
            "command": self.command,
            "content": self.content,
            "message": self.message,
            "requires_approval": self.requires_approval,
            "status": self.status,
            "metadata": self.metadata,
        }

    @staticmethod
    def from_dict(payload: dict[str, Any]) -> "ExecutionAction":
        return ExecutionAction(
            type=str(payload.get("type") or ""),
            target=str(payload.get("target") or ""),
            command=str(payload.get("command") or ""),
            content=str(payload.get("content") or ""),
            message=str(payload.get("message") or ""),
            requires_approval=bool(payload.get("requires_approval", False)),
            status=str(payload.get("status") or ACTION_PENDING),
            metadata=dict(payload.get("metadata") or {}),
        )


@dataclass(frozen=True)
class ExecutionPlan:
    """Execution plan generated before runtime execution."""

    plan_id: str
    title: str
    description: str
    actions: list[ExecutionAction] = field(default_factory=list)
    status: str = PLAN_PENDING
    approval_id: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str | None = None

    @staticmethod
    def create(title: str, description: str, actions: list[ExecutionAction]) -> "ExecutionPlan":
        return ExecutionPlan(
            plan_id=f"plan-{uuid4().hex[:12]}",
            title=title,
            description=description,
            actions=actions,
        )

    def update(self, **changes: Any) -> "ExecutionPlan":
        payload = self.to_dict()
        payload.update(changes)
        payload["updated_at"] = datetime.now(timezone.utc).isoformat()
        return ExecutionPlan.from_dict(payload)

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "title": self.title,
            "description": self.description,
            "actions": [action.to_dict() for action in self.actions],
            "status": self.status,
            "approval_id": self.approval_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @staticmethod
    def from_dict(payload: dict[str, Any]) -> "ExecutionPlan":
        return ExecutionPlan(
            plan_id=str(payload["plan_id"]),
            title=str(payload.get("title") or ""),
            description=str(payload.get("description") or ""),
            actions=[ExecutionAction.from_dict(action) for action in payload.get("actions", [])],
            status=str(payload.get("status") or PLAN_PENDING),
            approval_id=payload.get("approval_id"),
            created_at=str(payload.get("created_at") or datetime.now(timezone.utc).isoformat()),
            updated_at=payload.get("updated_at"),
        )


@dataclass(frozen=True)
class ExecutionEvent:
    """Execution log event."""

    event_type: str
    message: str
    action_type: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "message": self.message,
            "action_type": self.action_type,
            "timestamp": self.timestamp,
            "data": self.data,
        }

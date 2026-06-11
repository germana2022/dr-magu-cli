from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


WORKFLOW_PENDING = "pending"
WORKFLOW_RUNNING = "running"
WORKFLOW_WAITING_FOR_APPROVAL = "waiting_for_approval"
WORKFLOW_COMPLETED = "completed"
WORKFLOW_FAILED = "failed"
WORKFLOW_CANCELLED = "cancelled"

STEP_PENDING = "pending"
STEP_RUNNING = "running"
STEP_COMPLETED = "completed"
STEP_FAILED = "failed"
STEP_SKIPPED = "skipped"


@dataclass(frozen=True)
class WorkflowStep:
    """Single workflow step definition.

    v2.5.0 keeps command steps as the stable execution primitive and adds
    optional operational metadata used by the orchestration engine.
    """

    id: str
    name: str
    type: str = "command"
    command: str = ""
    description: str = ""
    enabled: bool = True
    requires_approval: bool = False
    timeout_seconds: int | None = None
    continue_on_error: bool = False
    output_key: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "command": self.command,
            "description": self.description,
            "enabled": self.enabled,
            "requires_approval": self.requires_approval,
            "timeout_seconds": self.timeout_seconds,
            "continue_on_error": self.continue_on_error,
            "output_key": self.output_key,
        }

    @staticmethod
    def from_dict(payload: dict[str, Any]) -> "WorkflowStep":
        return WorkflowStep(
            id=str(payload["id"]),
            name=str(payload.get("name") or payload["id"]),
            type=str(payload.get("type") or "command"),
            command=str(payload.get("command") or ""),
            description=str(payload.get("description") or ""),
            enabled=bool(payload.get("enabled", True)),
            requires_approval=bool(payload.get("requires_approval", False)),
            timeout_seconds=(int(payload["timeout_seconds"]) if payload.get("timeout_seconds") is not None else None),
            continue_on_error=bool(payload.get("continue_on_error", False)),
            output_key=(str(payload.get("output_key")) if payload.get("output_key") else None),
        )


@dataclass(frozen=True)
class WorkflowDefinition:
    """Workflow definition consumed by the orchestration engine."""

    id: str
    name: str
    description: str = ""
    version: str = "1.0"
    tags: list[str] = field(default_factory=list)
    inputs: dict[str, Any] = field(default_factory=dict)
    steps: list[WorkflowStep] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "tags": list(self.tags),
            "inputs": dict(self.inputs),
            "steps": [step.to_dict() for step in self.steps],
        }

    @staticmethod
    def from_dict(payload: dict[str, Any]) -> "WorkflowDefinition":
        return WorkflowDefinition(
            id=str(payload["id"]),
            name=str(payload.get("name") or payload["id"]),
            description=str(payload.get("description") or ""),
            version=str(payload.get("version") or "1.0"),
            tags=[str(item) for item in payload.get("tags", [])],
            inputs=dict(payload.get("inputs") or {}),
            steps=[WorkflowStep.from_dict(item) for item in payload.get("steps", [])],
        )


@dataclass(frozen=True)
class WorkflowRunState:
    """Persisted workflow run state."""

    run_id: str
    workflow_id: str
    status: str
    current_step_index: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str | None = None
    completed_at: str | None = None
    error: str | None = None

    @staticmethod
    def create(workflow_id: str) -> "WorkflowRunState":
        return WorkflowRunState(
            run_id=uuid4().hex[:12],
            workflow_id=workflow_id,
            status=WORKFLOW_PENDING,
        )

    def update(self, **changes: Any) -> "WorkflowRunState":
        payload = self.to_dict()
        payload.update(changes)
        payload["updated_at"] = datetime.now(timezone.utc).isoformat()
        return WorkflowRunState.from_dict(payload)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "workflow_id": self.workflow_id,
            "status": self.status,
            "current_step_index": self.current_step_index,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "error": self.error,
        }

    @staticmethod
    def from_dict(payload: dict[str, Any]) -> "WorkflowRunState":
        return WorkflowRunState(
            run_id=str(payload["run_id"]),
            workflow_id=str(payload["workflow_id"]),
            status=str(payload.get("status") or WORKFLOW_PENDING),
            current_step_index=int(payload.get("current_step_index") or 0),
            created_at=str(payload.get("created_at") or datetime.now(timezone.utc).isoformat()),
            updated_at=payload.get("updated_at"),
            completed_at=payload.get("completed_at"),
            error=payload.get("error"),
        )


@dataclass(frozen=True)
class WorkflowHistoryEvent:
    """Workflow history event."""

    event_type: str
    message: str
    step_id: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "message": self.message,
            "step_id": self.step_id,
            "timestamp": self.timestamp,
            "data": self.data,
        }

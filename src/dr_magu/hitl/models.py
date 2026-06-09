from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


APPROVAL_PENDING = "pending"
APPROVAL_APPROVED = "approved"
APPROVAL_REJECTED = "rejected"
APPROVAL_MODIFIED = "modified"


@dataclass(frozen=True)
class ApprovalOption:
    """Selectable option presented to the user."""

    id: str
    title: str
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class ApprovalRequest:
    """Approval request persisted before executing sensitive actions."""

    id: str
    title: str
    description: str
    action: str
    risk_level: str = "medium"
    status: str = APPROVAL_PENDING
    options: list[ApprovalOption] = field(default_factory=list)
    selected_option_id: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    resolved_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def create(
        title: str,
        description: str,
        action: str,
        risk_level: str = "medium",
        options: list[ApprovalOption] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "ApprovalRequest":
        return ApprovalRequest(
            id=uuid4().hex[:12],
            title=title,
            description=description,
            action=action,
            risk_level=risk_level,
            options=options or [],
            metadata=metadata or {},
        )

    def approve(self, selected_option_id: str | None = None) -> "ApprovalRequest":
        return ApprovalRequest(
            id=self.id,
            title=self.title,
            description=self.description,
            action=self.action,
            risk_level=self.risk_level,
            status=APPROVAL_APPROVED,
            options=self.options,
            selected_option_id=selected_option_id,
            created_at=self.created_at,
            resolved_at=datetime.now(timezone.utc).isoformat(),
            metadata=self.metadata,
        )

    def reject(self) -> "ApprovalRequest":
        return ApprovalRequest(
            id=self.id,
            title=self.title,
            description=self.description,
            action=self.action,
            risk_level=self.risk_level,
            status=APPROVAL_REJECTED,
            options=self.options,
            selected_option_id=self.selected_option_id,
            created_at=self.created_at,
            resolved_at=datetime.now(timezone.utc).isoformat(),
            metadata=self.metadata,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "action": self.action,
            "risk_level": self.risk_level,
            "status": self.status,
            "options": [option.to_dict() for option in self.options],
            "selected_option_id": self.selected_option_id,
            "created_at": self.created_at,
            "resolved_at": self.resolved_at,
            "metadata": self.metadata,
        }

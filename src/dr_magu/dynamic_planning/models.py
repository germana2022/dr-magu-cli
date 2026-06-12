from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from pydantic import BaseModel, Field


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class PlannedStep(BaseModel):
    id: str
    name: str
    command: str
    capability: str
    description: str = ""
    requires_approval: bool = False
    status: Literal["pending", "approved", "running", "success", "failed", "cancelled", "skipped"] = "pending"
    result: dict[str, Any] | None = None
    errors: list[str] = Field(default_factory=list)


class DynamicPlan(BaseModel):
    id: str
    goal: str
    intent: str
    status: Literal["draft", "approved", "running", "success", "failed", "cancelled"] = "draft"
    confidence: float = 0.75
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)
    workspace_path: str
    selected_agents: list[str] = Field(default_factory=list)
    selected_team: str | None = None
    selected_skills: list[str] = Field(default_factory=list)
    selected_workflows: list[str] = Field(default_factory=list)
    selected_mcp_providers: list[str] = Field(default_factory=list)
    approval_required: bool = False
    explanation: str = ""
    steps: list[PlannedStep] = Field(default_factory=list)
    latest_run_id: str | None = None

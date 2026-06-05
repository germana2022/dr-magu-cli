from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PlanStep(BaseModel):
    """One safe execution step produced by the future Orchestrator Brain."""

    name: str
    args: dict[str, Any] = Field(default_factory=dict)
    reason: str = ""


class BrainPlan(BaseModel):
    """Structured plan contract used before any Brain-generated execution."""

    intent: str
    language: str = "unknown"
    confidence: float = 0.0
    steps: list[PlanStep] = Field(default_factory=list)
    explanation: str = ""
    requires_approval: bool = False


class PlanValidationIssue(BaseModel):
    """Validation issue emitted before executing a Brain plan."""

    step: str | None = None
    severity: str = "error"
    message: str


class PlanValidationResult(BaseModel):
    """Result produced by the plan validator."""

    valid: bool
    requires_approval: bool = False
    issues: list[PlanValidationIssue] = Field(default_factory=list)
    allowed_steps: list[str] = Field(default_factory=list)
    blocked_steps: list[str] = Field(default_factory=list)

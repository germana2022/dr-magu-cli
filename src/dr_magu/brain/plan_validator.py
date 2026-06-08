from __future__ import annotations

from dataclasses import dataclass, field

from .models import BrainPlan


ALLOWED_COMMANDS = {"repo.scan", "context.generate", "brain.context"}
ALLOWED_WORKFLOWS = {"repository.context"}
ALLOWED_AGENTS = {"repository-analyzer"}


@dataclass(frozen=True)
class PlanValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)


def validate_plan(plan: BrainPlan) -> PlanValidationResult:
    """Validate a BrainPlan before execution."""
    errors: list[str] = []
    if not plan.steps:
        errors.append("Plan has no executable steps.")

    for step in plan.steps:
        if step.type == "command" and step.name not in ALLOWED_COMMANDS:
            errors.append(f"Command is not allowed: {step.name}")
        elif step.type == "workflow" and step.name not in ALLOWED_WORKFLOWS:
            errors.append(f"Workflow is not allowed: {step.name}")
        elif step.type == "agent" and step.name not in ALLOWED_AGENTS:
            errors.append(f"Agent is not allowed: {step.name}")
        elif step.type not in {"command", "workflow", "agent"}:
            errors.append(f"Unsupported step type: {step.type}")

    return PlanValidationResult(valid=not errors, errors=errors)

from __future__ import annotations

from pathlib import Path
from typing import Any

from dr_magu.commands.context import CommandContext
from dr_magu.commands.processor import CommandProcessor
from dr_magu.commands.registry import registry
from dr_magu.config import load_config

from .models import BrainPlan
from .plan_validator import validate_plan


def execute_plan(plan: BrainPlan, workspace_path: str | None = None) -> dict[str, Any]:
    """Validate and execute a BrainPlan through existing runtime boundaries."""
    validation = validate_plan(plan)
    if not validation.valid:
        return {"success": False, "errors": validation.errors, "results": []}

    context = CommandContext(
        workspace_path=str(Path(workspace_path or ".").resolve()),
        output_format="human",
        config=load_config(),
    )
    processor = CommandProcessor(registry)
    results: list[dict[str, Any]] = []

    for step in plan.steps:
        if step.type == "command":
            command_line = step.name
            if step.name == "context.generate" and step.args.get("refresh"):
                command_line = "context.generate --refresh"
            result = processor.execute_line(command_line, context)
        elif step.type == "workflow":
            result = processor.execute_line(f"workflow.run {step.name}", context)
        elif step.type == "agent":
            result = processor.execute_line(f"agent.run {step.name}", context)
        else:
            continue

        results.append({
            "step": step.name,
            "success": result.success,
            "tool": result.tool,
            "errors": result.errors,
            "data": result.data,
        })

    return {
        "success": all(item["success"] for item in results),
        "errors": [error for item in results for error in item.get("errors", [])],
        "results": results,
    }

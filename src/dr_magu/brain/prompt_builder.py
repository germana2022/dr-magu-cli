from __future__ import annotations

from typing import Any


def build_planner_prompt(user_prompt: str, brain_context: dict[str, Any]) -> str:
    """Build the planner prompt for future LLM execution."""
    actions = ", ".join(brain_context.get("available_actions", []))
    return (
        "You are Dr Magu AI Orchestrator Brain. "
        "Generate a safe structured execution plan using only available actions.\n"
        f"Available actions: {actions}\n"
        f"User prompt: {user_prompt}"
    )

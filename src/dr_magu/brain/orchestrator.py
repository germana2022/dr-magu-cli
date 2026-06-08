from __future__ import annotations

from typing import Any

from .context_loader import load_brain_context
from .executor import execute_plan
from .planner import plan_prompt
from .prompt_builder import build_planner_prompt


def create_plan(user_prompt: str, workspace_path: str | None = None) -> dict[str, Any]:
    context = load_brain_context(workspace_path)
    response = plan_prompt(user_prompt)
    return {
        "prompt": user_prompt,
        "planner_prompt": build_planner_prompt(user_prompt, context),
        "context": context,
        "response": response.to_dict(),
    }


def execute_prompt(user_prompt: str, workspace_path: str | None = None) -> dict[str, Any]:
    response = plan_prompt(user_prompt)
    if response.plan is None:
        return response.to_dict()
    payload = response.to_dict()
    payload["execution"] = execute_plan(response.plan, workspace_path)
    return payload

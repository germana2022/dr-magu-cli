from __future__ import annotations

import json

from .context_loader import load_brain_context
from .orchestrator import create_plan, execute_prompt


def brain_context(workspace_path: str | None = None) -> dict:
    return load_brain_context(workspace_path)


def brain_plan(prompt: str, workspace_path: str | None = None) -> dict:
    return create_plan(prompt, workspace_path)


def brain_execute(prompt: str, workspace_path: str | None = None) -> dict:
    return execute_prompt(prompt, workspace_path)


def render_brain_result(payload: dict) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False)

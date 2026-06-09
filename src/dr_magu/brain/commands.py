from __future__ import annotations

import json
from .intent_router import classify_prompt

from .context_loader import load_brain_context
from .orchestrator import create_plan, execute_prompt
from .conversation import ask as conversational_ask


def brain_context(workspace_path: str | None = None) -> dict:
    return load_brain_context(workspace_path)


def brain_plan(prompt: str, workspace_path: str | None = None) -> dict:
    return create_plan(prompt, workspace_path)


def brain_execute(prompt: str, workspace_path: str | None = None) -> dict:
    return execute_prompt(prompt, workspace_path)


def render_brain_result(payload: dict) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False)



def brain_route(prompt: str) -> dict:
    """Classify a natural-language prompt using the Intent Router."""
    return classify_prompt(prompt).to_dict()



def brain_ask(prompt: str, workspace_path: str | None = None) -> dict:
    """Route a natural-language prompt through the Conversational Brain."""
    result = conversational_ask(prompt, workspace_path or ".")
    return {
        "success": result.success,
        "tool": result.tool,
        "data": result.data,
        "errors": result.errors,
    }


def brain_chat(prompt: str, workspace_path: str | None = None) -> dict:
    """Alias for Conversational Brain prompts."""
    return brain_ask(prompt, workspace_path)

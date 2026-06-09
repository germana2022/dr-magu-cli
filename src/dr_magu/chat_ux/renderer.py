from __future__ import annotations

from typing import Any

from dr_magu.result import ToolResult


def is_chat_result(result: ToolResult) -> bool:
    """Return whether a result should be rendered as clean chat text."""
    return result.tool in {"brain.ask", "brain.chat", "llm.chat"}


def extract_chat_text(result: ToolResult) -> str | None:
    """Extract the user-facing chat response from a ToolResult."""
    if not result.success:
        return None

    data = result.data or {}

    if result.tool in {"brain.ask", "brain.chat"}:
        response = data.get("response")
        if isinstance(response, str) and response.strip():
            return response.strip()

        route_result = data.get("route_result")
        if isinstance(route_result, dict):
            route_data = route_result.get("data")
            if isinstance(route_data, dict):
                # Keep command-routed results compact but still useful.
                if "summary" in route_data and isinstance(route_data["summary"], str):
                    return route_data["summary"].strip()
                if "output_path" in route_data:
                    return f"Done. Output saved to: {route_data['output_path']}"

    if result.tool == "llm.chat":
        response = data.get("response")
        if isinstance(response, dict):
            content = response.get("content")
            if isinstance(content, str) and content.strip():
                return content.strip()

    return None


def render_user_facing_result(result: ToolResult, debug: bool = False) -> Any:
    """Return clean chat content unless debug output was requested."""
    if debug:
        return result.data if result.success else result.errors

    chat_text = extract_chat_text(result)
    if chat_text:
        return chat_text

    return result.data if result.success else result.errors

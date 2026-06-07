"""Reusable TUI result rendering helpers.

This module is intentionally independent from Textual widget imports so it can be
unit-tested without requiring a terminal application.
"""

from __future__ import annotations

from typing import Any


def summarize_result_data(tool_name: str, data: dict[str, Any] | None) -> str:
    """Return a compact, human-readable summary for command result data."""
    if not data:
        return "No output."

    if tool_name == "files.list":
        count = data.get("count")
        workspace = data.get("workspace", "")
        return f"Files: {count} | Workspace: {workspace}"

    if tool_name == "git.status":
        branch = data.get("branch", "unknown")
        status = data.get("status", "unknown")
        return f"Branch: {branch} | Status: {status}"

    if tool_name == "workflow.run":
        run_id = data.get("run_id", "unknown")
        status = data.get("status", "unknown")
        return f"Workflow run: {run_id} | Status: {status}"

    if tool_name == "agent.run":
        run_id = data.get("run_id", "unknown")
        status = data.get("status", "unknown")
        return f"Agent run: {run_id} | Status: {status}"

    keys = ", ".join(sorted(str(key) for key in data.keys()))
    return f"Data keys: {keys}"

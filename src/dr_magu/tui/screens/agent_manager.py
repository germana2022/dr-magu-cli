"""Agent Manager screen metadata and formatting helpers."""

from __future__ import annotations


def format_agent_state(enabled: bool, deleted: bool = False) -> str:
    """Return a compact agent state label."""
    if deleted:
        return "deleted"
    return "enabled" if enabled else "disabled"

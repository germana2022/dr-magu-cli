"""Session Manager screen metadata and formatting helpers."""

from __future__ import annotations


def format_session_status(status: str, is_current: bool = False) -> str:
    """Return a compact status label for the session manager."""
    prefix = "current " if is_current else ""
    return f"{prefix}{status}".strip()

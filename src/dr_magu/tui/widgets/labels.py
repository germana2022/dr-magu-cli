"""Reusable label text helpers for Dr Magu TUI widgets."""

from __future__ import annotations


def command_hint() -> str:
    """Return the default command hint shown in the command input."""
    return "Type a command... Examples: /brain, /control, /agents, /workflow-last"

"""Control Center screen metadata.

The actual Textual screen remains wired through the current TUI application.
This module establishes the modular boundary used by future Control Center
extraction work.
"""

from __future__ import annotations


CONTROL_CENTER_SECTIONS = [
    "Plugins",
    "Agents",
    "Workflows",
    "Tools",
    "Permissions",
    "Brain",
    "Schedules",
]


def list_control_center_sections() -> list[str]:
    """Return the sections displayed by the Control Center."""
    return list(CONTROL_CENTER_SECTIONS)

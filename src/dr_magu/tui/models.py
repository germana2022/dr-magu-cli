"""Shared models for the Dr Magu Terminal UI."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TuiSettings:
    """Settings used to start the Dr Magu Terminal UI."""

    workspace_path: str
    version: str = "0.9.5"

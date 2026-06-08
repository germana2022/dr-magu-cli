from __future__ import annotations

from pathlib import Path

from .checker import run_health_checks
from .renderer import render_health_report


def health_check(workspace_path: str | None = None) -> dict:
    root = Path(workspace_path or ".").resolve()
    report = run_health_checks(root)
    return report.to_dict()


def health_check_text(workspace_path: str | None = None) -> str:
    root = Path(workspace_path or ".").resolve()
    report = run_health_checks(root)
    return render_health_report(report)

from __future__ import annotations

import json

from .models import StabilizationReport


def render_report_text(report: StabilizationReport) -> str:
    """Render a stabilization report as readable text."""
    lines = [
        f"Dr Magu Platform Stabilization Report v{report.version}",
        f"Status: {report.status}",
        "",
        "Checks:",
    ]
    for check in report.checks:
        lines.append(f"- [{check.status.upper()}] {check.name}: {check.message}")
        if check.details:
            lines.append(f"  details: {check.details}")
    return "\n".join(lines) + "\n"


def render_report_json(report: StabilizationReport) -> str:
    """Render a stabilization report as JSON."""
    return json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n"

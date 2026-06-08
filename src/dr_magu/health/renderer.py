from __future__ import annotations

from .models import HealthReport


def render_health_report(report: HealthReport) -> str:
    lines = [f"Dr Magu Health Report: {report.status.upper()}", ""]
    for check in report.checks:
        icon = "OK" if check.status == "pass" else "FAIL"
        lines.append(f"[{icon}] {check.name}: {check.message}")
        if check.details:
            lines.append(f"  details: {check.details}")
    return "\n".join(lines)

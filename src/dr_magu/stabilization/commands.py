from __future__ import annotations

from pathlib import Path

from dr_magu.result import ToolResult

from .checker import PlatformStabilizationChecker
from .renderer import render_report_json, render_report_text


def run_stabilization_checks(project_root: str | Path, output_format: str = "text") -> ToolResult:
    """Run v1.0.0 readiness checks."""
    report = PlatformStabilizationChecker(project_root).run()
    rendered = render_report_json(report) if output_format == "json" else render_report_text(report)

    output_dir = Path(project_root).resolve() / ".dr-magu" / "stabilization"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / ("stabilization-report.json" if output_format == "json" else "stabilization-report.txt")
    output_path.write_text(rendered, encoding="utf-8")

    return ToolResult(
        success=report.status != "fail",
        tool="platform.stabilize",
        data={
            "status": report.status,
            "report": report.to_dict(),
            "output_path": str(output_path),
        },
        errors=[] if report.status != "fail" else ["Platform stabilization checks failed."],
    )

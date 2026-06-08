from pathlib import Path

from dr_magu.health.checker import run_health_checks
from dr_magu.health.renderer import render_health_report


def test_health_checks_return_report_for_project_root():
    root = Path(__file__).resolve().parents[1]
    report = run_health_checks(root)
    assert report.status in {"healthy", "unhealthy"}
    assert report.checks


def test_health_report_renderer_outputs_status():
    root = Path(__file__).resolve().parents[1]
    report = run_health_checks(root)
    text = render_health_report(report)
    assert "Dr Magu Health Report" in text

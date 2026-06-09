from pathlib import Path

from dr_magu.commands.context import CommandContext
from dr_magu.commands.processor import CommandProcessor
from dr_magu.commands.registry import registry
from dr_magu.plugins.registry import PluginRegistry
from dr_magu.stabilization.checker import PlatformStabilizationChecker
from dr_magu.stabilization.commands import run_stabilization_checks
from dr_magu.stabilization.renderer import render_report_json, render_report_text


def test_platform_stabilization_checker_runs_for_project_root():
    root = Path(__file__).resolve().parents[1]

    report = PlatformStabilizationChecker(root).run()

    assert report.version == "0.22.0"
    assert report.status in {"pass", "warn", "fail"}
    assert report.checks


def test_platform_stabilization_renderers_output_content():
    root = Path(__file__).resolve().parents[1]
    report = PlatformStabilizationChecker(root).run()

    text = render_report_text(report)
    json_output = render_report_json(report)

    assert "Platform Stabilization Report" in text
    assert '"version": "0.22.0"' in json_output


def test_platform_stabilization_command_persists_report(tmp_path: Path):
    # Copy-free check against real project root for package/plugin validation.
    root = Path(__file__).resolve().parents[1]
    result = run_stabilization_checks(root)

    assert result.tool == "platform.stabilize"
    assert "output_path" in result.data
    assert Path(result.data["output_path"]).exists()


def test_command_processor_routes_platform_stabilize(tmp_path: Path):
    root = Path(__file__).resolve().parents[1]
    context = CommandContext(workspace_path=str(root), output_format="human", config={})

    result = CommandProcessor(registry).execute_line("platform.stabilize", context)

    assert result.tool == "platform.stabilize"
    assert "report" in result.data


def test_platform_stabilization_plugin_is_discovered():
    plugins = PluginRegistry(".").list()
    assert any(plugin.id == "platform-stabilization" for plugin in plugins)

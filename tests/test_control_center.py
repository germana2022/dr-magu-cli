from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from dr_magu.cli import app
from dr_magu.control_center.service import ControlCenterService
from dr_magu.commands.context import CommandContext
from dr_magu.commands.processor import CommandProcessor
from dr_magu.commands.registry import registry


def test_control_center_dashboard_contains_core_areas(tmp_path: Path) -> None:
    result = ControlCenterService(tmp_path).dashboard_result()

    assert result.success is True
    assert result.tool == "control.center"
    section_names = {section["name"] for section in result.data["sections"]}
    assert {"Plugins", "Agents", "Workflows", "Tools", "Permissions", "Schedules", "Brain"}.issubset(section_names)
    assert result.data["schedules"]["status"] == "reserved"


def test_control_center_exposes_plugin_impact(tmp_path: Path) -> None:
    result = ControlCenterService(tmp_path).plugin_impact_result("software-dev")

    assert result.success is True
    assert result.tool == "control.plugin"
    assert result.data["plugin_id"] == "software-dev"
    assert "repository-analyzer" in result.data["agents"]
    assert "repository.context" in result.data["workflows"]


def test_control_center_unknown_plugin_returns_error(tmp_path: Path) -> None:
    result = ControlCenterService(tmp_path).plugin_impact_result("missing-plugin")

    assert result.success is False
    assert result.tool == "control.plugin"
    assert result.errors


def test_control_center_command_processor_routes_dashboard(tmp_path: Path) -> None:
    context = CommandContext(workspace_path=str(tmp_path), output_format="human", config={})
    result = CommandProcessor(registry).execute_line("control.center", context)

    assert result.success is True
    assert result.tool == "control.center"


def test_control_center_cli_command(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["control", "center", "--workspace", str(tmp_path)])

    assert result.exit_code == 0
    assert "Dr Magu Control Center" in result.output

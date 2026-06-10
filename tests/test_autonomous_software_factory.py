from typer.testing import CliRunner

from dr_magu.cli import app
from dr_magu.commands.context import CommandContext
from dr_magu.commands.processor import CommandProcessor
from dr_magu.commands.registry import registry
from dr_magu.plugins.registry import PluginRegistry
from dr_magu.software_factory.planner import SoftwareFactoryPlanner
from dr_magu.software_factory.runtime import SoftwareFactoryRuntime


def test_factory_planner_creates_end_to_end_pipeline():
    plan = SoftwareFactoryPlanner().create_plan("Build a CRM")

    assert plan.name == "software.factory"
    assert plan.idea == "Build a CRM"
    assert [stage.id for stage in plan.stages] == [
        "idea-intake",
        "research",
        "architecture",
        "tickets",
        "code-plan",
        "tests",
        "documentation",
        "release-notes",
    ]


def test_factory_plan_command_creates_artifact(tmp_path):
    context = CommandContext(workspace_path=str(tmp_path), output_format="human", config={})

    result = CommandProcessor(registry).execute_line("factory.plan Build a CRM", context)

    assert result.success is True
    assert result.tool == "factory.plan"
    assert result.data["plan"]["idea"] == "Build a CRM"
    assert result.data["artifact"]["filename"] == "factory-plan.json"


def test_factory_run_executes_pipeline(tmp_path):
    result = SoftwareFactoryRuntime(tmp_path).run("Build a CRM")

    assert result.success is True
    assert result.tool == "factory.run"
    assert "idea-intake" in result.data["summary"]["completed"]
    assert "release-notes" in result.data["summary"]["completed"]
    assert (tmp_path / ".dr-magu" / "factory" / "factory-run-summary.json").exists()


def test_factory_run_command(tmp_path):
    context = CommandContext(workspace_path=str(tmp_path), output_format="human", config={})

    result = CommandProcessor(registry).execute_line("factory.run Build a CRM", context)

    assert result.success is True
    assert result.data["summary"]["failed"] == []


def test_factory_stage_command(tmp_path):
    context = CommandContext(workspace_path=str(tmp_path), output_format="human", config={})

    result = CommandProcessor(registry).execute_line('factory.stage "Build a CRM" --stage code-plan', context)

    assert result.success is True
    assert result.data["stage"] == "code-plan"


def test_cli_exposes_factory_commands():
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "factory-plan" in result.output
    assert "factory-run" in result.output


def test_cli_factory_plan_command():
    result = CliRunner().invoke(app, ["factory-plan", "Build a CRM"])

    assert result.exit_code == 0
    assert "factory-plan.json" in result.output


def test_autonomous_software_factory_plugin_is_discovered():
    plugins = PluginRegistry(".").list()

    assert any(plugin.id == "autonomous-software-factory" for plugin in plugins)

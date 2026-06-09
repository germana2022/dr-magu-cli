from typer.testing import CliRunner

from dr_magu.cli import app
from dr_magu.commands.context import CommandContext
from dr_magu.commands.processor import CommandProcessor
from dr_magu.commands.registry import registry
from dr_magu.multi_agent.planner import MultiAgentPlanner
from dr_magu.multi_agent.runtime import MultiAgentOrchestrator
from dr_magu.plugins.registry import PluginRegistry


def test_multi_agent_planner_creates_sdlc_pipeline():
    plan = MultiAgentPlanner().create_plan("sdlc.pipeline")

    assert plan.name == "sdlc.pipeline"
    assert plan.mode == "sequential"
    assert len(plan.tasks) >= 5
    assert plan.tasks[0].agent_id == "repository-analyzer"


def test_multi_agent_plan_command(tmp_path):
    context = CommandContext(workspace_path=str(tmp_path), output_format="human", config={})

    result = CommandProcessor(registry).execute_line("multiagent.plan sdlc.pipeline", context)

    assert result.success is True
    assert result.tool == "multiagent.plan"
    assert result.data["plan"]["tasks"][0]["agent_id"] == "repository-analyzer"


def test_multi_agent_run_executes_sdlc_pipeline(tmp_path):
    result = MultiAgentOrchestrator(tmp_path).run("sdlc.pipeline")

    assert result.success is True
    assert result.tool == "multiagent.run"
    assert "repository-analyzer" in result.data["completed"]
    assert "release-notes-generator" in result.data["completed"]


def test_multi_agent_run_command(tmp_path):
    context = CommandContext(workspace_path=str(tmp_path), output_format="human", config={})

    result = CommandProcessor(registry).execute_line("multiagent.run sdlc.pipeline", context)

    assert result.success is True
    assert result.data["summary"].endswith("0 failed")


def test_cli_exposes_multiagent_commands():
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "multiagent-plan" in result.output
    assert "multiagent-run" in result.output


def test_cli_multiagent_plan_command():
    result = CliRunner().invoke(app, ["multiagent-plan", "sdlc.pipeline"])

    assert result.exit_code == 0
    assert "repository-analyzer" in result.output


def test_multi_agent_orchestrator_plugin_is_discovered():
    plugins = PluginRegistry(".").list()

    assert any(plugin.id == "multi-agent-orchestrator" for plugin in plugins)

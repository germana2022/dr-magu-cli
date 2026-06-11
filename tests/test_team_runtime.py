from typer.testing import CliRunner

from dr_magu.cli import app
from dr_magu.commands.context import CommandContext
from dr_magu.commands.processor import CommandProcessor
from dr_magu.commands.registry import registry
from dr_magu.config import load_config
from dr_magu.multi_agent.team import TeamRuntime


def _ctx(tmp_path):
    return CommandContext(workspace_path=str(tmp_path), output_format="human", config=load_config())


def test_team_runtime_create_add_list_show_run(tmp_path):
    runtime = TeamRuntime(tmp_path)
    assert runtime.create("repo-analysis").success
    assert runtime.agent_runner.create_agent("researcher", workflow="research-brief").success
    assert runtime.agent_runner.create_agent("architect", workflow="research-brief").success
    assert runtime.add("repo-analysis", "researcher").success
    assert runtime.add("repo-analysis", "architect").success

    listed = runtime.list()
    assert listed.success
    assert listed.data["count"] == 1
    assert listed.data["teams"][0]["agents"] == ["researcher", "architect"]

    shown = runtime.show("repo-analysis")
    assert shown.success
    assert len(shown.data["agents"]) == 2

    result = runtime.run("repo-analysis", "Analyze repository", dry_run=True)
    assert result.success
    assert result.data["team_run"]["completed"] == ["researcher", "architect"]
    assert result.data["team_run"]["failed"] == []


def test_team_commands_are_registered_and_normalized(tmp_path):
    processor = CommandProcessor(registry)
    ctx = _ctx(tmp_path)
    assert CommandProcessor.parse_line("team create repo-analysis")["command_name"] == "team.create"
    assert CommandProcessor.parse_line("team add repo-analysis researcher")["args"] == {"team_id": "repo-analysis", "agent_id": "researcher"}

    assert processor.execute_line("agent.create researcher", ctx).success
    assert processor.execute_line("team.create repo-analysis", ctx).success
    assert processor.execute_line("team.add repo-analysis researcher", ctx).success
    run = processor.execute_line("team.run repo-analysis Analyze repo --dry-run", ctx)
    assert run.success
    assert run.tool == "team.run"


def test_cli_exposes_team_commands(tmp_path):
    runner = CliRunner()
    result = runner.invoke(app, ["team", "create", "repo-analysis", "--workspace", str(tmp_path), "--json"])
    assert result.exit_code == 0
    assert "repo-analysis" in result.output

    result = runner.invoke(app, ["team", "list", "--workspace", str(tmp_path)])
    assert result.exit_code == 0
    assert "repo-analysis" in result.output

from typer.testing import CliRunner

from dr_magu.cli import app
from dr_magu.commands.context import CommandContext
from dr_magu.commands.processor import CommandProcessor
from dr_magu.commands.registry import registry
from dr_magu.plugins.registry import PluginRegistry
from dr_magu.self_healing.policies import default_policy_for
from dr_magu.self_healing.runtime import SelfHealingRuntime


def test_default_policy_for_repository_read_has_repo_scan_fallback():
    policy = default_policy_for("repository.read owner/repo")

    assert policy.max_retries == 1
    assert policy.fallback_command == "repo.scan"
    assert policy.escalate_on_failure is True


def test_healing_plan_command(tmp_path):
    context = CommandContext(workspace_path=str(tmp_path), output_format="human", config={})

    result = CommandProcessor(registry).execute_line("healing.plan unknown.command", context)

    assert result.success is True
    assert result.tool == "healing.plan"
    assert result.data["policy"]["max_retries"] == 1


def test_healing_run_success_without_fallback(tmp_path):
    result = SelfHealingRuntime(tmp_path).run("files.list")

    assert result.success is True
    assert result.data["report"]["status"] == "completed"
    assert result.data["report"]["fallback_used"] is False
    assert (tmp_path / ".dr-magu" / "healing" / "latest-healing-report.json").exists()


def test_healing_run_recovers_with_fallback(tmp_path):
    result = SelfHealingRuntime(tmp_path).run(
        "unknown.command",
        fallback_command="files.list",
        max_retries=0,
    )

    assert result.success is True
    assert result.data["report"]["status"] == "recovered"
    assert result.data["report"]["fallback_used"] is True
    assert len(result.data["report"]["attempts"]) == 2


def test_healing_run_escalates_after_failure(tmp_path):
    result = SelfHealingRuntime(tmp_path).run(
        "unknown.command",
        fallback_command=None,
        max_retries=0,
        escalate_on_failure=True,
    )

    assert result.success is False
    assert result.data["report"]["status"] == "escalated"
    assert result.data["report"]["escalated"] is True
    assert "Escalated for human review." in result.errors


def test_healing_run_command_with_fallback(tmp_path):
    context = CommandContext(workspace_path=str(tmp_path), output_format="human", config={})

    result = CommandProcessor(registry).execute_line('healing.run "unknown.command" --fallback-command files.list --max-retries 0', context)

    assert result.success is True
    assert result.data["report"]["status"] == "recovered"


def test_cli_exposes_healing_commands():
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "healing-plan" in result.output
    assert "healing-run" in result.output


def test_self_healing_plugin_is_discovered():
    plugins = PluginRegistry(".").list()

    assert any(plugin.id == "self-healing-workflows" for plugin in plugins)

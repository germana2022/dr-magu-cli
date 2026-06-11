from __future__ import annotations

from pathlib import Path

from dr_magu.agents.registry import AgentRegistry
from dr_magu.agents.runner import AgentRunner
from dr_magu.commands.context import CommandContext
from dr_magu.commands.processor import CommandProcessor
from dr_magu.commands.registry import registry


def test_agent_runtime_create_status_context_and_stop(tmp_path: Path):
    runner = AgentRunner(tmp_path)

    created = runner.create_agent("researcher", role="researcher", workflow="research-brief")
    assert created.success is True
    assert AgentRegistry(tmp_path).get("researcher").workflow == "research-brief"
    assert (tmp_path / ".dr-magu" / "agent-runtime" / "state.json").exists()

    status = runner.status_agent("researcher")
    assert status.success is True
    assert status.data["runtime_state"]["status"] == "idle"
    assert status.data["mcp_access"]["enabled"] is True

    context = runner.context("researcher")
    assert context.success is True
    assert context.data["workflow_access"]["bound_workflow"] == "research-brief"

    stopped = runner.stop_agent("researcher", reason="test stop")
    assert stopped.success is True
    assert stopped.data["runtime_state"]["status"] == "stopped"


def test_agent_runtime_run_persists_history_with_workflow_engine_dry_run(tmp_path: Path):
    runner = AgentRunner(tmp_path)
    assert runner.create_agent("researcher", role="researcher", workflow="research-brief").success

    result = runner.run_agent("researcher", prompt="AI news", dry_run=True)

    assert result.success is True
    assert result.data["agent_run"]["agent_id"] == "researcher"
    assert result.data["agent_run"]["status"] == "completed"
    assert result.data["agent_run"]["dry_run"] is True
    assert Path(result.data["run_path"]).exists()

    history = runner.history("researcher")
    assert history.success is True
    assert history.data["count"] == 1
    assert history.data["runs"][0]["prompt"] == "AI news"


def test_command_processor_supports_agent_runtime_commands(tmp_path: Path):
    context = CommandContext(workspace_path=str(tmp_path), output_format="human", config={})
    processor = CommandProcessor(registry)

    assert processor.execute_line("agent create researcher --role researcher --workflow research-brief", context).success
    assert processor.execute_line("agent status researcher", context).success
    assert processor.execute_line("agent context researcher", context).success
    assert processor.execute_line('agent run researcher "AI news" --dry-run', context).success
    assert processor.execute_line("agent history researcher", context).success
    assert processor.execute_line("agent stop researcher", context).success

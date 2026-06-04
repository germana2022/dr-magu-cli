from __future__ import annotations

import json
from pathlib import Path

from dr_magu.commands.context import CommandContext
from dr_magu.commands.processor import CommandProcessor
from dr_magu.commands.registry import registry
from dr_magu.workflows.registry import workflow_registry
from dr_magu.workflows.runner import WorkflowRunner


def test_workflow_registry_lists_repository_context() -> None:
    workflows = workflow_registry.list()

    assert any(workflow.name == "repository.context" for workflow in workflows)
    workflow = workflow_registry.get("rc")
    assert workflow.name == "repository.context"
    assert workflow.requires_llm is False


def test_workflow_runner_runs_repository_context(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='sample'\n", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "sample.py").write_text("print('hello')\n", encoding="utf-8")

    result = WorkflowRunner(str(tmp_path)).run("repository.context")

    assert result.success is True
    assert result.data is not None
    run_id = result.data["run_id"]
    run_dir = tmp_path / ".dr-magu" / "workflows" / "runs" / run_id
    assert (run_dir / "run.json").exists()
    assert (run_dir / "state.json").exists()
    assert (run_dir / "events.jsonl").exists()
    assert (tmp_path / ".dr-magu" / "scans" / "latest-scan.json").exists()
    assert (tmp_path / ".dr-magu" / "context" / "PROJECT_CONTEXT.md").exists()

    state = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
    assert state["workflow"] == "repository.context"
    assert state["context_path"]
    assert state["generated_files"]


def test_workflow_runner_lists_and_shows_runs(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Sample\n", encoding="utf-8")
    runner = WorkflowRunner(str(tmp_path))
    run_result = runner.run("repository.context")
    assert run_result.success is True
    assert run_result.data is not None

    runs_result = runner.list_runs()
    assert runs_result.success is True
    assert runs_result.data is not None
    assert len(runs_result.data["runs"]) == 1

    show_result = runner.show_run(run_result.data["run_id"])
    assert show_result.success is True
    assert show_result.data is not None
    assert show_result.data["run"]["workflow"] == "repository.context"


def test_command_processor_executes_workflow_alias(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Sample\n", encoding="utf-8")
    context = CommandContext(workspace_path=str(tmp_path), output_format="human", config={})

    result = CommandProcessor(registry).execute_line("wf repository.context", context)

    assert result.success is True
    assert result.tool == "workflow.run"
    assert result.data is not None
    assert result.data["workflow"] == "repository.context"


def test_workflow_run_metadata_includes_duration_and_events(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Sample\n", encoding="utf-8")
    runner = WorkflowRunner(str(tmp_path))

    result = runner.run("repository.context")

    assert result.success is True
    assert result.data is not None
    assert isinstance(result.data["duration_ms"], int)
    run_id = result.data["run_id"]
    run_dir = tmp_path / ".dr-magu" / "workflows" / "runs" / run_id
    run_data = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    assert isinstance(run_data["duration_ms"], int)
    events = [json.loads(line) for line in (run_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    assert any(event["type"] == "node.started" for event in events)
    assert any(event["type"] == "node.completed" for event in events)
    assert all(event.get("run_id") == run_id for event in events if event.get("run_id"))


def test_workflow_runner_shows_last_run(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Sample\n", encoding="utf-8")
    runner = WorkflowRunner(str(tmp_path))
    run_result = runner.run("repository.context")

    last_result = runner.show_last_run()

    assert last_result.success is True
    assert last_result.tool == "workflow.last"
    assert last_result.data is not None
    assert last_result.data["run"]["id"] == run_result.data["run_id"]
    assert "events" in last_result.data


def test_workflow_runner_validates_workspace(tmp_path: Path) -> None:
    empty_workspace = tmp_path / "empty"
    empty_workspace.mkdir()

    result = WorkflowRunner(str(empty_workspace)).run("repository.context")

    assert result.success is False
    assert "no scannable files" in result.errors[0]


def test_command_processor_executes_workflow_last_alias(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Sample\n", encoding="utf-8")
    runner = WorkflowRunner(str(tmp_path))
    runner.run("repository.context")
    context = CommandContext(workspace_path=str(tmp_path), output_format="human", config={})

    result = CommandProcessor(registry).execute_line("wlast", context)

    assert result.success is True
    assert result.tool == "workflow.last"

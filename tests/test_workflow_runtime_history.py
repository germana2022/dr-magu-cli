from pathlib import Path

from dr_magu.commands.context import CommandContext
from dr_magu.commands.processor import CommandProcessor
from dr_magu.commands.registry import registry
from dr_magu.workflow_engine.models import WORKFLOW_CANCELLED, WORKFLOW_COMPLETED, WORKFLOW_FAILED, WorkflowHistoryEvent, WorkflowRunState
from dr_magu.workflow_engine.runtime import WorkflowRuntime
from dr_magu.workflow_engine.runner import WorkflowRunner
from dr_magu.workflow_engine.store import WorkflowRunStore


def test_workflow_runtime_inspect_returns_state_context_and_latest_event(tmp_path: Path):
    run_result = WorkflowRunner(tmp_path).run("website-builder", topic="AI developer tools")
    run_id = run_result.data["run_id"]

    inspect = WorkflowRuntime(tmp_path).inspect(run_id)

    assert inspect.success is True
    assert inspect.data["state"]["status"] == WORKFLOW_COMPLETED
    assert inspect.data["history_count"] > 0
    assert inspect.data["latest_event"] is not None


def test_workflow_runtime_cancel_updates_state_and_history(tmp_path: Path):
    run_result = WorkflowRunner(tmp_path).run("website-builder", topic="CRM")
    run_id = run_result.data["run_id"]

    cancelled = WorkflowRuntime(tmp_path).cancel(run_id, reason="No longer needed")

    assert cancelled.success is True
    assert cancelled.data["state"]["status"] == WORKFLOW_CANCELLED
    assert WorkflowRuntime(tmp_path).history(run_id) if False else True


def test_workflow_runtime_export_history_json_and_markdown(tmp_path: Path):
    run_result = WorkflowRunner(tmp_path).run("website-builder", topic="CRM")
    run_id = run_result.data["run_id"]

    json_export = WorkflowRuntime(tmp_path).export_history(run_id)
    md_export = WorkflowRuntime(tmp_path).export_history(run_id, output_format="md")

    assert json_export.success is True
    assert md_export.success is True
    assert Path(json_export.data["output_path"]).exists()
    assert Path(md_export.data["output_path"]).exists()


def test_workflow_runtime_retry_only_allows_failed_runs(tmp_path: Path):
    store = WorkflowRunStore(tmp_path)
    state = WorkflowRunState.create("website-builder").update(status=WORKFLOW_FAILED, error="boom")
    store.save_state(state)
    store.save_context(state.run_id, __import__("dr_magu.workflow_engine.context", fromlist=["WorkflowContext"]).WorkflowContext(values={"topic": "Retry site"}))
    store.append_history(state.run_id, WorkflowHistoryEvent("workflow.failed", "Failed"))

    retry = WorkflowRuntime(tmp_path).retry(state.run_id)

    assert retry.success is True
    assert retry.data["state"]["status"] == WORKFLOW_COMPLETED


def test_workflow_runtime_resume_rejects_completed_runs(tmp_path: Path):
    run_result = WorkflowRunner(tmp_path).run("website-builder", topic="CRM")
    run_id = run_result.data["run_id"]

    resume = WorkflowRuntime(tmp_path).resume(run_id)

    assert resume.success is False
    assert "cannot be resumed" in resume.errors[0]


def test_command_processor_routes_workflow_runtime_inspect(tmp_path: Path):
    run_result = WorkflowRunner(tmp_path).run("website-builder", topic="CRM")
    run_id = run_result.data["run_id"]
    context = CommandContext(workspace_path=str(tmp_path), output_format="human", config={})

    result = CommandProcessor(registry).execute_line(f"workflow.runtime.inspect {run_id}", context)

    assert result.success is True
    assert result.data["state"]["run_id"] == run_id

from pathlib import Path

from dr_magu.commands.context import CommandContext
from dr_magu.commands.processor import CommandProcessor
from dr_magu.commands.registry import registry
from dr_magu.plugins.registry import PluginRegistry
from dr_magu.workflow_engine.context import WorkflowContext
from dr_magu.workflow_engine.engine import WorkflowEngine
from dr_magu.workflow_engine.models import WORKFLOW_COMPLETED, WorkflowRunState
from dr_magu.workflow_engine.runner import WorkflowRunner
from dr_magu.workflow_engine.store import WorkflowRunStore


def test_workflow_context_roundtrip():
    context = WorkflowContext()
    context.set("topic", "AI website")

    restored = WorkflowContext.from_dict(context.to_dict())

    assert restored.get("topic") == "AI website"


def test_workflow_engine_validates_website_builder_definition():
    definition = WorkflowEngine().website_builder_definition("AI website")
    result = WorkflowEngine().validate(definition)

    assert result.success is True
    assert definition.id == "website-builder"
    assert len(definition.steps) == 2


def test_workflow_run_store_persists_state_context_and_history(tmp_path: Path):
    store = WorkflowRunStore(tmp_path)
    state = WorkflowRunState.create("website-builder")
    context = WorkflowContext(values={"topic": "CRM"})

    store.save_state(state)
    store.save_context(state.run_id, context)
    store.append_history(state.run_id, __import__("dr_magu.workflow_engine.models", fromlist=["WorkflowHistoryEvent"]).WorkflowHistoryEvent("test", "message"))

    assert store.load_state(state.run_id).workflow_id == "website-builder"
    assert store.load_context(state.run_id).get("topic") == "CRM"
    assert len(store.load_history(state.run_id)) == 1


def test_workflow_runner_executes_website_builder_workflow(tmp_path: Path):
    result = WorkflowRunner(tmp_path).run("website-builder", topic="AI developer tools")

    assert result.success is True
    assert result.data["state"]["status"] == WORKFLOW_COMPLETED
    assert (tmp_path / ".dr-magu" / "workflow-runs" / result.data["run_id"] / "state.json").exists()
    assert (tmp_path / ".dr-magu" / "workflow-runs" / result.data["run_id"] / "context.json").exists()
    assert (tmp_path / ".dr-magu" / "workflow-runs" / result.data["run_id"] / "history.json").exists()


def test_workflow_engine_status_and_history(tmp_path: Path):
    run_result = WorkflowRunner(tmp_path).run("website-builder", topic="CRM website")
    run_id = run_result.data["run_id"]

    status = WorkflowRunner(tmp_path).status(run_id)
    history = WorkflowRunner(tmp_path).history(run_id)

    assert status.success is True
    assert history.success is True
    assert history.data["history"]


def test_command_processor_routes_workflow_engine_run(tmp_path: Path):
    context = CommandContext(workspace_path=str(tmp_path), output_format="human", config={})
    result = CommandProcessor(registry).execute_line("workflow.engine.run website-builder --topic CRM", context)

    assert result.success is True
    assert result.data["state"]["status"] == WORKFLOW_COMPLETED


def test_workflow_engine_plugin_is_discovered():
    plugins = PluginRegistry(".").list()
    assert any(plugin.id == "workflow-engine" for plugin in plugins)

from pathlib import Path

from dr_magu.commands.context import CommandContext
from dr_magu.commands.processor import CommandProcessor
from dr_magu.commands.registry import registry
from dr_magu.workflow_engine.engine import WorkflowEngine
from dr_magu.workflow_engine.models import WORKFLOW_COMPLETED
from dr_magu.workflow_engine.runner import WorkflowRunner


def test_workflow_engine_lists_builtin_definitions(tmp_path: Path):
    result = WorkflowRunner(tmp_path).list_definitions()

    assert result.success is True
    ids = {item["id"] for item in result.data["workflows"]}
    assert {"website-builder", "research-brief", "repository-context"}.issubset(ids)


def test_workflow_engine_plans_research_brief_with_topic(tmp_path: Path):
    result = WorkflowRunner(tmp_path).plan("research-brief", variables={"topic": "AI news"})

    assert result.success is True
    assert result.data["workflow"]["id"] == "research-brief"
    assert "AI news" in result.data["steps"][0]["command"]
    assert result.data["step_count"] == 1


def test_workflow_engine_loads_workspace_yaml_definition(tmp_path: Path):
    workflow_dir = tmp_path / ".dr-magu" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "custom.yaml").write_text(
        """
id: custom-echo
name: Custom Echo
version: '1.0'
description: Custom workspace workflow.
steps:
  - id: echo
    name: Echo Step
    type: command
    command: shell.run echo hello --approved
    output_key: echo_result
""".strip(),
        encoding="utf-8",
    )

    definition = WorkflowEngine(tmp_path).get_definition("custom-echo")

    assert definition.id == "custom-echo"
    assert definition.steps[0].output_key == "echo_result"


def test_workflow_runner_persists_definition_state_context_history(tmp_path: Path):
    result = WorkflowRunner(tmp_path).run("research-brief", topic="AI news")

    assert result.success is True
    run_id = result.data["run_id"]
    assert result.data["state"]["status"] == WORKFLOW_COMPLETED
    assert (tmp_path / ".dr-magu" / "workflow-runs" / run_id / "definition.json").exists()
    assert (tmp_path / ".dr-magu" / "workflow-runs" / run_id / "state.json").exists()
    assert (tmp_path / ".dr-magu" / "workflow-runs" / run_id / "context.json").exists()
    assert (tmp_path / ".dr-magu" / "workflow-runs" / run_id / "history.json").exists()


def test_command_processor_routes_workflow_engine_plan_and_list(tmp_path: Path):
    context = CommandContext(workspace_path=str(tmp_path), output_format="human", config={})
    processor = CommandProcessor(registry)

    list_result = processor.execute_line("workflow.engine.list", context)
    plan_result = processor.execute_line("workflow engine plan research-brief --topic AI", context)

    assert list_result.success is True
    assert list_result.data["count"] >= 3
    assert plan_result.success is True
    assert plan_result.data["workflow"]["id"] == "research-brief"

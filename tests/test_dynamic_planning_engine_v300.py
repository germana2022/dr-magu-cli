from __future__ import annotations

from dr_magu.commands.context import CommandContext
from dr_magu.commands.processor import CommandProcessor
from dr_magu.commands.registry import registry
from dr_magu.dynamic_planning.runtime import DynamicPlanningEngine
from dr_magu.config import load_config


def test_dynamic_plan_create_persists_repository_plan(tmp_path):
    result = DynamicPlanningEngine(str(tmp_path)).create("Analyze this repository")
    assert result.success
    plan = result.data["plan"]
    assert plan["intent"] == "repository_analysis"
    assert plan["selected_team"] == "repo-analysis"
    assert "researcher" in plan["selected_agents"]
    assert any(step["command"].startswith("team.run repo-analysis") for step in plan["steps"])


def test_dynamic_plan_list_show_status_and_approve(tmp_path):
    engine = DynamicPlanningEngine(str(tmp_path))
    created = engine.create("Research AI trends")
    plan_id = created.data["plan"]["id"]
    assert engine.list().data["count"] == 1
    assert engine.show(plan_id).data["plan"]["goal"] == "Research AI trends"
    assert engine.status(plan_id).data["status"] == "draft"
    approved = engine.approve(plan_id)
    assert approved.success
    assert approved.data["plan"]["status"] == "approved"


def test_command_processor_supports_plan_space_syntax(tmp_path):
    context = CommandContext(workspace_path=str(tmp_path), output_format="human", config=load_config())
    result = CommandProcessor(registry).execute_line('plan create "Analyze this repository"', context)
    assert result.success
    assert result.tool == "plan.create"
    assert result.data["plan"]["intent"] == "repository_analysis"


def test_dynamic_plan_cancel(tmp_path):
    engine = DynamicPlanningEngine(str(tmp_path))
    created = engine.create("General objective")
    plan_id = created.data["plan"]["id"]
    cancelled = engine.cancel(plan_id, reason="test")
    assert cancelled.success
    assert cancelled.data["plan"]["status"] == "cancelled"

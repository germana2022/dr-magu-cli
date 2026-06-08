from dr_magu.brain.context_loader import load_brain_context
from dr_magu.brain.orchestrator import create_plan
from dr_magu.brain.planner import plan_prompt
from dr_magu.brain.plan_validator import validate_plan


def test_brain_context_loader_returns_workspace_and_actions():
    context = load_brain_context(".")
    assert "workspace" in context
    assert "available_actions" in context
    assert "repo.scan" in context["available_actions"]


def test_spanish_repository_context_prompt_creates_plan():
    response = plan_prompt("analiza este repositorio y genera contexto tecnico")
    assert response.mode == "workspace_action"
    assert response.plan is not None
    assert response.plan.intent == "generate_repository_context"
    assert [step.name for step in response.plan.steps] == ["repo.scan", "context.generate"]


def test_general_prompt_does_not_create_execution_plan():
    response = plan_prompt("quien fue Albert Einstein")
    assert response.mode == "general_chat"
    assert response.plan is None


def test_brain_plan_validator_accepts_known_plan():
    response = plan_prompt("analyze this repository and generate context")
    assert response.plan is not None
    validation = validate_plan(response.plan)
    assert validation.valid is True


def test_create_plan_payload_contains_planner_prompt():
    payload = create_plan("analyze this repository and generate context", ".")
    assert "planner_prompt" in payload
    assert payload["response"]["plan"] is not None

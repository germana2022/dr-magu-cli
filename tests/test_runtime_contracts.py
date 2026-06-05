from dr_magu.contracts.models import PermissionMode, RiskLevel
from dr_magu.plans.models import BrainPlan, PlanStep
from dr_magu.plans.validator import PlanValidator
from dr_magu.tools.registry import ToolRegistry


def test_tool_registry_exposes_formal_contracts():
    tools = ToolRegistry().list_tools()
    shell = next(tool for tool in tools if tool.name == "shell.run")

    assert shell.risk_level == RiskLevel.high
    assert shell.permission_mode == PermissionMode.approval_required
    assert shell.requires_approval is True
    assert shell.background_allowed is False
    assert shell.input_schema


def test_plan_validator_accepts_known_low_risk_steps():
    plan = BrainPlan(
        intent="inspect_repository",
        steps=[PlanStep(name="repo.scan"), PlanStep(name="context.generate")],
    )

    result = PlanValidator().validate(plan)

    assert result.valid is True
    assert "repo.scan" in result.allowed_steps
    assert "context.generate" in result.allowed_steps


def test_plan_validator_rejects_unknown_steps():
    plan = BrainPlan(intent="bad_plan", steps=[PlanStep(name="unknown.tool")])

    result = PlanValidator().validate(plan)

    assert result.valid is False
    assert "unknown.tool" in result.blocked_steps
    assert result.issues


def test_plan_validator_marks_approval_required_steps():
    plan = BrainPlan(intent="run_shell", steps=[PlanStep(name="shell.run")])

    result = PlanValidator().validate(plan)

    assert result.valid is True
    assert result.requires_approval is True
    assert "shell.run" in result.allowed_steps

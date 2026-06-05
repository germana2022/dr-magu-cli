from __future__ import annotations

from dr_magu.contracts.models import PermissionMode
from dr_magu.plans.models import BrainPlan, PlanValidationIssue, PlanValidationResult
from dr_magu.tools.registry import ToolRegistry


class PlanValidator:
    """Validates a structured Brain plan before any execution happens.

    v0.9.4 does not execute LLM plans yet. It only introduces the contract and
    safety gate that v0.10.0 will use.
    """

    def __init__(self, tool_registry: ToolRegistry | None = None) -> None:
        self.tool_registry = tool_registry or ToolRegistry()

    def validate(self, plan: BrainPlan) -> PlanValidationResult:
        tools = {tool.name: tool for tool in self.tool_registry.list_tools()}
        aliases = {alias: tool.name for tool in tools.values() for alias in tool.aliases}
        issues: list[PlanValidationIssue] = []
        allowed_steps: list[str] = []
        blocked_steps: list[str] = []
        requires_approval = bool(plan.requires_approval)

        if not plan.steps:
            issues.append(PlanValidationIssue(message="Plan does not contain executable steps."))

        for step in plan.steps:
            tool_name = aliases.get(step.name, step.name)
            tool = tools.get(tool_name)
            if tool is None:
                issues.append(PlanValidationIssue(step=step.name, message=f"Unknown tool or command '{step.name}'."))
                blocked_steps.append(step.name)
                continue

            if tool.permission_mode == PermissionMode.blocked:
                issues.append(PlanValidationIssue(step=step.name, message=f"Tool '{tool.name}' is blocked by policy."))
                blocked_steps.append(tool.name)
                continue

            if tool.requires_approval or tool.permission_mode == PermissionMode.approval_required:
                requires_approval = True

            allowed_steps.append(tool.name)

        return PlanValidationResult(
            valid=not any(issue.severity == "error" for issue in issues),
            requires_approval=requires_approval,
            issues=issues,
            allowed_steps=allowed_steps,
            blocked_steps=blocked_steps,
        )

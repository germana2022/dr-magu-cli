from __future__ import annotations

from pathlib import Path
from typing import Any

from dr_magu.hitl.engine import ApprovalEngine
from dr_magu.result import ToolResult

from .filesystem_runtime import FilesystemRuntime
from .git_runtime import GitRuntime
from .models import (
    ACTION_BLOCKED,
    ACTION_COMPLETED,
    ACTION_FAILED,
    ACTION_RUNNING,
    PLAN_BLOCKED,
    PLAN_COMPLETED,
    PLAN_FAILED,
    PLAN_RUNNING,
    ExecutionEvent,
    ExecutionPlan,
)
from .permissions import ExecutionPermissions
from .store import ExecutionStore
from .terminal_runtime import TerminalRuntime


class ExecutionExecutor:
    """Execute persisted execution plans through runtime boundaries."""

    def __init__(self, workspace_path: str | Path):
        self.workspace_path = Path(workspace_path).resolve()
        self.permissions = ExecutionPermissions()
        self.store = ExecutionStore(self.workspace_path)

    def request_approval(self, plan_id: str) -> ToolResult:
        plan = self.store.load_plan(plan_id)
        approval = ApprovalEngine(self.workspace_path).request(
            title=f"Approve execution plan: {plan.title}",
            description=plan.description,
            action="execution.plan.execute",
            risk_level="high" if any(action.requires_approval for action in plan.actions) else "medium",
        )
        updated = plan.update(approval_id=approval.data["approval"]["id"], status=PLAN_BLOCKED)
        self.store.save_plan(updated)
        self.store.append_event(
            plan.plan_id,
            ExecutionEvent("approval.requested", "Execution approval requested.", data={"approval_id": updated.approval_id}),
        )
        return ToolResult(success=True, tool="execution.approval.request", data={"plan": updated.to_dict()})

    def execute(self, plan_id: str, approved: bool = False) -> ToolResult:
        plan = self.store.load_plan(plan_id)

        if any(action.requires_approval for action in plan.actions) and not approved:
            return self.request_approval(plan_id)

        running = plan.update(status=PLAN_RUNNING)
        self.store.save_plan(running)
        self.store.append_event(plan_id, ExecutionEvent("execution.started", "Execution started."))

        action_results: list[dict[str, Any]] = []

        for action in running.actions:
            if not self.permissions.is_allowed(action.type):
                action_results.append({"action": action.to_dict(), "status": ACTION_BLOCKED, "errors": ["Action is not allowed by execution permissions."]})
                failed = running.update(status=PLAN_BLOCKED)
                self.store.save_plan(failed)
                self.store.append_event(plan_id, ExecutionEvent("action.blocked", f"Action blocked: {action.type}", action_type=action.type))
                result_payload = {"plan": failed.to_dict(), "actions": action_results}
                self.store.save_result(plan_id, result_payload)
                return ToolResult(success=False, tool="execution.plan.execute", data=result_payload, errors=["Execution plan was blocked."])

            self.store.append_event(plan_id, ExecutionEvent("action.started", f"Action started: {action.type}", action_type=action.type))
            result = self._execute_action(action)
            status = ACTION_COMPLETED if result.success else ACTION_FAILED
            action_results.append({
                "action": action.to_dict(),
                "status": status,
                "tool": result.tool,
                "data": result.data,
                "errors": result.errors,
            })
            self.store.append_event(
                plan_id,
                ExecutionEvent(
                    "action.completed" if result.success else "action.failed",
                    f"Action {'completed' if result.success else 'failed'}: {action.type}",
                    action_type=action.type,
                    data={"errors": result.errors},
                ),
            )

            if not result.success:
                failed = running.update(status=PLAN_FAILED)
                self.store.save_plan(failed)
                result_payload = {"plan": failed.to_dict(), "actions": action_results}
                self.store.save_result(plan_id, result_payload)
                return ToolResult(success=False, tool="execution.plan.execute", data=result_payload, errors=result.errors)

        completed = running.update(status=PLAN_COMPLETED)
        self.store.save_plan(completed)
        self.store.append_event(plan_id, ExecutionEvent("execution.completed", "Execution completed."))
        result_payload = {"plan": completed.to_dict(), "actions": action_results}
        result_path = self.store.save_result(plan_id, result_payload)
        result_payload["result_path"] = str(result_path)
        return ToolResult(success=True, tool="execution.plan.execute", data=result_payload)

    def inspect(self, plan_id: str) -> ToolResult:
        plan = self.store.load_plan(plan_id)
        events = self.store.load_events(plan_id)
        return ToolResult(
            success=True,
            tool="execution.plan.inspect",
            data={"plan": plan.to_dict(), "events": events, "event_count": len(events)},
        )

    def list_plans(self) -> ToolResult:
        plans = self.store.list_plans()
        return ToolResult(
            success=True,
            tool="execution.plan.list",
            data={"count": len(plans), "plans": [plan.to_dict() for plan in plans]},
        )

    def _execute_action(self, action) -> ToolResult:
        if action.type == "filesystem.read":
            return FilesystemRuntime(self.workspace_path).read(action.target)
        if action.type == "filesystem.write":
            return FilesystemRuntime(self.workspace_path).write(action.target, action.content)
        if action.type == "filesystem.delete":
            return FilesystemRuntime(self.workspace_path).delete(action.target)
        if action.type == "terminal.run":
            return TerminalRuntime(self.workspace_path).run(action.command)
        if action.type == "git.status":
            return GitRuntime(self.workspace_path).status()
        if action.type == "git.diff":
            return GitRuntime(self.workspace_path).diff()
        if action.type == "git.log":
            return GitRuntime(self.workspace_path).log()
        if action.type == "git.branch":
            return GitRuntime(self.workspace_path).branch()
        if action.type == "git.commit":
            return GitRuntime(self.workspace_path).commit(action.message)
        return ToolResult(success=False, tool=action.type, errors=[f"Unsupported execution action: {action.type}"])

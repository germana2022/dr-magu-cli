from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dr_magu.commands.context import CommandContext
from dr_magu.commands.processor import CommandProcessor
from dr_magu.commands.registry import registry
from dr_magu.config import load_config
from dr_magu.result import ToolResult

from .context import WorkflowContext
from .engine import WorkflowEngine
from .models import (
    STEP_COMPLETED,
    STEP_FAILED,
    STEP_RUNNING,
    STEP_SKIPPED,
    WORKFLOW_COMPLETED,
    WORKFLOW_FAILED,
    WORKFLOW_RUNNING,
    WorkflowDefinition,
    WorkflowHistoryEvent,
    WorkflowRunState,
)
from .store import WorkflowRunStore


class WorkflowRunner:
    """Stateful workflow orchestration runner.

    v2.5.0 turns workflows into observable orchestration runs with planning,
    sequential command execution, persisted state, context and history.
    """

    def __init__(self, workspace_path: str | Path):
        self.workspace_path = Path(workspace_path).resolve()
        self.store = WorkflowRunStore(self.workspace_path)
        self.engine = WorkflowEngine(self.workspace_path)

    def list_definitions(self) -> ToolResult:
        definitions = self.engine.list_definitions()
        return ToolResult(
            success=True,
            tool="workflow.engine.list",
            data={"count": len(definitions), "workflows": [definition.to_dict() for definition in definitions]},
        )

    def show_definition(self, workflow_id: str, variables: dict[str, Any] | None = None) -> ToolResult:
        try:
            definition = self.engine.get_definition(workflow_id, variables=variables)
            validation = self.engine.validate(definition)
            return ToolResult(
                success=validation.success,
                tool="workflow.engine.show",
                data={"workflow": definition.to_dict(), "valid": validation.success},
                errors=validation.errors,
            )
        except Exception as exc:
            return ToolResult(success=False, tool="workflow.engine.show", errors=[str(exc)])

    def plan(self, workflow_id: str, variables: dict[str, Any] | None = None) -> ToolResult:
        try:
            definition = self.engine.get_definition(workflow_id, variables=variables)
            return self.engine.plan(definition)
        except Exception as exc:
            return ToolResult(success=False, tool="workflow.engine.plan", errors=[str(exc)])

    def run(self, workflow_id: str, topic: str = "", variables: dict[str, Any] | None = None, dry_run: bool = False) -> ToolResult:
        variables = dict(variables or {})
        if topic:
            variables.setdefault("topic", topic)
        try:
            definition = self.engine.get_definition(workflow_id, variables=variables)
        except Exception as exc:
            return ToolResult(success=False, tool="workflow.engine.run", errors=[str(exc)])

        validation = self.engine.validate(definition)
        if not validation.success:
            return validation
        if dry_run:
            plan = self.engine.plan(definition)
            if plan.data is not None:
                plan.data["dry_run"] = True
            return plan

        state = WorkflowRunState.create(definition.id).update(status=WORKFLOW_RUNNING)
        context = WorkflowContext(values={"workflow_id": definition.id, "variables": variables, "topic": topic or variables.get("topic", "")})
        self.store.save_state(state)
        self.store.save_context(state.run_id, context)
        self.store.save_definition(state.run_id, definition)
        self.store.append_history(
            state.run_id,
            WorkflowHistoryEvent(
                "workflow.started",
                f"Workflow started: {definition.id}",
                data={"workflow": definition.to_dict(), "variables": variables},
            ),
        )
        return self._execute(definition, state, context, start_index=0)

    def resume(self, run_id: str) -> ToolResult:
        try:
            state = self.store.load_state(run_id)
            definition = self.store.load_definition(run_id)
            context = self.store.load_context(run_id)
        except Exception as exc:
            return ToolResult(success=False, tool="workflow.engine.resume", errors=[str(exc)])

        if state.status == WORKFLOW_COMPLETED:
            return ToolResult(success=False, tool="workflow.engine.resume", errors=[f"Workflow run is already completed: {run_id}"])
        self.store.append_history(run_id, WorkflowHistoryEvent("workflow.resume.requested", "Resume requested."))
        resumed = state.update(status=WORKFLOW_RUNNING)
        self.store.save_state(resumed)
        return self._execute(definition, resumed, context, start_index=max(0, resumed.current_step_index))

    def _execute(self, definition: WorkflowDefinition, state: WorkflowRunState, context: WorkflowContext, start_index: int) -> ToolResult:
        processor = CommandProcessor(registry)
        command_context = CommandContext(
            workspace_path=str(self.workspace_path),
            output_format="human",
            config=load_config(),
        )

        for index, step in enumerate(definition.steps[start_index:], start=start_index):
            if not step.enabled:
                context.set(step.output_key or step.id, {"status": STEP_SKIPPED, "reason": "Step disabled"})
                self.store.save_context(state.run_id, context)
                self.store.append_history(state.run_id, WorkflowHistoryEvent("step.skipped", f"Step skipped: {step.name}", step_id=step.id))
                continue

            state = state.update(current_step_index=index, status=WORKFLOW_RUNNING)
            self.store.save_state(state)
            self.store.append_history(
                state.run_id,
                WorkflowHistoryEvent(
                    "step.started",
                    f"Step started: {step.name}",
                    step_id=step.id,
                    data={"index": index, "command": step.command, "status": STEP_RUNNING},
                ),
            )

            result = processor.execute_line(step.command, command_context)
            step_payload = {
                "success": result.success,
                "status": STEP_COMPLETED if result.success else STEP_FAILED,
                "tool": result.tool,
                "command": step.command,
                "data": result.data,
                "errors": result.errors,
                "index": index,
            }
            context.set(step.output_key or step.id, step_payload)
            context.set("last_step", step_payload)
            self.store.save_context(state.run_id, context)

            if not result.success and not step.continue_on_error:
                state = state.update(status=WORKFLOW_FAILED, error="; ".join(result.errors or ["Step failed"]))
                self.store.save_state(state)
                self.store.append_history(
                    state.run_id,
                    WorkflowHistoryEvent("step.failed", f"Step failed: {step.name}", step_id=step.id, data=step_payload),
                )
                return ToolResult(
                    success=False,
                    tool="workflow.engine.run",
                    data={"run_id": state.run_id, "state": state.to_dict(), "context": context.to_dict()},
                    errors=result.errors or ["Workflow step failed."],
                )

            event_type = "step.completed" if result.success else "step.failed.continued"
            self.store.append_history(state.run_id, WorkflowHistoryEvent(event_type, f"Step completed: {step.name}", step_id=step.id, data=step_payload))

        state = state.update(
            status=WORKFLOW_COMPLETED,
            current_step_index=len(definition.steps),
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
        self.store.save_state(state)
        self.store.append_history(state.run_id, WorkflowHistoryEvent("workflow.completed", f"Workflow completed: {definition.id}"))

        return ToolResult(
            success=True,
            tool="workflow.engine.run",
            data={
                "run_id": state.run_id,
                "state": state.to_dict(),
                "context": context.to_dict(),
                "definition_path": str(self.store.run_dir(state.run_id) / "definition.json"),
                "state_path": str(self.store.run_dir(state.run_id) / "state.json"),
                "context_path": str(self.store.run_dir(state.run_id) / "context.json"),
                "history_path": str(self.store.run_dir(state.run_id) / "history.json"),
            },
        )

    def status(self, run_id: str) -> ToolResult:
        state = self.store.load_state(run_id)
        context = self.store.load_context(run_id)
        definition = self.store.load_definition(run_id)
        return ToolResult(
            success=True,
            tool="workflow.engine.status",
            data={"state": state.to_dict(), "context": context.to_dict(), "workflow": definition.to_dict()},
        )

    def history(self, run_id: str) -> ToolResult:
        state = self.store.load_state(run_id)
        return ToolResult(
            success=True,
            tool="workflow.engine.history",
            data={"state": state.to_dict(), "history": self.store.load_history(run_id)},
        )

    def list_runs(self) -> ToolResult:
        runs = self.store.list_runs()
        return ToolResult(
            success=True,
            tool="workflow.engine.runs",
            data={"count": len(runs), "runs": [run.to_dict() for run in runs]},
        )

    def _resolve_definition(self, workflow_id: str, topic: str) -> WorkflowDefinition:
        variables = {"topic": topic} if topic else {}
        return self.engine.get_definition(workflow_id, variables=variables)

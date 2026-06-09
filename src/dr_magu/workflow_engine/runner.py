from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from dr_magu.commands.context import CommandContext
from dr_magu.commands.processor import CommandProcessor
from dr_magu.commands.registry import registry
from dr_magu.config import load_config
from dr_magu.result import ToolResult

from .context import WorkflowContext
from .engine import WorkflowEngine
from .models import (
    WORKFLOW_COMPLETED,
    WORKFLOW_FAILED,
    WORKFLOW_RUNNING,
    WorkflowDefinition,
    WorkflowHistoryEvent,
    WorkflowRunState,
)
from .store import WorkflowRunStore


class WorkflowRunner:
    """Stateful workflow runner foundation."""

    def __init__(self, workspace_path: str | Path):
        self.workspace_path = Path(workspace_path).resolve()
        self.store = WorkflowRunStore(self.workspace_path)

    def run(self, workflow_id: str, topic: str = "") -> ToolResult:
        definition = self._resolve_definition(workflow_id, topic)
        validation = WorkflowEngine().validate(definition)
        if not validation.success:
            return validation

        state = WorkflowRunState.create(definition.id).update(status=WORKFLOW_RUNNING)
        context = WorkflowContext(values={"workflow_id": definition.id, "topic": topic})
        self.store.save_state(state)
        self.store.save_context(state.run_id, context)
        self.store.append_history(state.run_id, WorkflowHistoryEvent("workflow.started", f"Workflow started: {definition.id}"))

        processor = CommandProcessor(registry)
        command_context = CommandContext(
            workspace_path=str(self.workspace_path),
            output_format="human",
            config=load_config(),
        )

        for index, step in enumerate(definition.steps):
            state = state.update(current_step_index=index, status=WORKFLOW_RUNNING)
            self.store.save_state(state)
            self.store.append_history(state.run_id, WorkflowHistoryEvent("step.started", f"Step started: {step.name}", step_id=step.id))

            result = processor.execute_line(step.command, command_context)
            context.set(step.id, {
                "success": result.success,
                "tool": result.tool,
                "data": result.data,
                "errors": result.errors,
            })
            self.store.save_context(state.run_id, context)

            if not result.success:
                state = state.update(status=WORKFLOW_FAILED, error="; ".join(result.errors or ["Step failed"]))
                self.store.save_state(state)
                self.store.append_history(state.run_id, WorkflowHistoryEvent("step.failed", f"Step failed: {step.name}", step_id=step.id, data={"errors": result.errors}))
                return ToolResult(
                    success=False,
                    tool="workflow.engine.run",
                    data={"run_id": state.run_id, "state": state.to_dict(), "context": context.to_dict()},
                    errors=result.errors,
                )

            self.store.append_history(state.run_id, WorkflowHistoryEvent("step.completed", f"Step completed: {step.name}", step_id=step.id))

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
            data={"run_id": state.run_id, "state": state.to_dict(), "context": context.to_dict()},
        )

    def status(self, run_id: str) -> ToolResult:
        state = self.store.load_state(run_id)
        context = self.store.load_context(run_id)
        return ToolResult(
            success=True,
            tool="workflow.engine.status",
            data={"state": state.to_dict(), "context": context.to_dict()},
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
        if workflow_id in {"website-builder", "website.build"}:
            return WorkflowEngine().website_builder_definition(topic)
        raise KeyError(f"Unknown workflow engine workflow: {workflow_id}")

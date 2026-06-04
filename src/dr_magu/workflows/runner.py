from __future__ import annotations

import time
from pathlib import Path

from dr_magu.result import ToolResult
from dr_magu.sessions.manager import SessionManager
from dr_magu.workflows.models import WorkflowEvent, WorkflowRunMetadata, new_run_id, utc_now_iso
from dr_magu.workflows.registry import workflow_registry
from dr_magu.workflows.repository_context_workflow import run_repository_context_workflow
from dr_magu.workflows.store import WorkflowRunStore


class WorkflowRunner:
    """Execute registered workflows and persist observable run metadata."""

    def __init__(self, workspace_path: str) -> None:
        self.workspace_path = str(Path(workspace_path).resolve())
        self.store = WorkflowRunStore(self.workspace_path)

    def list_workflows(self) -> ToolResult:
        return ToolResult(
            success=True,
            tool="workflow.list",
            data={"workflows": [workflow.model_dump() for workflow in workflow_registry.list()]},
        )

    def show_workflow(self, name: str) -> ToolResult:
        try:
            workflow = workflow_registry.get(name)
            return ToolResult(success=True, tool="workflow.show", data=workflow.model_dump())
        except Exception as exc:
            return ToolResult(success=False, tool="workflow.show", errors=[str(exc)])

    def list_runs(self, limit: int | None = None) -> ToolResult:
        return ToolResult(
            success=True,
            tool="workflow.runs",
            data={"runs": [run.model_dump() for run in self.store.list_runs(limit=limit)]},
        )

    def show_last_run(self) -> ToolResult:
        latest = self.store.latest_run()
        if latest is None:
            return ToolResult(success=False, tool="workflow.last", errors=["No workflow runs found for this workspace."])
        return self.show_run(latest.id, tool_name="workflow.last")

    def show_run(self, run_id: str, tool_name: str = "workflow.run.show") -> ToolResult:
        try:
            metadata = self.store.read_run(run_id)
            state = self.store.read_state(run_id)
            events = self.store.read_events(run_id)
            return ToolResult(
                success=True,
                tool=tool_name,
                data={"run": metadata.model_dump(), "state": state, "events": events},
            )
        except Exception as exc:
            return ToolResult(success=False, tool=tool_name, errors=[str(exc)])

    def run(self, workflow_name: str) -> ToolResult:
        validation_error = self._validate_workspace()
        if validation_error:
            return ToolResult(success=False, tool="workflow.run", errors=[validation_error])

        resolved_name = workflow_registry.resolve(workflow_name)
        try:
            workflow_registry.get(resolved_name)
        except Exception as exc:
            return ToolResult(success=False, tool="workflow.run", errors=[str(exc)])

        session = SessionManager(self.workspace_path).get_or_start_current()
        metadata = WorkflowRunMetadata(
            id=new_run_id(),
            workflow=resolved_name,
            workspace_path=self.workspace_path,
            session_id=session.id,
            status="running",
        )
        self.store.create_run(metadata)
        started = time.perf_counter()
        self.store.append_event(
            metadata.id,
            WorkflowEvent(
                type="workflow.started",
                workflow=resolved_name,
                run_id=metadata.id,
                node="START",
                data={"workspace_path": self.workspace_path, "session_id": session.id},
            ),
        )

        try:
            if resolved_name == "repository.context":
                result = run_repository_context_workflow(self.workspace_path, metadata.id, self.store, session.id)
            else:
                result = ToolResult(success=False, tool="workflow.run", errors=[f"Workflow '{resolved_name}' has no runner."])
        except Exception as exc:  # pragma: no cover - safety net for user workspaces
            result = ToolResult(success=False, tool="workflow.run", errors=[str(exc)])

        metadata.duration_ms = int((time.perf_counter() - started) * 1000)
        metadata.status = "completed" if result.success else "failed"
        metadata.completed_at = utc_now_iso()
        if result.errors:
            metadata.error = "; ".join(result.errors)
        self.store.write_metadata(metadata)
        if result.data:
            result.data["duration_ms"] = metadata.duration_ms
            self.store.write_state(metadata.id, result.data)
        self.store.append_event(
            metadata.id,
            WorkflowEvent(
                type="workflow.completed" if result.success else "workflow.failed",
                workflow=resolved_name,
                run_id=metadata.id,
                node="END",
                message=metadata.error,
                duration_ms=metadata.duration_ms,
            ),
        )
        if result.data is not None:
            result.data["run_file"] = str(self.store.run_dir(metadata.id) / "run.json")
            result.data["state_file"] = str(self.store.run_dir(metadata.id) / "state.json")
            result.data["events_file"] = str(self.store.run_dir(metadata.id) / "events.jsonl")
        return result

    def _validate_workspace(self) -> str | None:
        workspace = Path(self.workspace_path)
        if not workspace.exists():
            return f"Workspace does not exist: {workspace}"
        if not workspace.is_dir():
            return f"Workspace is not a directory: {workspace}"
        try:
            has_content = any(item.name != ".dr-magu" for item in workspace.iterdir())
        except OSError as exc:
            return f"Workspace cannot be read: {exc}"
        if not has_content:
            return f"Workspace has no scannable files: {workspace}"
        return None

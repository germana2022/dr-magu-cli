from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dr_magu.result import ToolResult

from .models import WORKFLOW_CANCELLED, WORKFLOW_FAILED, WORKFLOW_PENDING, WORKFLOW_RUNNING, WorkflowHistoryEvent
from .runner import WorkflowRunner
from .store import WorkflowRunStore


class WorkflowRuntime:
    """Higher-level workflow runtime operations.

    v0.20.0 adds operational commands around the v0.19.0 runner foundation:
    inspect, cancel, retry, resume and export history.
    """

    def __init__(self, workspace_path: str | Path):
        self.workspace_path = Path(workspace_path).resolve()
        self.store = WorkflowRunStore(self.workspace_path)
        self.runner = WorkflowRunner(self.workspace_path)

    def inspect(self, run_id: str) -> ToolResult:
        state = self.store.load_state(run_id)
        context = self.store.load_context(run_id)
        history = self.store.load_history(run_id)
        return ToolResult(
            success=True,
            tool="workflow.runtime.inspect",
            data={
                "state": state.to_dict(),
                "context": context.to_dict(),
                "history_count": len(history),
                "latest_event": history[-1] if history else None,
            },
        )

    def cancel(self, run_id: str, reason: str = "") -> ToolResult:
        state = self.store.load_state(run_id)
        updated = state.update(status=WORKFLOW_CANCELLED, error=reason or "Cancelled by user.")
        self.store.save_state(updated)
        self.store.append_history(run_id, WorkflowHistoryEvent("workflow.cancelled", reason or "Workflow cancelled by user."))
        return ToolResult(success=True, tool="workflow.runtime.cancel", data={"state": updated.to_dict()})

    def retry(self, run_id: str) -> ToolResult:
        state = self.store.load_state(run_id)
        context = self.store.load_context(run_id)
        if state.status != WORKFLOW_FAILED:
            return ToolResult(
                success=False,
                tool="workflow.runtime.retry",
                errors=[f"Only failed workflow runs can be retried. Current status: {state.status}"],
            )

        topic = str(context.get("topic", ""))
        self.store.append_history(run_id, WorkflowHistoryEvent("workflow.retry.requested", "Retry requested."))
        return self.runner.run(state.workflow_id, topic=topic)

    def resume(self, run_id: str) -> ToolResult:
        state = self.store.load_state(run_id)
        context = self.store.load_context(run_id)
        if state.status not in {WORKFLOW_PENDING, WORKFLOW_RUNNING, WORKFLOW_FAILED}:
            return ToolResult(
                success=False,
                tool="workflow.runtime.resume",
                errors=[f"Workflow run cannot be resumed from status: {state.status}"],
            )

        topic = str(context.get("topic", ""))
        self.store.append_history(run_id, WorkflowHistoryEvent("workflow.resume.requested", "Resume requested."))
        return self.runner.run(state.workflow_id, topic=topic)

    def export_history(self, run_id: str, output_format: str = "json") -> ToolResult:
        state = self.store.load_state(run_id)
        history = self.store.load_history(run_id)
        run_dir = self.store.run_dir(run_id)
        run_dir.mkdir(parents=True, exist_ok=True)

        normalized = output_format.lower().strip()
        if normalized == "md":
            path = run_dir / "history.md"
            lines = [
                f"# Workflow History: {run_id}",
                "",
                f"Workflow: `{state.workflow_id}`",
                f"Status: `{state.status}`",
                "",
                "## Events",
                "",
            ]
            for event in history:
                lines.append(f"- `{event.get('timestamp')}` **{event.get('event_type')}**: {event.get('message')}")
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        else:
            path = run_dir / "history-export.json"
            path.write_text(json.dumps({"state": state.to_dict(), "history": history}, indent=2, ensure_ascii=False), encoding="utf-8")

        return ToolResult(
            success=True,
            tool="workflow.runtime.export_history",
            data={"run_id": run_id, "output_path": str(path), "format": normalized},
        )

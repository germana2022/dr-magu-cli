from __future__ import annotations

import json
from pathlib import Path

from .context import WorkflowContext
from .models import WorkflowDefinition, WorkflowHistoryEvent, WorkflowRunState


class WorkflowRunStore:
    """Persist workflow run state, context and history."""

    def __init__(self, workspace_path: str | Path):
        self.workspace_path = Path(workspace_path).resolve()
        self.base_dir = self.workspace_path / ".dr-magu" / "workflow-runs"

    def run_dir(self, run_id: str) -> Path:
        return self.base_dir / run_id

    def save_state(self, state: WorkflowRunState) -> Path:
        path = self.run_dir(state.run_id)
        path.mkdir(parents=True, exist_ok=True)
        state_path = path / "state.json"
        state_path.write_text(json.dumps(state.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        return state_path

    def load_state(self, run_id: str) -> WorkflowRunState:
        path = self.run_dir(run_id) / "state.json"
        if not path.exists():
            raise KeyError(f"Unknown workflow run: {run_id}")
        return WorkflowRunState.from_dict(json.loads(path.read_text(encoding="utf-8")))


    def save_definition(self, run_id: str, definition: WorkflowDefinition) -> Path:
        path = self.run_dir(run_id)
        path.mkdir(parents=True, exist_ok=True)
        definition_path = path / "definition.json"
        definition_path.write_text(json.dumps(definition.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        return definition_path

    def load_definition(self, run_id: str) -> WorkflowDefinition:
        path = self.run_dir(run_id) / "definition.json"
        if not path.exists():
            state = self.load_state(run_id)
            from .engine import WorkflowEngine
            context = self.load_context(run_id)
            variables = context.get("variables", {}) if hasattr(context, "get") else {}
            return WorkflowEngine(self.workspace_path).get_definition(state.workflow_id, variables=variables)
        return WorkflowDefinition.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def save_context(self, run_id: str, context: WorkflowContext) -> Path:
        path = self.run_dir(run_id)
        path.mkdir(parents=True, exist_ok=True)
        context_path = path / "context.json"
        context_path.write_text(json.dumps(context.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        return context_path

    def load_context(self, run_id: str) -> WorkflowContext:
        path = self.run_dir(run_id) / "context.json"
        if not path.exists():
            return WorkflowContext()
        return WorkflowContext.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def append_history(self, run_id: str, event: WorkflowHistoryEvent) -> Path:
        path = self.run_dir(run_id)
        path.mkdir(parents=True, exist_ok=True)
        history_path = path / "history.json"
        existing = []
        if history_path.exists():
            existing = json.loads(history_path.read_text(encoding="utf-8"))
        existing.append(event.to_dict())
        history_path.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
        return history_path

    def load_history(self, run_id: str) -> list[dict]:
        path = self.run_dir(run_id) / "history.json"
        if not path.exists():
            return []
        return json.loads(path.read_text(encoding="utf-8"))

    def list_runs(self) -> list[WorkflowRunState]:
        if not self.base_dir.exists():
            return []
        states = []
        for path in sorted(self.base_dir.glob("*/state.json")):
            states.append(WorkflowRunState.from_dict(json.loads(path.read_text(encoding="utf-8"))))
        return states

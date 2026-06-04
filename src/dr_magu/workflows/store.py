from __future__ import annotations

import json
from pathlib import Path

from dr_magu.workflows.models import WorkflowEvent, WorkflowRunMetadata


class WorkflowRunStore:
    """File-system store for workflow run metadata, state, and events."""

    def __init__(self, workspace_path: str) -> None:
        self.workspace_path = Path(workspace_path).resolve()
        self.root = self.workspace_path / ".dr-magu" / "workflows" / "runs"
        self.root.mkdir(parents=True, exist_ok=True)

    def run_dir(self, run_id: str) -> Path:
        return self.root / run_id

    def create_run(self, metadata: WorkflowRunMetadata) -> Path:
        path = self.run_dir(metadata.id)
        path.mkdir(parents=True, exist_ok=True)
        self.write_metadata(metadata)
        return path

    def write_metadata(self, metadata: WorkflowRunMetadata) -> None:
        path = self.run_dir(metadata.id)
        path.mkdir(parents=True, exist_ok=True)
        (path / "run.json").write_text(json.dumps(metadata.model_dump(), indent=2), encoding="utf-8")

    def write_state(self, run_id: str, state: dict[str, object]) -> None:
        path = self.run_dir(run_id)
        path.mkdir(parents=True, exist_ok=True)
        (path / "state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")

    def append_event(self, run_id: str, event: WorkflowEvent) -> None:
        path = self.run_dir(run_id)
        path.mkdir(parents=True, exist_ok=True)
        with (path / "events.jsonl").open("a", encoding="utf-8") as file:
            file.write(json.dumps(event.model_dump()) + "\n")

    def list_runs(self, limit: int | None = None) -> list[WorkflowRunMetadata]:
        runs: list[WorkflowRunMetadata] = []
        if not self.root.exists():
            return runs
        for run_dir in sorted(self.root.iterdir(), reverse=True):
            run_path = run_dir / "run.json"
            if not run_path.exists():
                continue
            try:
                runs.append(WorkflowRunMetadata.model_validate(json.loads(run_path.read_text(encoding="utf-8"))))
            except Exception:
                continue
        return runs[:limit] if limit is not None else runs

    def latest_run(self) -> WorkflowRunMetadata | None:
        runs = self.list_runs(limit=1)
        return runs[0] if runs else None

    def read_run(self, run_id: str) -> WorkflowRunMetadata:
        run_path = self.run_dir(run_id) / "run.json"
        if not run_path.exists():
            raise ValueError(f"Workflow run '{run_id}' was not found.")
        return WorkflowRunMetadata.model_validate(json.loads(run_path.read_text(encoding="utf-8")))

    def read_state(self, run_id: str) -> dict[str, object]:
        state_path = self.run_dir(run_id) / "state.json"
        if not state_path.exists():
            raise ValueError(f"Workflow state for run '{run_id}' was not found.")
        return json.loads(state_path.read_text(encoding="utf-8"))

    def read_events(self, run_id: str) -> list[dict[str, object]]:
        events_path = self.run_dir(run_id) / "events.jsonl"
        if not events_path.exists():
            return []
        events: list[dict[str, object]] = []
        for line in events_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return events

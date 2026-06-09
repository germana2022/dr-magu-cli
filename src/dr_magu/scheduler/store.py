from __future__ import annotations

import json
from pathlib import Path

from .models import SCHEDULE_DELETED, ScheduledTask


class ScheduleStore:
    """Persist scheduled tasks inside the workspace .dr-magu directory."""

    def __init__(self, workspace_path: str | Path):
        self.workspace_path = Path(workspace_path).resolve()
        self.schedules_dir = self.workspace_path / ".dr-magu" / "schedules"

    def save(self, task: ScheduledTask) -> Path:
        self.schedules_dir.mkdir(parents=True, exist_ok=True)
        path = self.schedules_dir / f"{task.id}.json"
        path.write_text(json.dumps(task.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def get(self, task_id: str) -> ScheduledTask:
        direct_path = self.schedules_dir / f"{task_id}.json"
        if direct_path.exists():
            return ScheduledTask.from_dict(json.loads(direct_path.read_text(encoding="utf-8")))

        for task in self.list(include_deleted=True):
            if task.name == task_id:
                return task

        raise KeyError(f"Unknown scheduled task: {task_id}")

    def list(self, include_deleted: bool = False) -> list[ScheduledTask]:
        if not self.schedules_dir.exists():
            return []

        tasks = [
            ScheduledTask.from_dict(json.loads(path.read_text(encoding="utf-8")))
            for path in sorted(self.schedules_dir.glob("*.json"))
        ]
        if include_deleted:
            return tasks
        return [task for task in tasks if task.status != SCHEDULE_DELETED]

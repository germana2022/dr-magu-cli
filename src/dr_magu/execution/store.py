from __future__ import annotations

import json
from pathlib import Path

from .models import ExecutionEvent, ExecutionPlan


class ExecutionStore:
    """Persist execution plans, logs and results."""

    def __init__(self, workspace_path: str | Path):
        self.workspace_path = Path(workspace_path).resolve()
        self.base_dir = self.workspace_path / ".dr-magu" / "execution"

    def plan_dir(self, plan_id: str) -> Path:
        return self.base_dir / plan_id

    def save_plan(self, plan: ExecutionPlan) -> Path:
        path = self.plan_dir(plan.plan_id)
        path.mkdir(parents=True, exist_ok=True)
        plan_path = path / "execution-plan.json"
        plan_path.write_text(json.dumps(plan.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        return plan_path

    def load_plan(self, plan_id: str) -> ExecutionPlan:
        path = self.plan_dir(plan_id) / "execution-plan.json"
        if not path.exists():
            raise KeyError(f"Unknown execution plan: {plan_id}")
        return ExecutionPlan.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def append_event(self, plan_id: str, event: ExecutionEvent) -> Path:
        path = self.plan_dir(plan_id)
        path.mkdir(parents=True, exist_ok=True)
        events_path = path / "execution-log.json"
        events = []
        if events_path.exists():
            events = json.loads(events_path.read_text(encoding="utf-8"))
        events.append(event.to_dict())
        events_path.write_text(json.dumps(events, indent=2, ensure_ascii=False), encoding="utf-8")
        return events_path

    def save_result(self, plan_id: str, result: dict) -> Path:
        path = self.plan_dir(plan_id)
        path.mkdir(parents=True, exist_ok=True)
        result_path = path / "execution-result.json"
        result_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        return result_path

    def list_plans(self) -> list[ExecutionPlan]:
        if not self.base_dir.exists():
            return []
        plans = []
        for path in sorted(self.base_dir.glob("*/execution-plan.json")):
            plans.append(ExecutionPlan.from_dict(json.loads(path.read_text(encoding="utf-8"))))
        return plans

    def load_events(self, plan_id: str) -> list[dict]:
        path = self.plan_dir(plan_id) / "execution-log.json"
        if not path.exists():
            return []
        return json.loads(path.read_text(encoding="utf-8"))

from __future__ import annotations

from pathlib import Path

from dr_magu.commands.context import CommandContext
from dr_magu.commands.processor import CommandProcessor
from dr_magu.commands.registry import registry
from dr_magu.config import load_config
from dr_magu.result import ToolResult

from .models import SCHEDULE_DELETED, SCHEDULE_DISABLED, SCHEDULE_ENABLED, ScheduledTask
from .store import ScheduleStore


class SchedulerRuntime:
    """Runtime for managing scheduled Dr Magu commands.

    v0.16.0 intentionally provides run-once execution and persistence. A true
    daemon/worker loop should build on this runtime in a later version.
    """

    def __init__(self, workspace_path: str | Path):
        self.workspace_path = Path(workspace_path).resolve()
        self.store = ScheduleStore(self.workspace_path)

    def create(self, name: str, command: str, cron: str, timezone_name: str = "UTC", description: str = "") -> ToolResult:
        if not name.strip():
            return ToolResult(success=False, tool="schedule.create", errors=["Schedule name is required."])
        if not command.strip():
            return ToolResult(success=False, tool="schedule.create", errors=["Schedule command is required."])
        if not cron.strip():
            return ToolResult(success=False, tool="schedule.create", errors=["Schedule cron expression is required."])

        task = ScheduledTask.create(
            name=name.strip(),
            command=command.strip(),
            cron=cron.strip(),
            timezone_name=timezone_name.strip() or "UTC",
            description=description.strip(),
        )
        path = self.store.save(task)
        return ToolResult(success=True, tool="schedule.create", data={"task": task.to_dict(), "output_path": str(path)})

    def list(self, include_deleted: bool = False) -> ToolResult:
        tasks = self.store.list(include_deleted=include_deleted)
        return ToolResult(
            success=True,
            tool="schedule.list",
            data={"count": len(tasks), "tasks": [task.to_dict() for task in tasks]},
        )

    def enable(self, task_id: str) -> ToolResult:
        task = self.store.get(task_id)
        updated = task.update(enabled=True, status=SCHEDULE_ENABLED).with_next_run()
        self.store.save(updated)
        return ToolResult(success=True, tool="schedule.enable", data={"task": updated.to_dict()})

    def disable(self, task_id: str) -> ToolResult:
        task = self.store.get(task_id)
        updated = task.update(enabled=False, status=SCHEDULE_DISABLED)
        self.store.save(updated)
        return ToolResult(success=True, tool="schedule.disable", data={"task": updated.to_dict()})

    def delete(self, task_id: str) -> ToolResult:
        task = self.store.get(task_id)
        updated = task.update(enabled=False, status=SCHEDULE_DELETED)
        self.store.save(updated)
        return ToolResult(success=True, tool="schedule.delete", data={"task": updated.to_dict()})

    def run_once(self, task_id: str) -> ToolResult:
        task = self.store.get(task_id)
        if not task.enabled or task.status != SCHEDULE_ENABLED:
            return ToolResult(success=False, tool="schedule.run", errors=[f"Schedule is not enabled: {task_id}"])

        context = CommandContext(
            workspace_path=str(self.workspace_path),
            output_format="human",
            config=load_config(),
        )
        result = CommandProcessor(registry).execute_line(task.command, context)
        updated = task.mark_run()
        self.store.save(updated)

        return ToolResult(
            success=result.success,
            tool="schedule.run",
            data={
                "task": updated.to_dict(),
                "command_result": {
                    "success": result.success,
                    "tool": result.tool,
                    "data": result.data,
                    "errors": result.errors,
                },
            },
            errors=result.errors,
        )

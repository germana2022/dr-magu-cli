from __future__ import annotations

from pathlib import Path

from dr_magu.commands.context import CommandContext
from dr_magu.commands.processor import CommandProcessor
from dr_magu.commands.registry import registry
from dr_magu.config import load_config
from dr_magu.result import ToolResult

from .models import OrchestrationPlan
from .planner import MultiAgentPlanner


class MultiAgentOrchestrator:
    """Coordinate deterministic multi-agent execution."""

    def __init__(self, workspace_path: str | Path):
        self.workspace_path = str(Path(workspace_path).resolve())
        self.processor = CommandProcessor(registry)

    def plan(self, name: str = "sdlc.pipeline", mode: str = "sequential") -> ToolResult:
        plan = MultiAgentPlanner().create_plan(name=name, mode=mode)
        return ToolResult(success=True, tool="multiagent.plan", data={"plan": plan.to_dict()})

    def run(self, name: str = "sdlc.pipeline", mode: str = "sequential", continue_on_error: bool = False) -> ToolResult:
        plan = MultiAgentPlanner().create_plan(name=name, mode=mode)
        context = CommandContext(workspace_path=self.workspace_path, output_format="human", config=load_config())
        task_results: list[dict] = []
        completed: set[str] = set()
        failed: set[str] = set()

        for task in plan.tasks:
            blocked_by = [dep for dep in task.depends_on if dep not in completed]
            if blocked_by:
                task_results.append({
                    "agent_id": task.agent_id,
                    "command": task.command,
                    "status": "skipped",
                    "reason": f"Dependencies not completed: {', '.join(blocked_by)}",
                })
                failed.add(task.agent_id)
                if not continue_on_error:
                    break
                continue

            result = self.processor.execute_line(task.command, context)
            task_results.append({
                "agent_id": task.agent_id,
                "command": task.command,
                "description": task.description,
                "status": "completed" if result.success else "failed",
                "result": {
                    "success": result.success,
                    "tool": result.tool,
                    "data": result.data,
                    "errors": result.errors,
                },
            })
            if result.success:
                completed.add(task.agent_id)
            else:
                failed.add(task.agent_id)
                if not continue_on_error:
                    break

        success = not failed
        return ToolResult(
            success=success,
            tool="multiagent.run",
            data={
                "plan": plan.to_dict(),
                "mode": mode,
                "completed": sorted(completed),
                "failed": sorted(failed),
                "results": task_results,
                "summary": f"{len(completed)} completed, {len(failed)} failed",
            },
            errors=[] if success else [f"Multi-agent orchestration failed: {', '.join(sorted(failed))}"],
        )

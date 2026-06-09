from __future__ import annotations

from pathlib import Path

from dr_magu.result import ToolResult

from .models import ExecutionAction, ExecutionPlan
from .permissions import ExecutionPermissions
from .store import ExecutionStore


class ExecutionPlanner:
    """Create execution plans from explicit action requests."""

    def __init__(self, workspace_path: str | Path):
        self.workspace_path = Path(workspace_path).resolve()
        self.permissions = ExecutionPermissions()
        self.store = ExecutionStore(self.workspace_path)

    def create_plan(self, title: str, description: str, actions: list[ExecutionAction]) -> ToolResult:
        prepared = []
        for action in actions:
            prepared.append(
                ExecutionAction(
                    type=action.type,
                    target=action.target,
                    command=action.command,
                    content=action.content,
                    message=action.message,
                    requires_approval=self.permissions.requires_approval(action.type),
                    metadata=action.metadata,
                )
            )

        plan = ExecutionPlan.create(title=title, description=description, actions=prepared)
        path = self.store.save_plan(plan)
        return ToolResult(
            success=True,
            tool="execution.plan.create",
            data={"plan": plan.to_dict(), "output_path": str(path)},
        )

    def simple_file_plan(self, target: str, content: str) -> ToolResult:
        return self.create_plan(
            title="Write Workspace File",
            description=f"Write content to {target}.",
            actions=[ExecutionAction(type="filesystem.write", target=target, content=content)],
        )

    def simple_terminal_plan(self, command: str) -> ToolResult:
        return self.create_plan(
            title="Run Terminal Command",
            description=f"Run terminal command: {command}",
            actions=[ExecutionAction(type="terminal.run", command=command)],
        )

    def simple_git_commit_plan(self, message: str) -> ToolResult:
        return self.create_plan(
            title="Create Git Commit",
            description=f"Create git commit: {message}",
            actions=[ExecutionAction(type="git.status"), ExecutionAction(type="git.commit", message=message)],
        )

from __future__ import annotations

from pathlib import Path
from typing import Any

from dr_magu.commands.registry import registry
from dr_magu.config import load_config
from dr_magu.result import ToolResult
from dr_magu.runtime.models import (
    CommandRuntimeInfo,
    PermissionRuntimeInfo,
    RuntimeContextSnapshot,
    SessionRuntimeInfo,
    ToolRuntimeInfo,
    WorkflowRuntimeInfo,
    WorkspaceRuntimeInfo,
)
from dr_magu.sessions.manager import SessionManager
from dr_magu.workflows.registry import workflow_registry


_TOOL_CATEGORIES = {"files", "git", "search", "shell", "repository", "context"}


def _is_git_repository(workspace: Path) -> bool:
    """Return true when the workspace or one of its parents contains .git."""
    if not workspace.exists() or not workspace.is_dir():
        return False
    current = workspace
    while True:
        if (current / ".git").exists():
            return True
        if current.parent == current:
            return False
        current = current.parent


def _build_workspace_info(workspace_path: str | Path) -> WorkspaceRuntimeInfo:
    workspace = Path(workspace_path).resolve()
    dr_magu_path = workspace / ".dr-magu"
    return WorkspaceRuntimeInfo(
        path=str(workspace),
        exists=workspace.exists(),
        is_directory=workspace.is_dir(),
        is_git_repository=_is_git_repository(workspace),
        dr_magu_path=str(dr_magu_path),
        has_dr_magu_directory=dr_magu_path.exists(),
    )


def _build_session_info(workspace_path: str | Path) -> SessionRuntimeInfo:
    metadata = SessionManager(workspace_path).current()
    if metadata is None:
        return SessionRuntimeInfo()
    return SessionRuntimeInfo(
        id=metadata.id,
        status=metadata.status,
        command_count=metadata.command_count,
        event_count=metadata.event_count,
        updated_at=metadata.updated_at,
    )


def _build_permissions(config: dict[str, Any]) -> PermissionRuntimeInfo:
    permissions = config.get("permissions", {}) or {}
    return PermissionRuntimeInfo(
        file_read=bool(permissions.get("file_read", False)),
        file_write=bool(permissions.get("file_write", False)),
        file_delete=bool(permissions.get("file_delete", False)),
        shell_run=bool(permissions.get("shell_run", False)),
        git_status=bool(permissions.get("git_status", False)),
        git_diff=bool(permissions.get("git_diff", False)),
        git_commit=bool(permissions.get("git_commit", False)),
        git_push=bool(permissions.get("git_push", False)),
        blocked_shell_patterns=list(config.get("blocked_shell_patterns", []) or []),
    )


def _is_read_only_tool(command_name: str) -> bool:
    """Mark currently supported tool commands as read-only from a workspace perspective."""
    return command_name not in {"shell.run"}


class RuntimeInspector:
    """Builds a unified runtime snapshot for the future Orchestrator Brain.

    The inspector intentionally does not call an LLM. It only reads local runtime
    registries, workspace metadata, session metadata, and static configuration.
    """

    def __init__(self, workspace_path: str | Path, config: dict[str, Any] | None = None) -> None:
        self.workspace_path = str(Path(workspace_path).resolve())
        self.config = config if config is not None else load_config()

    def inspect(self) -> RuntimeContextSnapshot:
        commands = [
            CommandRuntimeInfo(
                name=command.name,
                category=command.category,
                description=command.description,
                aliases=list(command.aliases),
                requires_workspace=command.requires_workspace,
                requires_approval=command.requires_approval,
            )
            for command in registry.list_commands()
        ]

        workflows = [
            WorkflowRuntimeInfo(
                name=workflow.name,
                description=workflow.description,
                workflow_type=workflow.workflow_type,
                requires_llm=workflow.requires_llm,
                aliases=list(workflow.aliases),
            )
            for workflow in workflow_registry.list()
        ]

        tools = [
            ToolRuntimeInfo(
                name=command.name,
                category=command.category,
                description=command.description,
                command=command.name,
                aliases=list(command.aliases),
                read_only=_is_read_only_tool(command.name),
                requires_approval=command.requires_approval,
            )
            for command in registry.list_commands()
            if command.category in _TOOL_CATEGORIES
        ]

        snapshot = RuntimeContextSnapshot(
            workspace=_build_workspace_info(self.workspace_path),
            session=_build_session_info(self.workspace_path),
            commands=commands,
            workflows=workflows,
            tools=tools,
            permissions=_build_permissions(self.config),
            agents=[],
            summary={
                "command_count": len(commands),
                "workflow_count": len(workflows),
                "tool_count": len(tools),
                "agent_count": 0,
                "brain_ready": True,
                "llm_required": False,
            },
        )
        return snapshot

    def inspect_result(self) -> ToolResult:
        snapshot = self.inspect()
        return ToolResult(
            success=True,
            tool="runtime.inspect",
            data=snapshot.model_dump(),
        )

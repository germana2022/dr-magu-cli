from __future__ import annotations

from typing import Any

from dr_magu.runtime.models import PermissionRuntimeInfo


class PermissionContextReader:
    """Builds a permission summary for the Brain and plan validator."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

    def read(self) -> PermissionRuntimeInfo:
        permissions = self.config.get("permissions", {}) or {}
        return PermissionRuntimeInfo(
            file_read=bool(permissions.get("file_read", False)),
            file_write=bool(permissions.get("file_write", False)),
            file_delete=bool(permissions.get("file_delete", False)),
            shell_run=bool(permissions.get("shell_run", False)),
            git_status=bool(permissions.get("git_status", False)),
            git_diff=bool(permissions.get("git_diff", False)),
            git_commit=bool(permissions.get("git_commit", False)),
            git_push=bool(permissions.get("git_push", False)),
            blocked_shell_patterns=list(self.config.get("blocked_shell_patterns", []) or []),
        )

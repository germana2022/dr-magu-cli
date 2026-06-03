from __future__ import annotations

import subprocess
from time import perf_counter
from dr_magu.result import ToolResult
from dr_magu.workspace import Workspace
from dr_magu.security.permission_guard import PermissionGuard


def run_shell(workspace_path: str, command: str, blocked_patterns: list[str] | None = None, timeout_seconds: int = 120) -> ToolResult:
    start = perf_counter()
    workspace = Workspace(workspace_path)
    guard = PermissionGuard(blocked_patterns or [])
    try:
        guard.validate_shell_command(command)
        completed = subprocess.run(
            command,
            cwd=workspace.root,
            shell=True,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
        return ToolResult(
            success=completed.returncode == 0,
            tool="shell.run",
            data={"stdout": completed.stdout, "stderr": completed.stderr, "return_code": completed.returncode},
            errors=[] if completed.returncode == 0 else [completed.stderr.strip() or "Shell command failed"],
            metadata={"duration_ms": int((perf_counter() - start) * 1000)},
        )
    except Exception as exc:
        return ToolResult(success=False, tool="shell.run", errors=[str(exc)])

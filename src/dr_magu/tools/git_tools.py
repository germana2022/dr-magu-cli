from __future__ import annotations

import subprocess
from time import perf_counter
from dr_magu.result import ToolResult
from dr_magu.workspace import Workspace


def _run_git(workspace_path: str, args: list[str], tool_name: str) -> ToolResult:
    start = perf_counter()
    workspace = Workspace(workspace_path)
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=workspace.root,
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
        return ToolResult(
            success=completed.returncode == 0,
            tool=tool_name,
            data={"stdout": completed.stdout, "stderr": completed.stderr, "return_code": completed.returncode},
            errors=[] if completed.returncode == 0 else [completed.stderr.strip() or "Git command failed"],
            metadata={"duration_ms": int((perf_counter() - start) * 1000)},
        )
    except Exception as exc:
        return ToolResult(success=False, tool=tool_name, errors=[str(exc)])


def git_status(workspace_path: str) -> ToolResult:
    return _run_git(workspace_path, ["status", "--short"], "git.status")


def git_diff(workspace_path: str) -> ToolResult:
    return _run_git(workspace_path, ["diff"], "git.diff")

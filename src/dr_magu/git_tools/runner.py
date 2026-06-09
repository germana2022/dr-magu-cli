from __future__ import annotations

import subprocess
from pathlib import Path

from dr_magu.result import ToolResult


SAFE_GIT_COMMANDS = {
    "status": ["git", "status", "--short"],
    "diff": ["git", "diff", "--stat"],
    "log": ["git", "log", "--oneline", "-10"],
    "branch": ["git", "branch", "--show-current"],
}


class GitToolRunner:
    """Safe read-only Git command runner."""

    def __init__(self, workspace_path: str | Path):
        self.workspace_path = Path(workspace_path).resolve()

    def run(self, operation: str) -> ToolResult:
        if operation not in SAFE_GIT_COMMANDS:
            return ToolResult(success=False, tool=f"git.{operation}", errors=[f"Unsupported safe git operation: {operation}"])

        try:
            result = subprocess.run(
                SAFE_GIT_COMMANDS[operation],
                cwd=str(self.workspace_path),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=20,
                check=False,
            )
            return ToolResult(
                success=result.returncode == 0,
                tool=f"git.{operation}",
                data={"operation": operation, "stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode},
                errors=[result.stderr] if result.returncode != 0 and result.stderr else [],
            )
        except Exception as exc:
            return ToolResult(success=False, tool=f"git.{operation}", errors=[str(exc)])

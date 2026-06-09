from __future__ import annotations

import subprocess
from pathlib import Path

from dr_magu.hitl.guard import requires_approval
from dr_magu.result import ToolResult


class ShellToolRunner:
    """Approval-aware shell command runner foundation."""

    def __init__(self, workspace_path: str | Path):
        self.workspace_path = Path(workspace_path).resolve()

    def run(self, command: str, approved: bool = False) -> ToolResult:
        if not command.strip():
            return ToolResult(success=False, tool="shell.run", errors=["Shell command is required."])

        if requires_approval("shell.run", "high") and not approved:
            return ToolResult(
                success=False,
                tool="shell.run",
                data={"requires_approval": True, "command": command},
                errors=["Shell execution requires approval."],
            )

        try:
            result = subprocess.run(
                command,
                cwd=str(self.workspace_path),
                shell=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
                check=False,
            )
            return ToolResult(
                success=result.returncode == 0,
                tool="shell.run",
                data={"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode},
                errors=[result.stderr] if result.returncode != 0 and result.stderr else [],
            )
        except Exception as exc:
            return ToolResult(success=False, tool="shell.run", errors=[str(exc)])

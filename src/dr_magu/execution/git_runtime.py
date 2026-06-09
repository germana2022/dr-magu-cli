from __future__ import annotations

import subprocess
from pathlib import Path

from dr_magu.result import ToolResult


class GitRuntime:
    """Git execution runtime with read and commit operations."""

    def __init__(self, workspace_path: str | Path):
        self.workspace_path = Path(workspace_path).resolve()

    def _run(self, args: list[str], tool: str) -> ToolResult:
        try:
            result = subprocess.run(
                args,
                cwd=str(self.workspace_path),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=60,
                check=False,
            )
            return ToolResult(
                success=result.returncode == 0,
                tool=tool,
                data={
                    "command": " ".join(args),
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode,
                },
                errors=[result.stderr] if result.returncode != 0 and result.stderr else [],
            )
        except Exception as exc:
            return ToolResult(success=False, tool=tool, errors=[str(exc)])

    def status(self) -> ToolResult:
        return self._run(["git", "status", "--short"], "git.status")

    def diff(self) -> ToolResult:
        return self._run(["git", "diff", "--stat"], "git.diff")

    def log(self) -> ToolResult:
        return self._run(["git", "log", "--oneline", "-10"], "git.log")

    def branch(self) -> ToolResult:
        return self._run(["git", "branch", "--show-current"], "git.branch")

    def commit(self, message: str) -> ToolResult:
        if not message.strip():
            return ToolResult(success=False, tool="git.commit", errors=["Commit message is required."])
        add_result = self._run(["git", "add", "-A"], "git.add")
        if not add_result.success:
            return add_result
        return self._run(["git", "commit", "-m", message], "git.commit")

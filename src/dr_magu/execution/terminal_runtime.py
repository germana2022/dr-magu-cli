from __future__ import annotations

import subprocess
from pathlib import Path

from dr_magu.result import ToolResult


class TerminalRuntime:
    """Cross-platform terminal execution runtime."""

    def __init__(self, workspace_path: str | Path):
        self.workspace_path = Path(workspace_path).resolve()

    def run(self, command: str, timeout: int = 60) -> ToolResult:
        if not command.strip():
            return ToolResult(success=False, tool="terminal.run", errors=["Terminal command is required."])
        try:
            result = subprocess.run(
                command,
                cwd=str(self.workspace_path),
                shell=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                check=False,
            )
            return ToolResult(
                success=result.returncode == 0,
                tool="terminal.run",
                data={
                    "command": command,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode,
                },
                errors=[result.stderr] if result.returncode != 0 and result.stderr else [],
            )
        except Exception as exc:
            return ToolResult(success=False, tool="terminal.run", errors=[str(exc)])

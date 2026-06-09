from __future__ import annotations

from pathlib import Path

from dr_magu.result import ToolResult


class FilesystemRuntime:
    """Workspace-scoped filesystem execution runtime."""

    def __init__(self, workspace_path: str | Path):
        self.workspace_path = Path(workspace_path).resolve()

    def _resolve(self, target: str) -> Path:
        path = (self.workspace_path / target).resolve()
        if path != self.workspace_path and self.workspace_path not in path.parents:
            raise ValueError("Path escapes the workspace boundary.")
        return path

    def read(self, target: str) -> ToolResult:
        try:
            path = self._resolve(target)
            return ToolResult(success=True, tool="filesystem.read", data={"path": str(path), "content": path.read_text(encoding="utf-8")})
        except Exception as exc:
            return ToolResult(success=False, tool="filesystem.read", errors=[str(exc)])

    def write(self, target: str, content: str) -> ToolResult:
        try:
            path = self._resolve(target)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            return ToolResult(success=True, tool="filesystem.write", data={"path": str(path)})
        except Exception as exc:
            return ToolResult(success=False, tool="filesystem.write", errors=[str(exc)])

    def delete(self, target: str) -> ToolResult:
        try:
            path = self._resolve(target)
            if path.is_dir():
                return ToolResult(success=False, tool="filesystem.delete", errors=["Directory deletion is not supported by the safe runtime."])
            if path.exists():
                path.unlink()
            return ToolResult(success=True, tool="filesystem.delete", data={"path": str(path)})
        except Exception as exc:
            return ToolResult(success=False, tool="filesystem.delete", errors=[str(exc)])

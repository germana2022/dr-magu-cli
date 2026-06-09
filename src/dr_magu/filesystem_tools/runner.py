from __future__ import annotations

from pathlib import Path

from dr_magu.result import ToolResult


class FilesystemToolRunner:
    """Workspace-scoped filesystem tools."""

    def __init__(self, workspace_path: str | Path):
        self.workspace_path = Path(workspace_path).resolve()

    def _resolve(self, relative_path: str) -> Path:
        path = (self.workspace_path / relative_path).resolve()
        if self.workspace_path not in path.parents and path != self.workspace_path:
            raise ValueError("Path escapes the workspace boundary.")
        return path

    def list(self, relative_path: str = ".") -> ToolResult:
        try:
            path = self._resolve(relative_path)
            items = sorted(child.name for child in path.iterdir()) if path.exists() and path.is_dir() else []
            return ToolResult(success=True, tool="fs.list", data={"path": str(path), "items": items})
        except Exception as exc:
            return ToolResult(success=False, tool="fs.list", errors=[str(exc)])

    def read(self, relative_path: str) -> ToolResult:
        try:
            path = self._resolve(relative_path)
            return ToolResult(success=True, tool="fs.read", data={"path": str(path), "content": path.read_text(encoding="utf-8")})
        except Exception as exc:
            return ToolResult(success=False, tool="fs.read", errors=[str(exc)])

    def write(self, relative_path: str, content: str) -> ToolResult:
        try:
            path = self._resolve(relative_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            return ToolResult(success=True, tool="fs.write", data={"path": str(path)})
        except Exception as exc:
            return ToolResult(success=False, tool="fs.write", errors=[str(exc)])

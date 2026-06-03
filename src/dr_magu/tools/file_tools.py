from __future__ import annotations

from pathlib import Path
from time import perf_counter
from dr_magu.result import ToolResult
from dr_magu.workspace import Workspace

IGNORED_DIRS = {".git", ".venv", "venv", "node_modules", "bin", "obj", "__pycache__"}


def list_files(workspace_path: str, target_path: str = ".", max_files: int = 500) -> ToolResult:
    start = perf_counter()
    workspace = Workspace(workspace_path)
    try:
        root = workspace.resolve(target_path)
        if not root.exists():
            raise FileNotFoundError(str(root))

        files: list[str] = []
        if root.is_file():
            files.append(str(root.relative_to(workspace.root)))
        else:
            for path in root.rglob("*"):
                if any(part in IGNORED_DIRS for part in path.parts):
                    continue
                if path.is_file():
                    files.append(str(path.relative_to(workspace.root)))
                if len(files) >= max_files:
                    break

        return ToolResult(
            success=True,
            tool="files.list",
            data={"workspace": str(workspace.root), "files": files, "count": len(files)},
            metadata={"duration_ms": int((perf_counter() - start) * 1000)},
        )
    except Exception as exc:
        return ToolResult(success=False, tool="files.list", errors=[str(exc)])


def read_file(workspace_path: str, file_path: str, max_chars: int = 20000) -> ToolResult:
    start = perf_counter()
    workspace = Workspace(workspace_path)
    try:
        path = workspace.resolve(file_path)
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(file_path)
        content = path.read_text(encoding="utf-8", errors="replace")
        truncated = len(content) > max_chars
        return ToolResult(
            success=True,
            tool="files.read",
            data={
                "path": str(path.relative_to(workspace.root)),
                "content": content[:max_chars],
                "truncated": truncated,
            },
            metadata={"duration_ms": int((perf_counter() - start) * 1000)},
        )
    except Exception as exc:
        return ToolResult(success=False, tool="files.read", errors=[str(exc)])

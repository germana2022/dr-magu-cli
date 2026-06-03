from __future__ import annotations

from time import perf_counter
from dr_magu.result import ToolResult
from dr_magu.workspace import Workspace
from dr_magu.tools.file_tools import IGNORED_DIRS

TEXT_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".cs", ".java", ".md", ".json",
    ".yaml", ".yml", ".txt", ".html", ".css", ".scss", ".xml", ".sql"
}


def search_code(workspace_path: str, query: str, target_path: str = ".", max_results: int = 100) -> ToolResult:
    start = perf_counter()
    workspace = Workspace(workspace_path)
    try:
        root = workspace.resolve(target_path)
        results: list[dict[str, object]] = []
        for path in root.rglob("*"):
            if any(part in IGNORED_DIRS for part in path.parts):
                continue
            if not path.is_file() or path.suffix.lower() not in TEXT_EXTENSIONS:
                continue
            content = path.read_text(encoding="utf-8", errors="ignore")
            for line_number, line in enumerate(content.splitlines(), start=1):
                if query.lower() in line.lower():
                    results.append({
                        "path": str(path.relative_to(workspace.root)),
                        "line": line_number,
                        "text": line.strip(),
                    })
                if len(results) >= max_results:
                    break
            if len(results) >= max_results:
                break
        return ToolResult(
            success=True,
            tool="search.code",
            data={"query": query, "results": results, "count": len(results)},
            metadata={"duration_ms": int((perf_counter() - start) * 1000)},
        )
    except Exception as exc:
        return ToolResult(success=False, tool="search.code", errors=[str(exc)])

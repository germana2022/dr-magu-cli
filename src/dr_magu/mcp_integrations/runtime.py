from __future__ import annotations

from pathlib import Path

from dr_magu.mcp_runtime.client import MCPClient
from dr_magu.mcp_runtime.registry import MCPServerRegistry
from dr_magu.result import ToolResult


class MCPIntegrationRuntime:
    """High-level MCP integration runtime."""

    def __init__(self, workspace_path: str | Path):
        self.workspace_path = Path(workspace_path).resolve()
        self.registry = MCPServerRegistry(self.workspace_path)
        self.client = MCPClient(self.workspace_path)

    def website_analyze(self, url: str) -> ToolResult:
        return self._call_by_capability("website_analysis", "website.analyze", {"url": url, "query": url}, "website.analyze")

    def web_search(self, query: str, limit: int = 5) -> ToolResult:
        server = self.registry.find_server("web_search")
        if not server:
            return ToolResult(success=False, tool="web.search", errors=["No enabled MCP server found for web_search."])
        result = self.client.call_tool(server, "web.search", {"query": query, "limit": limit})
        return ToolResult(success=result.success, tool="web.search", data=result.to_dict(), errors=[] if result.success else [result.error or "MCP web search failed."])

    def repository_read(self, repository: str) -> ToolResult:
        return self._call_by_capability("repository", "github.repository", {"repository": repository, "query": repository}, "repository.read")

    def filesystem_search(self, path: str = ".") -> ToolResult:
        return self._call_by_capability("filesystem", "filesystem.search", {"path": path, "query": path}, "filesystem.search")

    def _call_by_capability(self, capability: str, tool_name: str, arguments: dict, public_tool: str) -> ToolResult:
        server = self.registry.find_server(capability)
        if not server:
            return ToolResult(success=False, tool=public_tool, errors=[f"No enabled MCP server found for capability: {capability}"])
        result = self.client.call_tool(server, tool_name, arguments)
        return ToolResult(success=result.success, tool=public_tool, data=result.to_dict(), errors=[] if result.success else [result.error or "MCP call failed."])

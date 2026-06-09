from __future__ import annotations

from pathlib import Path

from .models import MCPServerConfig, MCPToolCall, MCPToolResult


class MCPClient:
    """MCP client boundary.

    v1.2.0 defines the MCP boundary and deterministic simulation mode. Real MCP
    process/session transport can be plugged in without changing research callers.
    """

    def __init__(self, workspace_path: str | Path, simulation_enabled: bool = True):
        self.workspace_path = Path(workspace_path).resolve()
        self.simulation_enabled = simulation_enabled

    def call_tool(self, server: MCPServerConfig, tool_name: str, arguments: dict) -> MCPToolResult:
        if not server.enabled:
            return MCPToolResult(
                success=False,
                server_id=server.id,
                tool_name=tool_name,
                error="MCP server is disabled.",
            )

        if self.simulation_enabled or not server.command:
            return self._simulate_tool_call(server, tool_name, arguments)

        # Real MCP transport is intentionally not started in v1.2.0 tests. The
        # execution boundary is explicit so future versions can add stdio/SSE
        # without changing tool contracts.
        return MCPToolResult(
            success=False,
            server_id=server.id,
            tool_name=tool_name,
            error="Real MCP transport execution is not enabled in this runtime.",
        )

    def _simulate_tool_call(self, server: MCPServerConfig, tool_name: str, arguments: dict) -> MCPToolResult:
        query = str(arguments.get("query") or arguments.get("topic") or "")
        limit = int(arguments.get("limit") or 5)

        if tool_name in {"web.search", "search"}:
            results = [
                {
                    "title": f"{query} MCP result {index}",
                    "url": f"mcp://{server.id}/result/{index}",
                    "summary": f"Simulated MCP result for {query}. Configure a real MCP server to replace this.",
                    "score": round(1.0 - ((index - 1) * 0.05), 2),
                }
                for index in range(1, limit + 1)
            ]
            return MCPToolResult(
                success=True,
                server_id=server.id,
                tool_name=tool_name,
                data={"query": query, "results": results, "count": len(results)},
                simulated=True,
            )

        return MCPToolResult(
            success=False,
            server_id=server.id,
            tool_name=tool_name,
            error=f"Unsupported MCP tool: {tool_name}",
            simulated=True,
        )

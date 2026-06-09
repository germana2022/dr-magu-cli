from __future__ import annotations

from pathlib import Path

from dr_magu.mcp_runtime.client import MCPClient
from dr_magu.mcp_runtime.registry import MCPServerRegistry

from .models import ResearchResult, ResearchSource
from .provider import DeterministicResearchProvider


class MCPResearchProvider:
    """Research provider backed by an MCP web-search boundary."""

    def __init__(self, workspace_path: str | Path, fallback_enabled: bool = True, simulation_enabled: bool = True):
        self.workspace_path = Path(workspace_path).resolve()
        self.registry = MCPServerRegistry(self.workspace_path)
        self.client = MCPClient(self.workspace_path, simulation_enabled=simulation_enabled)
        self.fallback_enabled = fallback_enabled
        self.fallback = DeterministicResearchProvider()

    def search(self, topic: str, limit: int = 5) -> ResearchResult:
        server = self.registry.find_server("web_search")
        if not server:
            if not self.fallback_enabled:
                return ResearchResult(topic=topic, query=topic, provider="mcp-unavailable", sources=[])
            return self.fallback.search(topic, limit=limit)

        call_result = self.client.call_tool(
            server,
            "web.search",
            {"query": topic, "topic": topic, "limit": limit},
        )

        if not call_result.success:
            if not self.fallback_enabled:
                return ResearchResult(topic=topic, query=topic, provider="mcp-error", sources=[])
            return self.fallback.search(topic, limit=limit)

        sources = [
            ResearchSource(
                title=str(item.get("title") or ""),
                url=str(item.get("url") or ""),
                summary=str(item.get("summary") or ""),
                score=float(item.get("score") or 0.0),
            )
            for item in call_result.data.get("results", [])
        ]

        return ResearchResult(
            topic=topic,
            query=topic,
            sources=sources,
            provider="mcp-simulated" if call_result.simulated else f"mcp:{server.id}",
        )

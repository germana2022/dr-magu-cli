from __future__ import annotations

from pathlib import Path

from dr_magu.result import ToolResult

from .provider import DeterministicResearchProvider
from .mcp_provider import MCPResearchProvider
from .store import ResearchStore


class WebResearchRunner:
    """Run research workflows through selectable real MCP providers and fallbacks."""

    def __init__(self, workspace_path: str | Path, provider_name: str | None = None, simulation_enabled: bool = False):
        import os

        self.workspace_path = Path(workspace_path).resolve()
        resolved_provider = provider_name or os.getenv("RESEARCH_PROVIDER") or "auto"
        self.provider_name = resolved_provider
        if resolved_provider == "deterministic":
            self.provider = DeterministicResearchProvider()
        else:
            self.provider = MCPResearchProvider(self.workspace_path, provider_name=resolved_provider, simulation_enabled=simulation_enabled)
        self.store = ResearchStore(self.workspace_path)

    def search(self, topic: str, limit: int = 5, persist: bool = True) -> ToolResult:
        if not topic.strip():
            return ToolResult(success=False, tool="research.search", errors=["Research topic is required."])

        result = self.provider.search(topic.strip(), limit=limit)
        output_path = self.store.save_latest(result) if persist else None

        return ToolResult(
            success=True,
            tool="research.search",
            data={
                "topic": result.topic,
                "query": result.query,
                "provider": result.provider,
                "provider_chain": result.provider_chain,
                "fallback_used": result.fallback_used,
                "source_count": len(result.sources),
                "sources": [source.to_dict() for source in result.sources],
                "output_path": str(output_path) if output_path else None,
            },
        )

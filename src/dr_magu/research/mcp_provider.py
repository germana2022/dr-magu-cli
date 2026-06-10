from __future__ import annotations

from pathlib import Path

from dr_magu.mcp_runtime.client import MCPClient
from dr_magu.mcp_runtime.registry import MCPServerRegistry

from .models import ResearchResult, ResearchSource
from .provider import DeterministicResearchProvider


CAPABILITY_BY_PROVIDER = {
    "auto": "web_search",
    "mcp": "web_search",
    "brave-search": "web_search",
    "playwright": "web_search",
    "github": "github",
    "filesystem": "filesystem",
}

TOOL_BY_PROVIDER = {
    "brave-search": "brave.search",
    "playwright": "browser.analyze",
    "github": "github.repository",
    "filesystem": "filesystem.search",
}


class MCPResearchProvider:
    """Research provider backed by operational MCP servers and fallback chains."""

    def __init__(
        self,
        workspace_path: str | Path,
        provider_name: str = "auto",
        fallback_enabled: bool = True,
        simulation_enabled: bool = True,
    ):
        self.workspace_path = Path(workspace_path).resolve()
        self.provider_name = provider_name
        self.registry = MCPServerRegistry(self.workspace_path)
        self.client = MCPClient(self.workspace_path, simulation_enabled=simulation_enabled)
        self.fallback_enabled = fallback_enabled
        self.fallback = DeterministicResearchProvider(provider="fallback-deterministic")

    def _candidate_servers(self) -> list:
        if self.provider_name in {"auto", "mcp"}:
            preferred = ["brave-search", "playwright", "github", "filesystem"]
        else:
            preferred = [self.provider_name]
            configured = self.registry.find_by_id(self.provider_name)
            if configured:
                preferred.extend(configured.fallbacks)

        servers = []
        seen = set()
        for server_id in preferred:
            server = self.registry.find_by_id(server_id, include_disabled=False)
            if server and server.id not in seen:
                servers.append(server)
                seen.add(server.id)
        if not servers and self.provider_name in {"auto", "mcp"}:
            server = self.registry.find_server("web_search")
            if server:
                servers.append(server)
        return servers

    def search(self, topic: str, limit: int = 5) -> ResearchResult:
        provider_chain: list[str] = []
        for server in self._candidate_servers():
            provider_chain.append(server.id)
            tool_name = TOOL_BY_PROVIDER.get(server.id, "web.search")
            call_result = self.client.call_tool(
                server,
                tool_name,
                {"query": topic, "topic": topic, "limit": limit, "repository": topic, "path": topic},
            )
            if not call_result.success:
                continue

            raw_results = call_result.data.get("results")
            if raw_results is None:
                raw_results = [{
                    "title": call_result.data.get("title") or f"{server.name} result for {topic}",
                    "url": call_result.data.get("url") or f"mcp://{server.id}/result",
                    "summary": call_result.data.get("summary") or str(call_result.data),
                    "score": 1.0,
                }]

            sources = [
                ResearchSource(
                    title=str(item.get("title") or ""),
                    url=str(item.get("url") or ""),
                    summary=str(item.get("summary") or ""),
                    score=float(item.get("score") or 0.0),
                )
                for item in raw_results[:limit]
            ]
            return ResearchResult(
                topic=topic,
                query=topic,
                sources=sources,
                provider=("mcp-simulated" if call_result.simulated else f"mcp:{server.id}"),
                provider_chain=provider_chain,
                fallback_used=len(provider_chain) > 1,
            )

        if self.fallback_enabled:
            fallback_result = self.fallback.search(topic, limit=limit)
            return ResearchResult(
                topic=fallback_result.topic,
                query=fallback_result.query,
                sources=fallback_result.sources,
                provider=fallback_result.provider,
                provider_chain=[*provider_chain, "fallback-deterministic"],
                fallback_used=True,
            )

        return ResearchResult(
            topic=topic,
            query=topic,
            provider="mcp-unavailable",
            sources=[],
            provider_chain=provider_chain,
            fallback_used=False,
        )

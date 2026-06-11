from __future__ import annotations

from pathlib import Path

from dr_magu.result import ToolResult

from .provider import DeterministicResearchProvider
from .mcp_provider import MCPResearchProvider
from .store import ResearchStore


class WebResearchRunner:
    """Run research workflows through selectable real MCP providers and fallbacks."""

    def __init__(
        self,
        workspace_path: str | Path,
        provider_name: str | None = None,
        simulation_enabled: bool = False,
        debug_enabled: bool = False,
    ):
        import os

        self.workspace_path = Path(workspace_path).resolve()
        resolved_provider = provider_name or os.getenv("RESEARCH_PROVIDER") or "auto"
        self.provider_name = resolved_provider
        self.debug_enabled = debug_enabled
        if resolved_provider == "deterministic":
            self.provider = DeterministicResearchProvider()
        else:
            self.provider = MCPResearchProvider(
                self.workspace_path,
                provider_name=resolved_provider,
                simulation_enabled=simulation_enabled,
                debug_enabled=debug_enabled,
            )
        self.store = ResearchStore(self.workspace_path)

    def search(self, topic: str, limit: int = 5, persist: bool = True, debug: bool | None = None) -> ToolResult:
        debug_enabled = self.debug_enabled if debug is None else debug
        if not topic.strip():
            return ToolResult(success=False, tool="research.search", errors=["Research topic is required."])

        result = self.provider.search(topic.strip(), limit=limit)
        output_path = self.store.save_latest(result) if persist else None
        debug_path = None
        if persist and result.debug:
            debug_path = self.store.save_latest_debug(result.debug)

        data = {
            "topic": result.topic,
            "query": result.query,
            "provider": result.provider,
            "provider_chain": result.provider_chain,
            "fallback_used": result.fallback_used,
            "source_count": len(result.sources),
            "sources": [source.to_dict() for source in result.sources],
            "output_path": str(output_path) if output_path else None,
        }
        if result.debug:
            data["debug_path"] = str(debug_path) if debug_path else None
            data["fallback_reason"] = result.debug.get("fallback_reason")
            data["mcp_client_attempted"] = result.debug.get("mcp_client_attempted")
            data["mcp_client_connected"] = result.debug.get("mcp_client_connected")
            data["mcp_stdio_session_attempted"] = result.debug.get("mcp_stdio_session_attempted")
            data["mcp_tool_called"] = result.debug.get("mcp_tool_called")
        if debug_enabled and result.debug:
            data["debug"] = result.debug

        return ToolResult(success=True, tool="research.search", data=data)

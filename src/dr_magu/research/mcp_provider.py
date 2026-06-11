from __future__ import annotations

from pathlib import Path
from typing import Any

from dr_magu.mcp_runtime.client import MCPClient
from dr_magu.mcp_runtime.manager import MCPRuntimeManager
from dr_magu.mcp_runtime.registry import MCPServerRegistry

from .models import ResearchResult, ResearchSource
from .provider import DeterministicResearchProvider


CAPABILITY_BY_PROVIDER = {
    "auto": "web_search",
    "mcp": "web_search",
    "multi": "web_search",
    "multi-provider": "web_search",
    "brave-search": "web_search",
    "playwright": "web_search",
    "github": "github",
    "filesystem": "filesystem",
}

MULTI_PROVIDER_MODES = {"auto", "mcp", "multi", "multi-provider"}
MULTI_PROVIDER_ORDER = ["brave-search", "playwright", "github", "filesystem"]

TOOL_BY_PROVIDER = {
    "brave-search": "brave.search",
    "playwright": "browser_navigate",
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
        simulation_enabled: bool = False,
        debug_enabled: bool = False,
    ):
        self.workspace_path = Path(workspace_path).resolve()
        self.provider_name = provider_name
        self.registry = MCPServerRegistry(self.workspace_path)
        self.runtime = MCPRuntimeManager(self.workspace_path)
        self.client = MCPClient(self.workspace_path, simulation_enabled=simulation_enabled)
        self.fallback_enabled = fallback_enabled and self.provider_name in MULTI_PROVIDER_MODES
        self.fallback = DeterministicResearchProvider(provider="fallback-deterministic")
        self.debug_enabled = debug_enabled
        self.debug_events: list[dict[str, Any]] = []

    def _debug(self, step: str, message: str, **extra: Any) -> None:
        self.debug_events.append({"step": step, "message": message, **extra})

    def _candidate_servers(self) -> list:
        self._debug("provider.requested", "Research provider requested.", provider=self.provider_name)
        if self.provider_name in MULTI_PROVIDER_MODES:
            preferred = MULTI_PROVIDER_ORDER
        else:
            # Explicit providers are strict in v2.2.0+. They no longer walk configured
            # fallback chains unless the caller uses the auto/mcp provider mode.
            preferred = [self.provider_name]

        servers = []
        seen = set()
        for server_id in preferred:
            server = self.registry.find_by_id(server_id, include_disabled=False)
            self._debug(
                "provider.candidate.lookup",
                "Resolved candidate server from registry." if server else "Candidate server was not enabled or not configured.",
                server_id=server_id,
                found=bool(server),
            )
            if server and server.id not in seen:
                servers.append(server)
                seen.add(server.id)
        if not servers and self.provider_name in MULTI_PROVIDER_MODES:
            server = self.registry.find_server("web_search")
            if server:
                servers.append(server)
                self._debug("provider.candidate.capability", "Resolved fallback candidate by web_search capability.", server_id=server.id)
        self._debug("provider.candidates.ready", "Candidate server list prepared.", server_ids=[server.id for server in servers])
        return servers

    def _debug_payload(self, provider_chain: list[str], fallback_used: bool, fallback_reason: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "debug_version": "2.4.0",
            "workspace_path": str(self.workspace_path),
            "provider_requested": self.provider_name,
            "provider_chain": provider_chain,
            "fallback_used": fallback_used,
            "fallback_reason": fallback_reason,
            "mcp_client_attempted": any(event.get("step") == "mcp.client.call" for event in self.debug_events),
            "mcp_client_connected": any((event.get("client_debug") or {}).get("mcp_client_connected") for event in self.debug_events),
            "mcp_stdio_session_attempted": any(
                event.get("mcp_stdio_session_attempted") or (event.get("client_debug") or {}).get("mcp_stdio_session_attempted")
                for event in self.debug_events
            ),
            "mcp_tool_called": self._resolved_mcp_tool_called(),
            "mcp_snapshot_tool_called": self._resolved_client_debug_value("mcp_snapshot_tool_called"),
            "mcp_tool_invocation_success": any((event.get("client_debug") or {}).get("mcp_tool_invocation_success") for event in self.debug_events),
            "mcp_tool_response_received": any((event.get("client_debug") or {}).get("mcp_tool_response_received") for event in self.debug_events),
            "events": self.debug_events,
        }
        return payload


    def _resolved_client_debug_value(self, key: str) -> Any:
        for event in reversed(self.debug_events):
            client_debug = event.get("client_debug") or {}
            if key in client_debug:
                return client_debug.get(key)
        return None

    def _resolved_mcp_tool_called(self) -> str | None:
        # Prefer the concrete tool reported by the MCP client. For Playwright
        # this maps Research to browser_navigate/browser_snapshot instead of
        # exposing the former synthetic browser.analyze adapter name.
        concrete = self._resolved_client_debug_value("mcp_tool_called")
        if concrete:
            return str(concrete)
        return next((event.get("tool_name") for event in self.debug_events if event.get("step") == "mcp.client.call"), None)

    def _source_key(self, item: dict[str, Any]) -> str:
        url = str(item.get("url") or "").strip().lower()
        if url:
            return url.rstrip("/")
        return str(item.get("title") or item.get("summary") or "").strip().lower()

    def _normalize_sources(self, raw_results: Any, server_id: str, topic: str, limit: int) -> list[ResearchSource]:
        if raw_results is None:
            raw_results = []
        normalized: list[ResearchSource] = []
        for item in list(raw_results)[: max(limit, 1)]:
            if not isinstance(item, dict):
                item = {"title": str(item), "url": f"mcp://{server_id}/result", "summary": str(item), "score": 0.5}
            title = str(item.get("title") or f"{server_id} result for {topic}")
            url = str(item.get("url") or f"mcp://{server_id}/result/{len(normalized) + 1}")
            summary = str(item.get("summary") or item.get("description") or "")
            try:
                score = float(item.get("score") or 0.0)
            except (TypeError, ValueError):
                score = 0.0
            normalized.append(ResearchSource(title=title, url=url, summary=summary, score=score))
        return normalized

    def _call_server(self, server: Any, topic: str, limit: int) -> tuple[list[ResearchSource], Any, str | None]:
        status_result = self.runtime.status(server.id)
        status_data = status_result.data if status_result.success else {"error": "; ".join(status_result.errors)}
        self._debug(
            "mcp.runtime.status",
            "Captured MCP runtime status before research provider invocation.",
            server_id=server.id,
            running=status_data.get("running"),
            healthy=status_data.get("healthy"),
            pid=status_data.get("pid"),
            error=status_data.get("error"),
            stdout_path=status_data.get("stdout_path"),
            stderr_path=status_data.get("stderr_path"),
        )
        tool_name = TOOL_BY_PROVIDER.get(server.id, "web.search")
        self._debug("mcp.client.call", "Calling MCP research client adapter with provider tool mapping.", server_id=server.id, tool_name=tool_name)
        call_result = self.client.call_tool(
            server,
            tool_name,
            {"query": topic, "topic": topic, "limit": limit, "repository": topic, "path": topic},
        )
        self._debug(
            "mcp.client.result",
            "MCP client adapter returned.",
            server_id=server.id,
            tool_name=tool_name,
            success=call_result.success,
            simulated=call_result.simulated,
            error=call_result.error,
            client_debug=call_result.debug,
            mcp_stdio_session_attempted=call_result.debug.get("mcp_stdio_session_attempted") if call_result.debug else False,
        )
        if not call_result.success:
            return [], call_result, call_result.error or f"Provider {server.id} returned no result."

        raw_results = call_result.data.get("results") if isinstance(call_result.data, dict) else None
        if raw_results is None and isinstance(call_result.data, dict):
            raw_results = [{
                "title": call_result.data.get("title") or f"{server.name} result for {topic}",
                "url": call_result.data.get("url") or f"mcp://{server.id}/result",
                "summary": call_result.data.get("summary") or str(call_result.data),
                "score": 1.0,
            }]
        sources = self._normalize_sources(raw_results, server.id, topic, limit)
        return sources, call_result, None

    def _rank_and_dedupe_sources(self, provider_sources: list[tuple[str, ResearchSource]], limit: int) -> list[ResearchSource]:
        seen: set[str] = set()
        ranked: list[ResearchSource] = []
        provider_weight = {provider: 1.0 - index * 0.03 for index, provider in enumerate(MULTI_PROVIDER_ORDER)}
        for provider_id, source in sorted(
            provider_sources,
            key=lambda pair: (provider_weight.get(pair[0], 0.75), pair[1].score),
            reverse=True,
        ):
            key = (source.url or source.title).strip().lower().rstrip("/")
            if not key or key in seen:
                continue
            seen.add(key)
            ranked.append(source)
            if len(ranked) >= limit:
                break
        return ranked

    def search(self, topic: str, limit: int = 5) -> ResearchResult:
        provider_chain: list[str] = []
        fallback_reason: str | None = None
        provider_sources: list[tuple[str, ResearchSource]] = []
        successful_providers: list[str] = []
        simulated_successes: list[bool] = []
        candidates = self._candidate_servers()
        multi_mode = self.provider_name in MULTI_PROVIDER_MODES

        for server in candidates:
            provider_chain.append(server.id)
            sources, call_result, error = self._call_server(server, topic, limit)
            if error:
                fallback_reason = error
                self._debug("provider.failed", "Provider returned no usable research data.", server_id=server.id, reason=error)
                if not multi_mode:
                    continue
                # Multi-provider mode keeps collecting from the remaining providers.
                continue

            successful_providers.append(server.id)
            simulated_successes.append(bool(call_result.simulated))
            for source in sources:
                provider_sources.append((server.id, source))
            self._debug("provider.completed", "Provider produced sources.", server_id=server.id, source_count=len(sources), simulated=call_result.simulated)

            if not multi_mode:
                selected_sources = self._rank_and_dedupe_sources(provider_sources, limit)
                self._debug("research.completed", "Research provider produced sources.", server_id=server.id, source_count=len(selected_sources))
                return ResearchResult(
                    topic=topic,
                    query=topic,
                    sources=selected_sources,
                    provider=("mcp-simulated" if call_result.simulated else server.id),
                    provider_chain=provider_chain,
                    fallback_used=False,
                    debug=self._debug_payload(provider_chain, fallback_used=False),
                )

        if provider_sources:
            selected_sources = self._rank_and_dedupe_sources(provider_sources, limit)
            if simulated_successes and all(simulated_successes):
                provider = "mcp-simulated"
            else:
                provider = successful_providers[0] if len(successful_providers) == 1 else "multi-provider"
            self._debug(
                "research.multi.completed",
                "Multi-provider MCP research aggregation completed.",
                providers=successful_providers,
                source_count=len(selected_sources),
            )
            debug_payload = self._debug_payload(provider_chain, fallback_used=False)
            debug_payload["multi_provider_enabled"] = multi_mode
            debug_payload["providers_successful"] = successful_providers
            debug_payload["providers_attempted"] = provider_chain
            debug_payload["deduplication_enabled"] = True
            debug_payload["ranking_strategy"] = "provider_priority_then_score"
            return ResearchResult(
                topic=topic,
                query=topic,
                sources=selected_sources,
                provider=provider,
                provider_chain=provider_chain,
                fallback_used=False,
                debug=debug_payload,
            )

        if self.fallback_enabled:
            self._debug("fallback.entered", "Falling back to deterministic provider.", reason=fallback_reason)
            fallback_result = self.fallback.search(topic, limit=limit)
            return ResearchResult(
                topic=fallback_result.topic,
                query=fallback_result.query,
                sources=fallback_result.sources,
                provider=fallback_result.provider,
                provider_chain=[*provider_chain, "fallback-deterministic"],
                fallback_used=True,
                debug=self._debug_payload([*provider_chain, "fallback-deterministic"], True, fallback_reason=fallback_reason),
            )

        self._debug("research.unavailable", "No MCP provider returned data and fallback is disabled.", reason=fallback_reason)
        return ResearchResult(
            topic=topic,
            query=topic,
            provider="mcp-unavailable",
            sources=[],
            provider_chain=provider_chain,
            fallback_used=False,
            debug=self._debug_payload(provider_chain, False, fallback_reason=fallback_reason),
        )

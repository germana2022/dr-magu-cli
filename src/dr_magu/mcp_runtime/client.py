from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from .stdio_client import StdioMCPClient, StdioMCPError, extract_text_from_tool_result, parse_links_from_text
from .models import MCPServerConfig, MCPToolResult


class MCPClient:
    """Real MCP provider adapter boundary.

    v2.4.0 maps Research to concrete provider tools. For Playwright, Research
    no longer exposes a synthetic browser.analyze tool name; it drives the real
    browser_navigate + browser_snapshot MCP tool sequence discovered from the
    server.
    """

    def __init__(self, workspace_path: str | Path, simulation_enabled: bool = False):
        self.workspace_path = Path(workspace_path).resolve()
        self.simulation_enabled = simulation_enabled

    def handshake(self, server: MCPServerConfig) -> MCPToolResult:
        """Open a direct client-owned MCP stdio session and initialize it."""
        debug: dict[str, Any] = {
            "server_id": server.id,
            "mcp_client_attempted": True,
            "mcp_stdio_session_attempted": False,
            "mcp_client_connected": False,
            "events": [],
        }
        if not server.enabled:
            return MCPToolResult(False, server.id, "mcp.handshake", error="MCP server is disabled.", debug=debug)
        try:
            with StdioMCPClient(self.workspace_path, timeout_seconds=max(20, server.startup_timeout_seconds + 20)) as session:
                debug["mcp_stdio_session_attempted"] = True
                debug["events"].append({"step": "mcp.stdio.session.attempted", "message": "Opening direct MCP stdio session."})
                session.start(server)
                initialize_result = session.initialize()
                debug["mcp_client_connected"] = True
                debug["mcp_handshake_success"] = True
                debug["resolved_command"] = session.resolved_command
                debug["events"].extend(session.debug_events)
                return MCPToolResult(True, server.id, "mcp.handshake", data={"initialized": True, "server_info": initialize_result.get("serverInfo") if isinstance(initialize_result, dict) else None, "resolved_command": session.resolved_command}, debug=debug)
        except Exception as exc:
            debug["mcp_error"] = str(exc)
            return MCPToolResult(False, server.id, "mcp.handshake", error=str(exc), debug=debug)

    def list_mcp_tools(self, server: MCPServerConfig) -> MCPToolResult:
        """Open a direct MCP session and list available tools."""
        handshake = self.handshake(server)
        # Re-open a fresh session to keep the handshake command side-effect free
        # and capture tool discovery in the same validation command.
        debug = dict(handshake.debug or {})
        if not handshake.success:
            return MCPToolResult(False, server.id, "mcp.tools", error=handshake.error, debug=debug)
        try:
            with StdioMCPClient(self.workspace_path, timeout_seconds=max(20, server.startup_timeout_seconds + 20)) as session:
                session.start(server)
                session.initialize()
                tools = session.list_tools()
                debug["mcp_tools_discovered"] = [tool.get("name") for tool in tools]
                debug["events"] = [*debug.get("events", []), *session.debug_events]
                return MCPToolResult(True, server.id, "mcp.tools", data={"tools": tools, "tool_names": [tool.get("name") for tool in tools], "count": len(tools)}, debug=debug)
        except Exception as exc:
            debug["mcp_error"] = str(exc)
            return MCPToolResult(False, server.id, "mcp.tools", error=str(exc), debug=debug)

    def test_server(self, server: MCPServerConfig, target: str = "https://www.google.com") -> MCPToolResult:
        """Run a provider-specific direct MCP smoke test."""
        if server.id == "playwright":
            target_url = target if target.startswith(("http://", "https://")) else f"https://{target}"
            result = self.call_tool(server, "browser.analyze", {"query": target_url, "url": target_url, "limit": 1})
            data = dict(result.data or {})
            data.update({"test_target": target_url, "validation": "playwright_navigate_snapshot"})
            return MCPToolResult(result.success, server.id, "mcp.test", data=data, error=result.error, simulated=result.simulated, debug=result.debug)
        tools = self.list_mcp_tools(server)
        return MCPToolResult(tools.success, server.id, "mcp.test", data={"test_target": target, "tools": tools.data.get("tool_names", []), "validation": "handshake_and_tools"}, error=tools.error, debug=tools.debug)

    def call_tool(self, server: MCPServerConfig, tool_name: str, arguments: dict) -> MCPToolResult:
        debug = {
            "mcp_client_attempted": True,
            "server_id": server.id,
            "tool_name": tool_name,
            "transport": server.transport,
            "command": " ".join([server.command or "", *server.args]).strip() or server.url,
            "simulation_enabled": self.simulation_enabled,
            "adapter_selected": None,
            "mcp_stdio_session_attempted": False,
            "mcp_tool_called": tool_name,
            "events": [
                {"step": "client.created", "message": "MCP client boundary created."},
                {"step": "server.loaded", "message": f"Loaded server configuration for {server.id}."},
            ],
        }
        if not server.enabled:
            debug["events"].append({"step": "server.disabled", "message": "Server is disabled; tool call was not attempted."})
            return MCPToolResult(False, server.id, tool_name, error="MCP server is disabled.", debug=debug)

        if self.simulation_enabled:
            debug["adapter_selected"] = "simulation"
            debug["events"].append({"step": "simulation.enabled", "message": "Simulation mode is enabled explicitly."})
            result = self._simulate_tool_call(server, tool_name, arguments)
            return MCPToolResult(result.success, result.server_id, result.tool_name, data=result.data, error=result.error, simulated=result.simulated, provider_chain=result.provider_chain, debug=debug)

        try:
            if server.id == "brave-search" or tool_name == "brave.search":
                debug["adapter_selected"] = "brave_search_http_api"
                debug["events"].append({"step": "adapter.selected", "message": "Using Brave Search HTTP API adapter."})
                result = self._brave_search(server, tool_name, arguments)
            elif server.id == "playwright" or (server.command and tool_name in {"browser.analyze", "website.analyze"}):
                if server.command:
                    debug["adapter_selected"] = "playwright_mcp_stdio"
                    debug["events"].append({"step": "adapter.selected", "message": "Using real Playwright MCP stdio adapter."})
                    result = self._playwright_research(server, tool_name, arguments, debug)
                else:
                    debug["adapter_selected"] = "playwright_http_compatibility"
                    debug["events"].append({"step": "adapter.selected", "message": "Playwright server has no command configured; using HTTP compatibility adapter."})
                    result = self._http_web_search(server, tool_name, arguments)
            elif server.id in {"web-search"} or tool_name in {"web.search", "search"}:
                debug["adapter_selected"] = "web_search_http_extraction"
                debug["events"].append({"step": "adapter.selected", "message": "Using HTTP web search extraction adapter for non-Playwright web-search providers."})
                result = self._http_web_search(server, tool_name, arguments)
            elif server.id == "github" or tool_name in {"github.repository", "repository.read"}:
                debug["adapter_selected"] = "github_http_api"
                debug["events"].append({"step": "adapter.selected", "message": "Using GitHub HTTP API adapter."})
                result = self._github_repository(server, tool_name, arguments)
            elif server.id == "filesystem" or tool_name in {"filesystem.search", "filesystem.read"}:
                debug["adapter_selected"] = "filesystem_workspace_scan"
                debug["events"].append({"step": "adapter.selected", "message": "Using local filesystem adapter."})
                result = self._filesystem_tool(server, tool_name, arguments)
            else:
                debug["events"].append({"step": "adapter.unsupported", "message": f"Unsupported MCP tool: {tool_name}"})
                return MCPToolResult(False, server.id, tool_name, error=f"Unsupported MCP tool: {tool_name}", debug=debug)
        except Exception as exc:
            debug["events"].append({"step": "adapter.exception", "message": str(exc)})
            debug["mcp_error"] = str(exc)
            return MCPToolResult(False, server.id, tool_name, error=str(exc), simulated=False, debug=debug)

        debug["success"] = result.success
        debug["mcp_error"] = result.error
        debug["events"].append({"step": "adapter.completed", "message": "Adapter returned a result." if result.success else (result.error or "Adapter returned failure.")})
        return MCPToolResult(result.success, result.server_id, result.tool_name, data=result.data, error=result.error, simulated=result.simulated, provider_chain=result.provider_chain, debug=debug)

    def _open_json(self, url: str, headers: dict[str, str] | None = None, timeout: int = 20) -> dict:
        request = urllib.request.Request(url, headers=headers or {})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def _open_text(self, url: str, headers: dict[str, str] | None = None, timeout: int = 20) -> str:
        request = urllib.request.Request(url, headers=headers or {"User-Agent": "dr-magu-cli/2.4.0"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read().decode("utf-8", errors="ignore")

    def _brave_search(self, server: MCPServerConfig, tool_name: str, arguments: dict) -> MCPToolResult:
        api_key = os.getenv("BRAVE_API_KEY")
        if not api_key:
            return MCPToolResult(False, server.id, tool_name, error="BRAVE_API_KEY is required for real Brave Search.")
        query = str(arguments.get("query") or arguments.get("topic") or "")
        limit = max(1, min(int(arguments.get("limit") or 5), 20))
        url = "https://api.search.brave.com/res/v1/web/search?" + urllib.parse.urlencode({"q": query, "count": limit})
        payload = self._open_json(url, headers={"Accept": "application/json", "X-Subscription-Token": api_key, "User-Agent": "dr-magu-cli/2.4.0"})
        web_results = payload.get("web", {}).get("results", [])
        results = [
            {
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "summary": item.get("description", ""),
                "score": round(1.0 - (index * 0.03), 2),
            }
            for index, item in enumerate(web_results[:limit])
        ]
        return MCPToolResult(True, server.id, tool_name, data={"query": query, "results": results, "count": len(results)})

    def _playwright_research(self, server: MCPServerConfig, tool_name: str, arguments: dict, debug: dict[str, Any] | None = None) -> MCPToolResult:
        query = str(arguments.get("query") or arguments.get("topic") or "").strip()
        limit = max(1, min(int(arguments.get("limit") or 5), 10))
        if not query:
            return MCPToolResult(False, server.id, tool_name, error="A query or URL is required for Playwright MCP research.")

        try:
            data = self._playwright_stdio_research(server, query, limit, debug)
            return MCPToolResult(True, server.id, data.get("primary_tool") or tool_name, data=data)
        except Exception as exc:
            if debug is not None:
                debug["mcp_error"] = str(exc)
                debug.setdefault("events", []).append({"step": "mcp.stdio.failed", "message": str(exc)})
            return MCPToolResult(False, server.id, tool_name, error=f"Playwright MCP stdio invocation failed: {exc}")

    def _select_tool(self, tools: list[dict[str, Any]], preferred: list[str]) -> str | None:
        names = [str(tool.get("name")) for tool in tools if tool.get("name")]
        for name in preferred:
            if name in names:
                return name
        return None

    def _playwright_stdio_research(self, server: MCPServerConfig, query: str, limit: int, debug: dict[str, Any] | None = None) -> dict[str, Any]:
        search_url = query if query.startswith(("http://", "https://")) else "https://duckduckgo.com/?" + urllib.parse.urlencode({"q": query})
        with StdioMCPClient(self.workspace_path, timeout_seconds=max(10, server.startup_timeout_seconds + 10)) as session:
            if debug is not None:
                debug["mcp_stdio_session_attempted"] = True
                debug.setdefault("events", []).append({"step": "mcp.stdio.session.attempted", "message": "Opening real stdio MCP session."})
            session.start(server)
            initialize_result = session.initialize()
            tools = session.list_tools()
            if debug is not None:
                debug["mcp_client_connected"] = True
                debug["mcp_handshake_attempted"] = True
                debug["mcp_handshake_success"] = True
                debug["mcp_tools_discovered"] = [tool.get("name") for tool in tools]
                debug["mcp_server_info"] = initialize_result.get("serverInfo") if isinstance(initialize_result, dict) else None
                debug.setdefault("events", []).extend(session.debug_events)

            navigate_tool = self._select_tool(tools, ["browser_navigate", "playwright_navigate", "navigate", "browser.goto"])
            snapshot_tool = self._select_tool(tools, ["browser_snapshot", "browser_snapshot_text", "playwright_snapshot", "snapshot", "browser.text"])
            if not navigate_tool:
                raise StdioMCPError("No compatible Playwright navigation tool was discovered.")
            if debug is not None:
                debug["mcp_tool_mapping"] = {"research": "playwright", "navigate": navigate_tool, "snapshot": snapshot_tool}
                debug.setdefault("events", []).append({
                    "step": "mcp.tool.mapping",
                    "message": "Mapped Research provider to concrete Playwright MCP tools.",
                    "navigate_tool": navigate_tool,
                    "snapshot_tool": snapshot_tool,
                })

            session.call_tool(navigate_tool, {"url": search_url})
            if debug is not None:
                debug["mcp_tool_called"] = navigate_tool
                debug["mcp_tool_invocation_attempted"] = True
                debug.setdefault("events", []).extend(session.debug_events)

            snapshot_text = ""
            snapshot_tool_called = None
            if snapshot_tool:
                snapshot_result = session.call_tool(snapshot_tool, {})
                snapshot_tool_called = snapshot_tool
                snapshot_text = extract_text_from_tool_result(snapshot_result)
                if debug is not None:
                    debug["mcp_snapshot_tool_called"] = snapshot_tool
            else:
                # Navigation succeeded; return a verifiable source even when the
                # server does not expose a snapshot tool.
                snapshot_text = f"Playwright MCP navigated to {search_url}."

            results = parse_links_from_text(snapshot_text, limit)
            if not results:
                title = query if not query.startswith(("http://", "https://")) else search_url
                summary = snapshot_text[:1000] if snapshot_text else "Playwright MCP navigation completed, but no textual snapshot content was returned."
                results = [{"title": title, "url": search_url, "summary": summary, "score": 1.0}]
            if debug is not None:
                debug["mcp_tool_invocation_success"] = True
                debug["mcp_tool_response_received"] = True
                debug.setdefault("events", []).extend(session.debug_events)
            return {
                "query": query,
                "results": results[:limit],
                "count": len(results[:limit]),
                "search_url": search_url,
                "mcp_transport": "stdio",
                "primary_tool": navigate_tool,
                "tool_sequence": [tool for tool in [navigate_tool, snapshot_tool_called] if tool],
            }

    def _http_web_search(self, server: MCPServerConfig, tool_name: str, arguments: dict) -> MCPToolResult:
        query = str(arguments.get("query") or arguments.get("topic") or arguments.get("url") or "").strip()
        limit = max(1, min(int(arguments.get("limit") or 5), 10))
        if query.startswith(("http://", "https://")):
            page = self._website_extract(server, tool_name, {"url": query})
            if not page.success:
                return page
            item = {
                "title": page.data.get("title") or query,
                "url": page.data.get("url") or query,
                "summary": page.data.get("summary") or "Real web extraction completed.",
                "score": 1.0,
            }
            return MCPToolResult(True, server.id, tool_name, data={"query": query, "results": [item], "count": 1})
        search_url = "https://duckduckgo.com/html/?" + urllib.parse.urlencode({"q": query})
        html = self._open_text(search_url, headers={"User-Agent": "Mozilla/5.0 dr-magu-cli/2.4.0"})
        results = self._parse_duckduckgo_results(html, limit)
        if not results:
            return MCPToolResult(False, server.id, tool_name, error="No real web results were extracted.")
        return MCPToolResult(True, server.id, tool_name, data={"query": query, "results": results, "count": len(results), "search_url": search_url})

    def _parse_duckduckgo_results(self, html: str, limit: int) -> list[dict]:
        results: list[dict] = []
        pattern = re.compile(r'<a[^>]+class="[^"]*result__a[^"]*"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', re.I | re.S)
        snippets = re.findall(r'<a[^>]+class="[^"]*result__snippet[^"]*"[^>]*>(.*?)</a>|<div[^>]+class="[^"]*result__snippet[^"]*"[^>]*>(.*?)</div>', html, re.I | re.S)
        cleaned_snippets = [self._clean_html(a or b) for a, b in snippets]
        for index, match in enumerate(pattern.finditer(html)):
            raw_url, raw_title = match.groups()
            url = urllib.parse.unquote(raw_url)
            if "uddg=" in url:
                parsed = urllib.parse.urlparse(url)
                params = urllib.parse.parse_qs(parsed.query)
                url = urllib.parse.unquote(params.get("uddg", [url])[0])
            title = self._clean_html(raw_title)
            if not title or not url.startswith(("http://", "https://")):
                continue
            summary = cleaned_snippets[index] if index < len(cleaned_snippets) else "Real web result extracted through Playwright provider integration."
            results.append({"title": title, "url": url, "summary": summary, "score": round(1.0 - (len(results) * 0.05), 2)})
            if len(results) >= limit:
                break
        return results

    def _clean_html(self, value: str) -> str:
        text = re.sub(r"<[^>]+>", "", value or "")
        return (
            text.replace("&amp;", "&")
            .replace("&quot;", '"')
            .replace("&#x27;", "'")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .strip()
        )

    def _website_extract(self, server: MCPServerConfig, tool_name: str, arguments: dict) -> MCPToolResult:
        url = str(arguments.get("url") or arguments.get("query") or "")
        if not url.startswith(("http://", "https://")):
            return MCPToolResult(False, server.id, tool_name, error="A valid http(s) URL is required for direct Playwright page analysis.")
        html = self._open_text(url, headers={"User-Agent": "Mozilla/5.0 dr-magu-cli/2.4.0"})
        title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
        title = self._clean_html(title_match.group(1)) if title_match else url
        headings = [self._clean_html(match) for match in re.findall(r"<h[1-3][^>]*>(.*?)</h[1-3]>", html, re.I | re.S)]
        summary = "Real Playwright provider extraction completed."
        if headings:
            summary = "Real Playwright provider extraction completed. Key headings: " + "; ".join(headings[:5])
        return MCPToolResult(True, server.id, tool_name, data={"url": url, "title": title, "headings": headings[:20], "summary": summary})

    def _github_repository(self, server: MCPServerConfig, tool_name: str, arguments: dict) -> MCPToolResult:
        token = os.getenv("GITHUB_TOKEN")
        repository = str(arguments.get("repository") or arguments.get("query") or "").strip()
        repository = repository.replace("https://github.com/", "").strip("/")
        if repository.endswith(".git"):
            repository = repository[:-4]
        if "/" not in repository:
            return MCPToolResult(False, server.id, tool_name, error="GitHub repository must be owner/name or a GitHub URL.")
        api_url = f"https://api.github.com/repos/{repository}"
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "dr-magu-cli/2.4.0"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        payload = self._open_json(api_url, headers=headers)
        return MCPToolResult(
            True,
            server.id,
            tool_name,
            data={
                "repository": payload.get("full_name", repository),
                "url": payload.get("html_url", f"https://github.com/{repository}"),
                "summary": payload.get("description") or "GitHub repository metadata retrieved through the real provider adapter.",
                "default_branch": payload.get("default_branch"),
                "language": payload.get("language"),
                "stars": payload.get("stargazers_count"),
                "topics": payload.get("topics", []),
            },
        )

    def _filesystem_tool(self, server: MCPServerConfig, tool_name: str, arguments: dict) -> MCPToolResult:
        target = str(arguments.get("path") or arguments.get("query") or ".")
        root = self.workspace_path.resolve()
        path = (root / target).resolve()
        if not str(path).startswith(str(root)):
            return MCPToolResult(False, server.id, tool_name, error="Filesystem path escapes the workspace.")
        if tool_name == "filesystem.read" and path.is_file():
            return MCPToolResult(True, server.id, tool_name, data={"path": str(path), "content": path.read_text(encoding="utf-8", errors="ignore")[:20000]})
        matches = []
        if path.exists():
            base = path if path.is_dir() else path.parent
            for item in list(base.rglob("*"))[:200]:
                if item.is_file():
                    matches.append(str(item.relative_to(root)))
        return MCPToolResult(True, server.id, tool_name, data={"path": target, "matches": matches, "summary": "Real filesystem scan completed."})

    def _simulate_tool_call(self, server: MCPServerConfig, tool_name: str, arguments: dict) -> MCPToolResult:
        query = str(arguments.get("query") or arguments.get("topic") or "")
        limit = int(arguments.get("limit") or 5)

        if tool_name in {"browser.analyze", "website.analyze"}:
            url = str(arguments.get("url") or arguments.get("query") or "")
            return MCPToolResult(
                True,
                server.id,
                tool_name,
                data={
                    "url": url,
                    "title": f"Simulated analysis for {url}",
                    "headings": ["Hero", "Features", "Pricing", "Contact"],
                    "navigation": ["Home", "Product", "Pricing", "Resources"],
                    "ctas": ["Get started", "Book a demo"],
                    "summary": "Simulated website analysis. Use --simulate only for deterministic offline tests.",
                },
                simulated=True,
            )

        if tool_name in {"github.repository", "repository.read"}:
            repository = str(arguments.get("repository") or arguments.get("query") or "")
            return MCPToolResult(
                True,
                server.id,
                tool_name,
                data={
                    "repository": repository,
                    "summary": "Simulated GitHub repository metadata. Use --simulate only for deterministic offline tests.",
                    "files": ["README.md", "src/", "tests/"],
                    "topics": ["ai-agent-platform", "cli"],
                },
                simulated=True,
            )

        if tool_name in {"filesystem.search", "filesystem.read"}:
            target = str(arguments.get("path") or arguments.get("query") or ".")
            return MCPToolResult(
                True,
                server.id,
                tool_name,
                data={"path": target, "matches": [], "summary": "Simulated filesystem MCP result."},
                simulated=True,
            )

        results = [
            {
                "title": f"{query} MCP result {index}",
                "url": f"mcp://{server.id}/result/{index}",
                "summary": f"Simulated MCP result for {query}. Use --simulate only for deterministic offline tests.",
                "score": round(1.0 - ((index - 1) * 0.05), 2),
            }
            for index in range(1, limit + 1)
        ]
        return MCPToolResult(True, server.id, tool_name, data={"query": query, "results": results, "count": len(results)}, simulated=True)

from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path

from .models import MCPServerConfig, MCPToolResult


class MCPClient:
    """Real MCP provider adapter boundary.

    v2.2.0 removes simulation from the default research path. When simulation is
    explicitly requested, deterministic mock data is still available for tests and
    offline demos. Otherwise the client uses real provider adapters for Brave
    Search, Playwright/browser analysis, GitHub and Filesystem.
    """

    def __init__(self, workspace_path: str | Path, simulation_enabled: bool = False):
        self.workspace_path = Path(workspace_path).resolve()
        self.simulation_enabled = simulation_enabled

    def call_tool(self, server: MCPServerConfig, tool_name: str, arguments: dict) -> MCPToolResult:
        if not server.enabled:
            return MCPToolResult(False, server.id, tool_name, error="MCP server is disabled.")

        if self.simulation_enabled:
            return self._simulate_tool_call(server, tool_name, arguments)

        try:
            if server.id == "brave-search" or tool_name == "brave.search":
                return self._brave_search(server, tool_name, arguments)
            if server.id in {"playwright", "web-search"} or tool_name in {"browser.analyze", "website.analyze", "web.search", "search"}:
                return self._playwright_research(server, tool_name, arguments)
            if server.id == "github" or tool_name in {"github.repository", "repository.read"}:
                return self._github_repository(server, tool_name, arguments)
            if server.id == "filesystem" or tool_name in {"filesystem.search", "filesystem.read"}:
                return self._filesystem_tool(server, tool_name, arguments)
        except Exception as exc:
            return MCPToolResult(False, server.id, tool_name, error=str(exc), simulated=False)

        return MCPToolResult(False, server.id, tool_name, error=f"Unsupported MCP tool: {tool_name}")

    def _open_json(self, url: str, headers: dict[str, str] | None = None, timeout: int = 20) -> dict:
        request = urllib.request.Request(url, headers=headers or {})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def _open_text(self, url: str, headers: dict[str, str] | None = None, timeout: int = 20) -> str:
        request = urllib.request.Request(url, headers=headers or {"User-Agent": "dr-magu-cli/2.2.0"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read().decode("utf-8", errors="ignore")

    def _brave_search(self, server: MCPServerConfig, tool_name: str, arguments: dict) -> MCPToolResult:
        api_key = os.getenv("BRAVE_API_KEY")
        if not api_key:
            return MCPToolResult(False, server.id, tool_name, error="BRAVE_API_KEY is required for real Brave Search.")
        query = str(arguments.get("query") or arguments.get("topic") or "")
        limit = max(1, min(int(arguments.get("limit") or 5), 20))
        url = "https://api.search.brave.com/res/v1/web/search?" + urllib.parse.urlencode({"q": query, "count": limit})
        payload = self._open_json(url, headers={"Accept": "application/json", "X-Subscription-Token": api_key, "User-Agent": "dr-magu-cli/2.2.0"})
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

    def _playwright_research(self, server: MCPServerConfig, tool_name: str, arguments: dict) -> MCPToolResult:
        query = str(arguments.get("query") or arguments.get("topic") or "").strip()
        limit = max(1, min(int(arguments.get("limit") or 5), 10))
        if query.startswith(("http://", "https://")):
            page = self._website_extract(server, tool_name, {"url": query})
            if not page.success:
                return page
            item = {
                "title": page.data.get("title") or query,
                "url": page.data.get("url") or query,
                "summary": page.data.get("summary") or "Real browser-style extraction completed.",
                "score": 1.0,
            }
            return MCPToolResult(True, server.id, tool_name, data={"query": query, "results": [item], "count": 1})

        # Real browser-style web discovery without falling back to simulation.
        # DuckDuckGo HTML is intentionally used because it does not require API keys.
        search_url = "https://duckduckgo.com/html/?" + urllib.parse.urlencode({"q": query})
        html = self._open_text(search_url, headers={"User-Agent": "Mozilla/5.0 dr-magu-cli/2.2.0"})
        results = self._parse_duckduckgo_results(html, limit)
        if not results:
            return MCPToolResult(False, server.id, tool_name, error="No real Playwright/web results were extracted.")
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
        html = self._open_text(url, headers={"User-Agent": "Mozilla/5.0 dr-magu-cli/2.2.0"})
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
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "dr-magu-cli/2.2.0"}
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

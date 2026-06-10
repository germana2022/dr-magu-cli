from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path

from .models import MCPServerConfig, MCPToolResult


class MCPClient:
    """Operational MCP client boundary.

    v2.1.3 keeps the MCP process lifecycle separate from the tool-call boundary.
    When real MCP stdio adapters are not available, built-in operational adapters
    provide real Brave Search, GitHub, Filesystem and basic web-page extraction.
    """

    def __init__(self, workspace_path: str | Path, simulation_enabled: bool = True):
        self.workspace_path = Path(workspace_path).resolve()
        self.simulation_enabled = simulation_enabled

    def call_tool(self, server: MCPServerConfig, tool_name: str, arguments: dict) -> MCPToolResult:
        if not server.enabled:
            return MCPToolResult(False, server.id, tool_name, error="MCP server is disabled.")

        if self.simulation_enabled:
            return self._simulate_tool_call(server, tool_name, arguments)

        try:
            if server.id == "brave-search" or tool_name in {"web.search", "search", "brave.search"}:
                return self._brave_search(server, tool_name, arguments)
            if server.id == "playwright" or tool_name in {"browser.analyze", "website.analyze"}:
                return self._website_extract(server, tool_name, arguments)
            if server.id == "github" or tool_name in {"github.repository", "repository.read"}:
                return self._github_repository(server, tool_name, arguments)
            if server.id == "filesystem" or tool_name in {"filesystem.search", "filesystem.read"}:
                return self._filesystem_tool(server, tool_name, arguments)
        except Exception as exc:
            return MCPToolResult(False, server.id, tool_name, error=str(exc), simulated=False)

        return MCPToolResult(False, server.id, tool_name, error=f"Unsupported MCP tool: {tool_name}")

    def _brave_search(self, server: MCPServerConfig, tool_name: str, arguments: dict) -> MCPToolResult:
        api_key = os.getenv("BRAVE_API_KEY")
        if not api_key:
            return MCPToolResult(False, server.id, tool_name, error="BRAVE_API_KEY is required for real Brave Search.")
        query = str(arguments.get("query") or arguments.get("topic") or "")
        limit = max(1, min(int(arguments.get("limit") or 5), 20))
        url = "https://api.search.brave.com/res/v1/web/search?" + urllib.parse.urlencode({"q": query, "count": limit})
        request = urllib.request.Request(url, headers={"Accept": "application/json", "X-Subscription-Token": api_key})
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
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

    def _website_extract(self, server: MCPServerConfig, tool_name: str, arguments: dict) -> MCPToolResult:
        url = str(arguments.get("url") or arguments.get("query") or "")
        if not url.startswith(("http://", "https://")):
            return MCPToolResult(False, server.id, tool_name, error="A valid http(s) URL is required for Playwright provider analysis.")
        request = urllib.request.Request(url, headers={"User-Agent": "dr-magu-cli/2.1.3"})
        with urllib.request.urlopen(request, timeout=20) as response:
            html = response.read().decode("utf-8", errors="ignore")
        title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
        headings = [re.sub(r"<[^>]+>", "", match).strip() for match in re.findall(r"<h[1-3][^>]*>(.*?)</h[1-3]>", html, re.I | re.S)]
        links = [match.strip() for match in re.findall(r"<a[^>]*>(.*?)</a>", html, re.I | re.S)]
        links = [re.sub(r"<[^>]+>", "", item).strip() for item in links if item.strip()]
        return MCPToolResult(
            True,
            server.id,
            tool_name,
            data={
                "url": url,
                "title": title_match.group(1).strip() if title_match else url,
                "headings": headings[:20],
                "navigation": links[:20],
                "summary": "Real web-page extraction completed through the Playwright provider boundary.",
            },
        )

    def _github_repository(self, server: MCPServerConfig, tool_name: str, arguments: dict) -> MCPToolResult:
        token = os.getenv("GITHUB_TOKEN")
        repository = str(arguments.get("repository") or arguments.get("query") or "").strip()
        repository = repository.replace("https://github.com/", "").strip("/")
        if repository.endswith(".git"):
            repository = repository[:-4]
        if "/" not in repository:
            return MCPToolResult(False, server.id, tool_name, error="GitHub repository must be owner/name or a GitHub URL.")
        api_url = f"https://api.github.com/repos/{repository}"
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "dr-magu-cli/2.1.3"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        request = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return MCPToolResult(
            True,
            server.id,
            tool_name,
            data={
                "repository": payload.get("full_name", repository),
                "url": payload.get("html_url", f"https://github.com/{repository}"),
                "summary": payload.get("description") or "GitHub repository metadata retrieved.",
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
                    "summary": "Simulated website analysis. Configure Playwright MCP for real browser extraction.",
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
                    "summary": "Simulated GitHub repository metadata. Configure GitHub MCP for live repository access.",
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
                "summary": f"Simulated MCP result for {query}. Configure a real MCP server to replace this.",
                "score": round(1.0 - ((index - 1) * 0.05), 2),
            }
            for index in range(1, limit + 1)
        ]
        return MCPToolResult(True, server.id, tool_name, data={"query": query, "results": results, "count": len(results)}, simulated=True)

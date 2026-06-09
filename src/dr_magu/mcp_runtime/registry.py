from __future__ import annotations

import json
import os
from pathlib import Path

from .models import MCPServerConfig


def _env_args(name: str) -> list[str]:
    raw = os.getenv(name)
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    except json.JSONDecodeError:
        pass
    return [part for part in raw.split(" ") if part]


DEFAULT_MCP_SERVERS = [
    MCPServerConfig(
        id="playwright",
        name="Playwright MCP",
        transport="stdio",
        command=os.getenv("MCP_PLAYWRIGHT_COMMAND") or "npx",
        args=_env_args("MCP_PLAYWRIGHT_ARGS") or ["@playwright/mcp"],
        enabled=os.getenv("MCP_PLAYWRIGHT_ENABLED", "false").lower() in {"1", "true", "yes", "on"},
        capabilities=["browser", "web_scraping", "website_analysis", "screenshot", "web_search"],
    ),
    MCPServerConfig(
        id="brave-search",
        name="Brave Search MCP",
        transport="stdio",
        command=os.getenv("MCP_BRAVE_SEARCH_COMMAND"),
        args=_env_args("MCP_BRAVE_SEARCH_ARGS"),
        enabled=bool(os.getenv("MCP_BRAVE_SEARCH_COMMAND")) or os.getenv("MCP_BRAVE_SEARCH_ENABLED", "false").lower() in {"1", "true", "yes", "on"},
        capabilities=["web_search", "research", "news_search"],
    ),
    MCPServerConfig(
        id="github",
        name="GitHub MCP",
        transport="stdio",
        command=os.getenv("MCP_GITHUB_COMMAND"),
        args=_env_args("MCP_GITHUB_ARGS"),
        enabled=bool(os.getenv("MCP_GITHUB_COMMAND")) or os.getenv("MCP_GITHUB_ENABLED", "false").lower() in {"1", "true", "yes", "on"},
        capabilities=["github", "repository", "pull_request", "issues"],
    ),
    MCPServerConfig(
        id="filesystem",
        name="Filesystem MCP",
        transport="stdio",
        command=os.getenv("MCP_FILESYSTEM_COMMAND"),
        args=_env_args("MCP_FILESYSTEM_ARGS"),
        enabled=bool(os.getenv("MCP_FILESYSTEM_COMMAND")) or os.getenv("MCP_FILESYSTEM_ENABLED", "false").lower() in {"1", "true", "yes", "on"},
        capabilities=["filesystem", "files_read", "files_write", "workspace"],
    ),
]


class MCPServerRegistry:
    """Loads MCP server configuration from workspace config and environment."""

    def __init__(self, workspace_path: str | Path):
        self.workspace_path = Path(workspace_path).resolve()

    def config_path(self) -> Path:
        return self.workspace_path / ".dr-magu" / "config" / "mcp_servers.json"

    def list_servers(self) -> list[MCPServerConfig]:
        path = self.config_path()
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            return [MCPServerConfig.from_dict(item) for item in payload.get("servers", [])]

        env_json = os.getenv("MCP_SERVERS_JSON")
        if env_json:
            try:
                payload = json.loads(env_json)
                return [MCPServerConfig.from_dict(item) for item in payload.get("servers", [])]
            except json.JSONDecodeError:
                return DEFAULT_MCP_SERVERS

        return DEFAULT_MCP_SERVERS

    def enabled_servers(self) -> list[MCPServerConfig]:
        return [server for server in self.list_servers() if server.enabled]

    def find_server(self, capability: str) -> MCPServerConfig | None:
        for server in self.enabled_servers():
            if capability in server.capabilities:
                return server
        return None

    def find_by_id(self, server_id: str) -> MCPServerConfig | None:
        for server in self.list_servers():
            if server.id == server_id:
                return server
        return None

    def to_dict(self) -> dict:
        servers = self.list_servers()
        return {
            "count": len(servers),
            "enabled_count": len([server for server in servers if server.enabled]),
            "servers": [server.to_dict() for server in servers],
            "config_path": str(self.config_path()),
        }

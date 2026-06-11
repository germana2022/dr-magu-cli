from __future__ import annotations

import json
import os
from pathlib import Path

from .models import MCPServerConfig

TRUE_VALUES = {"1", "true", "yes", "on"}


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


def _env_enabled(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.lower() in TRUE_VALUES


DEFAULT_MCP_SERVERS = [
    MCPServerConfig(
        id="brave-search",
        name="Brave Search MCP",
        transport="stdio",
        command=os.getenv("MCP_BRAVE_SEARCH_COMMAND") or "npx",
        args=_env_args("MCP_BRAVE_SEARCH_ARGS") or ["-y", "@modelcontextprotocol/server-brave-search"],
        enabled=_env_enabled("MCP_BRAVE_SEARCH_ENABLED", False),
        auto_start=_env_enabled("MCP_BRAVE_SEARCH_AUTO_START", True),
        required_env=["BRAVE_API_KEY"],
        capabilities=["web_search", "research", "news_search"],
        fallbacks=["playwright", "filesystem"],
    ),
    MCPServerConfig(
        id="playwright",
        name="Playwright MCP",
        transport="stdio",
        command=os.getenv("MCP_PLAYWRIGHT_COMMAND") or "npx",
        args=_env_args("MCP_PLAYWRIGHT_ARGS") or ["-y", "@playwright/mcp"],
        enabled=_env_enabled("MCP_PLAYWRIGHT_ENABLED", False),
        auto_start=_env_enabled("MCP_PLAYWRIGHT_AUTO_START", True),
        required_env=[],
        capabilities=["browser", "web_scraping", "website_analysis", "screenshot", "web_search"],
        fallbacks=["brave-search", "filesystem"],
    ),
    MCPServerConfig(
        id="github",
        name="GitHub MCP",
        transport="stdio",
        command=os.getenv("MCP_GITHUB_COMMAND") or "npx",
        args=_env_args("MCP_GITHUB_ARGS") or ["-y", "@modelcontextprotocol/server-github"],
        enabled=_env_enabled("MCP_GITHUB_ENABLED", False),
        auto_start=_env_enabled("MCP_GITHUB_AUTO_START", True),
        required_env=["GITHUB_TOKEN"],
        capabilities=["github", "repository", "pull_request", "issues"],
        fallbacks=["filesystem"],
    ),
    MCPServerConfig(
        id="filesystem",
        name="Filesystem MCP",
        transport="stdio",
        command=os.getenv("MCP_FILESYSTEM_COMMAND") or "npx",
        args=_env_args("MCP_FILESYSTEM_ARGS") or ["-y", "@modelcontextprotocol/server-filesystem", "."],
        enabled=_env_enabled("MCP_FILESYSTEM_ENABLED", False),
        auto_start=_env_enabled("MCP_FILESYSTEM_AUTO_START", True),
        required_env=[],
        capabilities=["filesystem", "files_read", "files_write", "workspace", "research"],
        fallbacks=[],
    ),
]


class MCPServerRegistry:
    """Loads and persists MCP server configuration from workspace config and environment."""

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

    def save_servers(self, servers: list[MCPServerConfig]) -> Path:
        path = self.config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"version": "2.2.0", "servers": [server.to_dict() for server in servers]}
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path

    def initialize_config(self, overwrite: bool = False) -> Path:
        path = self.config_path()
        if overwrite or not path.exists():
            self.save_servers(DEFAULT_MCP_SERVERS)
        return path

    def enabled_servers(self) -> list[MCPServerConfig]:
        return [server for server in self.list_servers() if server.enabled]

    def find_server(self, capability: str, include_disabled: bool = False) -> MCPServerConfig | None:
        servers = self.list_servers() if include_disabled else self.enabled_servers()
        for server in servers:
            if capability in server.capabilities:
                return server
        return None

    def find_by_id(self, server_id: str, include_disabled: bool = True) -> MCPServerConfig | None:
        servers = self.list_servers() if include_disabled else self.enabled_servers()
        for server in servers:
            if server.id == server_id:
                return server
        return None

    def set_enabled(self, server_id: str, enabled: bool) -> MCPServerConfig:
        servers = self.list_servers()
        updated: list[MCPServerConfig] = []
        selected: MCPServerConfig | None = None
        for server in servers:
            if server.id == server_id:
                selected = server.with_enabled(enabled)
                updated.append(selected)
            else:
                updated.append(server)
        if selected is None:
            raise KeyError(f"Unknown MCP server: {server_id}")
        self.save_servers(updated)
        return selected

    def discover(self) -> list[MCPServerConfig]:
        discovered = self.list_servers()
        if not self.config_path().exists():
            self.save_servers(discovered)
        return discovered

    def to_dict(self) -> dict:
        servers = self.list_servers()
        return {
            "count": len(servers),
            "enabled_count": len([server for server in servers if server.enabled]),
            "servers": [server.to_dict() for server in servers],
            "config_path": str(self.config_path()),
        }

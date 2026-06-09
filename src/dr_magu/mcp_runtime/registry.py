from __future__ import annotations

import json
import os
from pathlib import Path

from .models import MCPServerConfig


DEFAULT_MCP_SERVERS = [
    MCPServerConfig(
        id="web-search",
        name="Web Search MCP",
        transport="stdio",
        command=os.getenv("MCP_WEB_SEARCH_COMMAND"),
        args=[],
        enabled=bool(os.getenv("MCP_WEB_SEARCH_COMMAND")),
        capabilities=["web_search", "research"],
    )
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

    def to_dict(self) -> dict:
        servers = self.list_servers()
        return {
            "count": len(servers),
            "enabled_count": len([server for server in servers if server.enabled]),
            "servers": [server.to_dict() for server in servers],
            "config_path": str(self.config_path()),
        }

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class MCPServerConfig:
    """MCP server configuration."""

    id: str
    name: str
    transport: str = "stdio"
    command: str | None = None
    args: list[str] = field(default_factory=list)
    url: str | None = None
    enabled: bool = True
    capabilities: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "transport": self.transport,
            "command": self.command,
            "args": self.args,
            "url": self.url,
            "enabled": self.enabled,
            "capabilities": self.capabilities,
        }

    @staticmethod
    def from_dict(payload: dict[str, Any]) -> "MCPServerConfig":
        return MCPServerConfig(
            id=str(payload.get("id") or ""),
            name=str(payload.get("name") or payload.get("id") or ""),
            transport=str(payload.get("transport") or "stdio"),
            command=payload.get("command"),
            args=[str(arg) for arg in payload.get("args", [])],
            url=payload.get("url"),
            enabled=bool(payload.get("enabled", True)),
            capabilities=[str(item) for item in payload.get("capabilities", [])],
        )


@dataclass(frozen=True)
class MCPToolCall:
    """MCP tool call request."""

    server_id: str
    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "server_id": self.server_id,
            "tool_name": self.tool_name,
            "arguments": self.arguments,
        }


@dataclass(frozen=True)
class MCPToolResult:
    """MCP tool call result."""

    success: bool
    server_id: str
    tool_name: str
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    simulated: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "server_id": self.server_id,
            "tool_name": self.tool_name,
            "data": self.data,
            "error": self.error,
            "simulated": self.simulated,
        }

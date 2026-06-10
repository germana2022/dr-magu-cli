from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class MCPServerConfig:
    """Operational MCP server configuration."""

    id: str
    name: str
    transport: str = "stdio"
    command: str | None = None
    args: list[str] = field(default_factory=list)
    url: str | None = None
    enabled: bool = True
    auto_start: bool = False
    health_check: bool = True
    required_env: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    fallbacks: list[str] = field(default_factory=list)
    startup_timeout_seconds: int = 10

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "transport": self.transport,
            "command": self.command,
            "args": self.args,
            "url": self.url,
            "enabled": self.enabled,
            "auto_start": self.auto_start,
            "health_check": self.health_check,
            "required_env": self.required_env,
            "capabilities": self.capabilities,
            "fallbacks": self.fallbacks,
            "startup_timeout_seconds": self.startup_timeout_seconds,
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
            auto_start=bool(payload.get("auto_start", False)),
            health_check=bool(payload.get("health_check", True)),
            required_env=[str(item) for item in payload.get("required_env", [])],
            capabilities=[str(item) for item in payload.get("capabilities", [])],
            fallbacks=[str(item) for item in payload.get("fallbacks", [])],
            startup_timeout_seconds=int(payload.get("startup_timeout_seconds") or 10),
        )

    def with_enabled(self, enabled: bool) -> "MCPServerConfig":
        data = self.to_dict()
        data["enabled"] = enabled
        return MCPServerConfig.from_dict(data)


@dataclass(frozen=True)
class MCPServerStatus:
    """Runtime status snapshot for one MCP server."""

    server_id: str
    enabled: bool
    configured: bool
    running: bool
    healthy: bool
    command: str | None = None
    pid: int | None = None
    missing_env: list[str] = field(default_factory=list)
    error: str | None = None
    checked_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "server_id": self.server_id,
            "enabled": self.enabled,
            "configured": self.configured,
            "running": self.running,
            "healthy": self.healthy,
            "command": self.command,
            "pid": self.pid,
            "missing_env": self.missing_env,
            "error": self.error,
            "checked_at": self.checked_at,
        }


@dataclass(frozen=True)
class MCPToolCall:
    """MCP tool call request."""

    server_id: str
    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"server_id": self.server_id, "tool_name": self.tool_name, "arguments": self.arguments}


@dataclass(frozen=True)
class MCPToolResult:
    """MCP tool call result."""

    success: bool
    server_id: str
    tool_name: str
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    simulated: bool = False
    provider_chain: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "server_id": self.server_id,
            "tool_name": self.tool_name,
            "data": self.data,
            "error": self.error,
            "simulated": self.simulated,
            "provider_chain": self.provider_chain,
        }

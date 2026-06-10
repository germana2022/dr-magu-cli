from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from dr_magu.result import ToolResult

from .models import MCPServerConfig, MCPServerStatus, utc_now
from .registry import MCPServerRegistry


class MCPRuntimeManager:
    """Operational lifecycle manager for local MCP server processes."""

    def __init__(self, workspace_path: str | Path):
        self.workspace_path = Path(workspace_path).resolve()
        self.registry = MCPServerRegistry(self.workspace_path)
        self.state_dir = self.workspace_path / ".dr-magu" / "mcp_runtime"
        self.state_path = self.state_dir / "processes.json"

    def _read_state(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return {}
        try:
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def _write_state(self, state: dict[str, Any]) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def _is_pid_running(self, pid: int | None) -> bool:
        if not pid:
            return False
        try:
            if sys.platform.startswith("win"):
                completed = subprocess.run(["tasklist", "/FI", f"PID eq {pid}"], capture_output=True, text=True, timeout=5)
                return str(pid) in completed.stdout
            os.kill(pid, 0)
            return True
        except Exception:
            return False

    def _missing_env(self, server: MCPServerConfig) -> list[str]:
        return [name for name in server.required_env if not os.getenv(name)]

    def list(self) -> ToolResult:
        statuses = [self.status(server.id).data for server in self.registry.list_servers()]
        return ToolResult(success=True, tool="mcp.list", data={"servers": statuses, "state_path": str(self.state_path)})

    def status(self, server_id: str) -> ToolResult:
        server = self.registry.find_by_id(server_id)
        if server is None:
            return ToolResult(success=False, tool="mcp.status", errors=[f"Unknown MCP server: {server_id}"])
        state = self._read_state().get(server_id, {})
        pid = state.get("pid")
        running = self._is_pid_running(pid)
        missing_env = self._missing_env(server)
        configured = bool(server.command or server.url)
        healthy = server.enabled and configured and running and not missing_env
        if not server.enabled:
            error = "MCP server is disabled."
        elif missing_env:
            error = f"Missing required environment variables: {', '.join(missing_env)}"
        elif not configured:
            error = "MCP server command or URL is not configured."
        elif not running:
            error = "MCP server is not running."
        else:
            error = None
        status = MCPServerStatus(
            server_id=server.id,
            enabled=server.enabled,
            configured=configured,
            running=running,
            healthy=healthy,
            command=" ".join([server.command or "", *server.args]).strip() or server.url,
            pid=pid if running else None,
            missing_env=missing_env,
            error=error,
        )
        return ToolResult(success=True, tool="mcp.status", data=status.to_dict())

    def health(self, server_id: str) -> ToolResult:
        result = self.status(server_id)
        if not result.success:
            return result
        return ToolResult(success=True, tool="mcp.health", data=result.data)

    def start(self, server_id: str) -> ToolResult:
        server = self.registry.find_by_id(server_id)
        if server is None:
            return ToolResult(success=False, tool="mcp.start", errors=[f"Unknown MCP server: {server_id}"])
        if not server.enabled:
            return ToolResult(success=False, tool="mcp.start", errors=["MCP server is disabled. Enable it before starting."])
        missing_env = self._missing_env(server)
        if missing_env:
            return ToolResult(success=False, tool="mcp.start", errors=[f"Missing required environment variables: {', '.join(missing_env)}"])
        if server.transport != "stdio":
            return ToolResult(success=False, tool="mcp.start", errors=[f"Unsupported runtime transport for start: {server.transport}"])
        if not server.command:
            return ToolResult(success=False, tool="mcp.start", errors=["MCP server command is not configured."])

        current = self.status(server_id).data
        if current.get("running"):
            return ToolResult(success=True, tool="mcp.start", data={"server_id": server_id, "status": "already-running", "pid": current.get("pid")})

        try:
            process = subprocess.Popen(
                [server.command, *server.args],
                cwd=str(self.workspace_path),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            time.sleep(min(1.0, max(0.1, server.startup_timeout_seconds / 10)))
            if process.poll() is not None:
                _, stderr = process.communicate(timeout=2)
                return ToolResult(success=False, tool="mcp.start", errors=[stderr.strip() or "MCP process exited during startup."])
            state = self._read_state()
            state[server_id] = {"pid": process.pid, "started_at": utc_now(), "command": [server.command, *server.args]}
            self._write_state(state)
            return ToolResult(success=True, tool="mcp.start", data={"server_id": server_id, "status": "started", "pid": process.pid})
        except FileNotFoundError:
            return ToolResult(success=False, tool="mcp.start", errors=[f"Command not found: {server.command}"])
        except Exception as exc:
            return ToolResult(success=False, tool="mcp.start", errors=[str(exc)])

    def stop(self, server_id: str) -> ToolResult:
        state = self._read_state()
        entry = state.get(server_id, {})
        pid = entry.get("pid")
        if not self._is_pid_running(pid):
            state.pop(server_id, None)
            self._write_state(state)
            return ToolResult(success=True, tool="mcp.stop", data={"server_id": server_id, "status": "not-running"})
        try:
            if sys.platform.startswith("win"):
                subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, text=True, timeout=10)
            else:
                os.kill(pid, 15)
            state.pop(server_id, None)
            self._write_state(state)
            return ToolResult(success=True, tool="mcp.stop", data={"server_id": server_id, "status": "stopped", "pid": pid})
        except Exception as exc:
            return ToolResult(success=False, tool="mcp.stop", errors=[str(exc)])

    def restart(self, server_id: str) -> ToolResult:
        self.stop(server_id)
        return self.start(server_id)

    def enable(self, server_id: str) -> ToolResult:
        try:
            server = self.registry.set_enabled(server_id, True)
            return ToolResult(success=True, tool="mcp.enable", data=server.to_dict())
        except KeyError as exc:
            return ToolResult(success=False, tool="mcp.enable", errors=[str(exc)])

    def disable(self, server_id: str) -> ToolResult:
        try:
            server = self.registry.set_enabled(server_id, False)
            self.stop(server_id)
            return ToolResult(success=True, tool="mcp.disable", data=server.to_dict())
        except KeyError as exc:
            return ToolResult(success=False, tool="mcp.disable", errors=[str(exc)])

    def discover(self) -> ToolResult:
        servers = self.registry.discover()
        return ToolResult(success=True, tool="mcp.discover", data={"servers": [server.to_dict() for server in servers], "config_path": str(self.registry.config_path())})

    def boot(self) -> ToolResult:
        started = []
        skipped = []
        for server in self.registry.enabled_servers():
            if not server.auto_start:
                skipped.append({"server_id": server.id, "reason": "auto_start=false"})
                continue
            result = self.start(server.id)
            if result.success:
                started.append(result.data)
            else:
                skipped.append({"server_id": server.id, "reason": "; ".join(result.errors)})
        return ToolResult(success=True, tool="mcp.boot", data={"started": started, "skipped": skipped})

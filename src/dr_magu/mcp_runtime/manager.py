from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from dr_magu.result import ToolResult

from .models import MCPServerConfig, MCPServerStatus, utc_now
from .registry import MCPServerRegistry


_PROCESS_TABLE: dict[str, subprocess.Popen] = {}


class MCPRuntimeManager:
    """Operational lifecycle manager for local MCP server processes."""

    def __init__(self, workspace_path: str | Path):
        self.workspace_path = Path(workspace_path).resolve()
        self.registry = MCPServerRegistry(self.workspace_path)
        self.state_dir = self.workspace_path / ".dr-magu" / "mcp_runtime"
        self.state_path = self.state_dir / "processes.json"
        self.logs_dir = self.state_dir / "logs"

    def _process_key(self, server_id: str) -> str:
        return f"{self.workspace_path}:{server_id}"

    def _log_paths(self, server_id: str) -> dict[str, Path]:
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        safe_id = server_id.replace("/", "_").replace("\\", "_")
        return {
            "stdout": self.logs_dir / f"{safe_id}.stdout.log",
            "stderr": self.logs_dir / f"{safe_id}.stderr.log",
        }

    def _tail_file(self, path: str | Path | None, max_bytes: int = 4096) -> str:
        if not path:
            return ""
        file_path = Path(path)
        if not file_path.exists():
            return ""
        try:
            with file_path.open("rb") as handle:
                handle.seek(0, os.SEEK_END)
                size = handle.tell()
                handle.seek(max(0, size - max_bytes))
                return handle.read().decode("utf-8", errors="replace").strip()
        except OSError:
            return ""

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


    def _resolve_command(self, command: str) -> str | None:
        """Resolve an MCP command in a cross-platform way.

        Windows commonly exposes npm package executables as .cmd shims
        (for example npx.cmd). The runtime accepts portable config values such
        as "npx" and resolves them to the concrete executable available in
        the current process PATH before spawning the MCP server.
        """
        raw = (command or "").strip()
        if not raw:
            return None

        expanded = os.path.expandvars(os.path.expanduser(raw))
        candidate_path = Path(expanded)
        if candidate_path.is_file():
            return str(candidate_path)

        candidates = [expanded]
        if sys.platform.startswith("win") and Path(expanded).suffix == "":
            candidates.extend([f"{expanded}.cmd", f"{expanded}.exe", f"{expanded}.bat"])

        for candidate in candidates:
            resolved = shutil.which(candidate)
            if resolved:
                return resolved
        return None

    def _missing_env(self, server: MCPServerConfig) -> list[str]:
        return [name for name in server.required_env if not os.getenv(name)]

    def list(self) -> ToolResult:
        statuses = [self.status(server.id).data for server in self.registry.list_servers()]
        return ToolResult(success=True, tool="mcp.list", data={"servers": statuses, "state_path": str(self.state_path)})

    def status(self, server_id: str) -> ToolResult:
        server = self.registry.find_by_id(server_id)
        if server is None:
            return ToolResult(success=False, tool="mcp.status", errors=[f"Unknown MCP server: {server_id}"])

        state = self._read_state()
        entry = state.get(server_id, {})
        process = _PROCESS_TABLE.get(self._process_key(server_id))
        exit_code = None
        if process is not None:
            exit_code = process.poll()
            if exit_code is None:
                entry = {**entry, "pid": process.pid}
                state[server_id] = entry
                self._write_state(state)
            else:
                entry = {**entry, "pid": process.pid, "last_exit_code": exit_code, "stopped_at": utc_now()}
                state[server_id] = entry
                self._write_state(state)
                _PROCESS_TABLE.pop(self._process_key(server_id), None)

        pid = entry.get("pid")
        running = bool(process is not None and exit_code is None) or self._is_pid_running(pid)
        missing_env = self._missing_env(server)
        configured = bool(server.command or server.url)
        resolved_command = self._resolve_command(server.command) if server.command else None
        command_available = bool(resolved_command or server.url)
        healthy = server.enabled and configured and command_available and running and not missing_env
        stderr_tail = self._tail_file(entry.get("stderr_path"))
        if not server.enabled:
            error = "MCP server is disabled."
        elif missing_env:
            error = f"Missing required environment variables: {', '.join(missing_env)}"
        elif not configured:
            error = "MCP server command or URL is not configured."
        elif not command_available:
            error = f"Command not found in PATH: {server.command}"
        elif not running:
            last_exit_code = entry.get("last_exit_code")
            if last_exit_code is not None:
                error = f"MCP server exited with code {last_exit_code}."
            else:
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
        data = status.to_dict()
        data["resolved_command"] = resolved_command
        data["command_available"] = command_available
        data["state_path"] = str(self.state_path)
        if entry.get("stdout_path"):
            data["stdout_path"] = entry.get("stdout_path")
        if entry.get("stderr_path"):
            data["stderr_path"] = entry.get("stderr_path")
        if entry.get("last_exit_code") is not None:
            data["last_exit_code"] = entry.get("last_exit_code")
        if stderr_tail:
            data["stderr_tail"] = stderr_tail
        return ToolResult(success=True, tool="mcp.status", data=data)

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
        resolved_command = self._resolve_command(server.command)
        if not resolved_command:
            return ToolResult(
                success=False,
                tool="mcp.start",
                errors=[f"Command not found in PATH: {server.command}"],
                data={"server_id": server_id, "command": server.command, "args": server.args},
            )

        current = self.status(server_id).data
        if current.get("running"):
            return ToolResult(
                success=True,
                tool="mcp.start",
                data={
                    "server_id": server_id,
                    "status": "already-running",
                    "pid": current.get("pid"),
                    "resolved_command": resolved_command,
                    "state_path": str(self.state_path),
                },
            )

        log_paths = self._log_paths(server_id)
        try:
            stdout_handle = log_paths["stdout"].open("ab")
            stderr_handle = log_paths["stderr"].open("ab")
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform.startswith("win") else 0
            process = subprocess.Popen(
                [resolved_command, *server.args],
                cwd=str(self.workspace_path),
                stdin=subprocess.PIPE,
                stdout=stdout_handle,
                stderr=stderr_handle,
                creationflags=creationflags,
            )
            stdout_handle.close()
            stderr_handle.close()
            state = self._read_state()
            state[server_id] = {
                "pid": process.pid,
                "started_at": utc_now(),
                "command": [resolved_command, *server.args],
                "configured_command": server.command,
                "resolved_command": resolved_command,
                "stdout_path": str(log_paths["stdout"]),
                "stderr_path": str(log_paths["stderr"]),
            }
            self._write_state(state)
            _PROCESS_TABLE[self._process_key(server_id)] = process

            time.sleep(min(1.0, max(0.1, server.startup_timeout_seconds / 10)))
            exit_code = process.poll()
            if exit_code is not None:
                state = self._read_state()
                entry = state.get(server_id, {})
                entry.update({"last_exit_code": exit_code, "stopped_at": utc_now()})
                state[server_id] = entry
                self._write_state(state)
                _PROCESS_TABLE.pop(self._process_key(server_id), None)
                stderr_tail = self._tail_file(log_paths["stderr"])
                message = f"MCP process exited during startup with code {exit_code}."
                if stderr_tail:
                    message = f"{message} stderr: {stderr_tail}"
                return ToolResult(
                    success=False,
                    tool="mcp.start",
                    errors=[message],
                    data={
                        "server_id": server_id,
                        "status": "exited",
                        "pid": process.pid,
                        "exit_code": exit_code,
                        "resolved_command": resolved_command,
                        "stderr_path": str(log_paths["stderr"]),
                    },
                )
            return ToolResult(
                success=True,
                tool="mcp.start",
                data={
                    "server_id": server_id,
                    "status": "started",
                    "pid": process.pid,
                    "resolved_command": resolved_command,
                    "state_path": str(self.state_path),
                    "stdout_path": str(log_paths["stdout"]),
                    "stderr_path": str(log_paths["stderr"]),
                },
            )
        except FileNotFoundError:
            return ToolResult(success=False, tool="mcp.start", errors=[f"Command not found in PATH: {server.command}"])
        except Exception as exc:
            return ToolResult(success=False, tool="mcp.start", errors=[str(exc)])

    def stop(self, server_id: str) -> ToolResult:
        state = self._read_state()
        entry = state.get(server_id, {})
        pid = entry.get("pid")
        process = _PROCESS_TABLE.pop(self._process_key(server_id), None)
        try:
            if process is not None and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                if process.stdin:
                    try:
                        process.stdin.close()
                    except OSError:
                        pass
                state.pop(server_id, None)
                self._write_state(state)
                return ToolResult(success=True, tool="mcp.stop", data={"server_id": server_id, "status": "stopped", "pid": process.pid})

            if not self._is_pid_running(pid):
                state.pop(server_id, None)
                self._write_state(state)
                return ToolResult(success=True, tool="mcp.stop", data={"server_id": server_id, "status": "not-running"})

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

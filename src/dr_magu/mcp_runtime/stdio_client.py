from __future__ import annotations

import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse
from pathlib import Path
from typing import Any

from .models import MCPServerConfig


class StdioMCPError(RuntimeError):
    """Raised when a stdio MCP session cannot be established or used."""


class StdioMCPClient:
    """Minimal JSON-RPC client for MCP servers using stdio transport.

    The operational runtime can keep a server process alive for lifecycle
    observability, but stdio MCP communication requires a client-owned process.
    This client opens a short-lived MCP stdio session, performs the JSON-RPC
    handshake, discovers tools, invokes tools, and shuts the session down.
    """

    def __init__(self, workspace_path: str | Path, timeout_seconds: float = 20.0):
        self.workspace_path = Path(workspace_path).resolve()
        self.timeout_seconds = timeout_seconds
        self._next_id = 1
        self.process: subprocess.Popen | None = None
        self._reader_queue: queue.Queue[dict[str, Any] | Exception] = queue.Queue()
        self.debug_events: list[dict[str, Any]] = []
        self.resolved_command: str | None = None

    def _event(self, step: str, message: str, **extra: Any) -> None:
        self.debug_events.append({"step": step, "message": message, **extra})

    def _resolve_command(self, command: str | None) -> str | None:
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

    def __enter__(self) -> "StdioMCPClient":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def start(self, server: MCPServerConfig) -> None:
        if server.transport != "stdio":
            raise StdioMCPError(f"Unsupported MCP transport: {server.transport}")
        resolved = self._resolve_command(server.command)
        self.resolved_command = resolved
        self._event("mcp.transport.resolve", "Resolved stdio MCP command.", command=server.command, resolved_command=resolved)
        if not resolved:
            raise StdioMCPError(f"Command not found in PATH: {server.command}")
        self._event("mcp.stdio.session.start", "Starting client-owned stdio MCP process.", command=[resolved, *server.args])
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform.startswith("win") else 0
        self.process = subprocess.Popen(
            [resolved, *server.args],
            cwd=str(self.workspace_path),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=creationflags,
        )
        threading.Thread(target=self._stderr_reader, daemon=True).start()
        threading.Thread(target=self._stdout_reader, daemon=True).start()

    def _stderr_reader(self) -> None:
        if not self.process or not self.process.stderr:
            return
        try:
            for raw in iter(self.process.stderr.readline, b""):
                text = raw.decode("utf-8", errors="replace").strip()
                if text:
                    self._event("mcp.stderr", text)
        except Exception as exc:  # pragma: no cover - defensive background reader
            self._event("mcp.stderr.error", str(exc))

    def _stdout_reader(self) -> None:
        if not self.process or not self.process.stdout:
            return
        try:
            while True:
                message = self._read_framed_message(self.process.stdout)
                if message is None:
                    break
                self._reader_queue.put(message)
        except Exception as exc:  # pragma: no cover - defensive background reader
            self._reader_queue.put(exc)

    def _read_framed_message(self, stream: Any) -> dict[str, Any] | None:
        """Read one MCP JSON-RPC message from stdio.

        MCP stdio servers commonly use newline-delimited JSON-RPC messages.
        Older Dr Magu versions used LSP-style Content-Length frames, which can
        make Playwright MCP hang forever waiting for initialize input. This
        reader supports both formats so Dr Magu remains compatible with either
        transport convention.
        """
        first_line = stream.readline()
        if not first_line:
            return None

        text = first_line.decode("utf-8", errors="replace").strip()
        if not text:
            return self._read_framed_message(stream)

        if text.lower().startswith("content-length:"):
            match = re.search(r"Content-Length:\s*(\d+)", text, re.I)
            if not match:
                raise StdioMCPError(f"Invalid MCP frame header: {text!r}")
            length = int(match.group(1))
            # Consume remaining header lines until the blank line.
            while True:
                header_line = stream.readline()
                if not header_line or header_line in {b"\r\n", b"\n"}:
                    break
            body = stream.read(length)
            if not body:
                return None
            return json.loads(body.decode("utf-8"))

        return json.loads(text)

    def _write_message(self, payload: dict[str, Any]) -> None:
        if not self.process or not self.process.stdin:
            raise StdioMCPError("MCP stdio process is not started.")
        # MCP stdio uses newline-delimited JSON-RPC messages. Do not use
        # Content-Length framing here; Playwright MCP waits for newline JSON.
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8") + b"\n"
        self.process.stdin.write(body)
        self.process.stdin.flush()

    def _request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        request_id = self._next_id
        self._next_id += 1
        self._event("mcp.jsonrpc.request", f"Calling {method}.", method=method, request_id=request_id)
        self._write_message({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}})
        deadline = time.time() + self.timeout_seconds
        while time.time() < deadline:
            remaining = max(0.05, deadline - time.time())
            try:
                item = self._reader_queue.get(timeout=remaining)
            except queue.Empty:
                break
            if isinstance(item, Exception):
                raise StdioMCPError(str(item))
            if item.get("id") != request_id:
                self._event("mcp.jsonrpc.notification", "Received non-matching MCP message.", payload=item)
                continue
            if "error" in item:
                raise StdioMCPError(json.dumps(item["error"], ensure_ascii=False))
            self._event("mcp.jsonrpc.response", f"Received {method} response.", method=method, request_id=request_id)
            return item.get("result", {})
        raise StdioMCPError(f"Timeout waiting for MCP response to {method}.")

    def initialize(self) -> dict[str, Any]:
        result = self._request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "dr-magu-cli", "version": "2.7.0"},
            },
        )
        self._write_message({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
        self._event("mcp.handshake.success", "MCP initialize handshake completed.")
        return result

    def list_tools(self) -> list[dict[str, Any]]:
        result = self._request("tools/list", {})
        tools = result.get("tools", []) if isinstance(result, dict) else []
        self._event("mcp.tools.discovered", "Discovered MCP tools.", tool_names=[tool.get("name") for tool in tools])
        return tools

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        self._event("mcp.tool.invoke", "Invoking MCP tool.", tool_name=name, arguments=arguments or {})
        result = self._request("tools/call", {"name": name, "arguments": arguments or {}})
        self._event("mcp.tool.response", "Received MCP tool response.", tool_name=name)
        return result

    def close(self) -> None:
        process = self.process
        self.process = None
        if not process:
            return
        try:
            if process.stdin:
                process.stdin.close()
        except OSError:
            pass
        try:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
        except Exception:  # pragma: no cover - defensive cleanup
            pass


def extract_text_from_tool_result(result: dict[str, Any]) -> str:
    """Flatten common MCP tool content payloads into text."""
    content = result.get("content") if isinstance(result, dict) else None
    if isinstance(content, list):
        chunks: list[str] = []
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text" and item.get("text"):
                    chunks.append(str(item["text"]))
                elif item.get("text"):
                    chunks.append(str(item["text"]))
                elif item.get("data"):
                    chunks.append(str(item["data"]))
            elif item is not None:
                chunks.append(str(item))
        return "\n".join(chunks).strip()
    if isinstance(result, dict) and result.get("text"):
        return str(result["text"])
    return json.dumps(result, ensure_ascii=False)[:20000]


def parse_links_from_text(text: str, limit: int) -> list[dict[str, Any]]:
    """Parse URLs and markdown-style links from a browser snapshot."""
    results: list[dict[str, Any]] = []
    seen: set[str] = set()
    markdown_pattern = re.compile(r"\[([^\]]{2,160})\]\((https?://[^\s)]+)\)")
    for title, url in markdown_pattern.findall(text):
        clean_url = url.rstrip(".,)")
        if clean_url in seen:
            continue
        seen.add(clean_url)
        results.append({"title": title.strip(), "url": clean_url, "summary": "Extracted from Playwright MCP browser snapshot.", "score": round(1.0 - len(results) * 0.05, 2)})
        if len(results) >= limit:
            return results

    url_pattern = re.compile(r"https?://[^\s)\]}>\"']+")
    for url in url_pattern.findall(text):
        clean_url = url.rstrip(".,)")
        if clean_url in seen:
            continue
        seen.add(clean_url)
        results.append({"title": clean_url, "url": clean_url, "summary": "Extracted from Playwright MCP browser snapshot.", "score": round(1.0 - len(results) * 0.05, 2)})
        if len(results) >= limit:
            break
    return results

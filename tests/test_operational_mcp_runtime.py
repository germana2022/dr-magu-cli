from __future__ import annotations

from dr_magu.mcp_runtime.manager import MCPRuntimeManager
from dr_magu.mcp_runtime.registry import MCPServerRegistry
from dr_magu.research.runner import WebResearchRunner


def test_mcp_discover_persists_workspace_config(tmp_path):
    manager = MCPRuntimeManager(tmp_path)
    result = manager.discover()

    assert result.success
    assert (tmp_path / ".dr-magu" / "config" / "mcp_servers.json").exists()
    assert any(server["id"] == "brave-search" for server in result.data["servers"])


def test_mcp_enable_disable_updates_configuration(tmp_path):
    registry = MCPServerRegistry(tmp_path)
    registry.initialize_config()
    manager = MCPRuntimeManager(tmp_path)

    enabled = manager.enable("filesystem")
    assert enabled.success
    assert registry.find_by_id("filesystem").enabled is True

    disabled = manager.disable("filesystem")
    assert disabled.success
    assert registry.find_by_id("filesystem").enabled is False


def test_mcp_health_reports_missing_required_env(tmp_path, monkeypatch):
    registry = MCPServerRegistry(tmp_path)
    registry.initialize_config()
    registry.set_enabled("brave-search", True)
    monkeypatch.delenv("BRAVE_API_KEY", raising=False)

    result = MCPRuntimeManager(tmp_path).health("brave-search")

    assert result.success
    assert result.data["healthy"] is False
    assert "BRAVE_API_KEY" in result.data["missing_env"]


def test_research_provider_selection_returns_unavailable_for_explicit_disabled_provider(tmp_path):
    MCPServerRegistry(tmp_path).initialize_config()

    result = WebResearchRunner(tmp_path, provider_name="brave-search").search("operational mcp runtime", limit=2)

    assert result.success
    assert result.data["provider"] == "mcp-unavailable"
    assert result.data["fallback_used"] is False
    assert result.data["source_count"] == 0


def test_mcp_runtime_resolves_windows_cmd_shims(tmp_path, monkeypatch):
    manager = MCPRuntimeManager(tmp_path)
    monkeypatch.setattr("sys.platform", "win32")
    calls = []

    def fake_which(candidate: str):
        calls.append(candidate)
        if candidate == "npx.cmd":
            return r"C:\\Program Files\\nodejs\\npx.cmd"
        return None

    monkeypatch.setattr("shutil.which", fake_which)

    assert manager._resolve_command("npx") == r"C:\\Program Files\\nodejs\\npx.cmd"
    assert calls == ["npx", "npx.cmd"]


def test_mcp_start_returns_clear_error_when_command_is_missing(tmp_path):
    registry = MCPServerRegistry(tmp_path)
    registry.initialize_config()
    registry.set_enabled("playwright", True)
    servers = registry.list_servers()
    updated = []
    for server in servers:
        if server.id == "playwright":
            updated.append(server.__class__.from_dict({**server.to_dict(), "command": "definitely-not-a-real-command"}))
        else:
            updated.append(server)
    registry.save_servers(updated)

    result = MCPRuntimeManager(tmp_path).start("playwright")

    assert result.success is False
    assert "Command not found in PATH: definitely-not-a-real-command" in result.errors[0]
    assert result.data["server_id"] == "playwright"


def test_mcp_start_persists_process_state_and_status_uses_tracked_process(tmp_path, monkeypatch):
    registry = MCPServerRegistry(tmp_path)
    registry.initialize_config()
    registry.set_enabled("playwright", True)

    class FakeStdin:
        def close(self):
            pass

    class FakeProcess:
        pid = 4242
        stdin = FakeStdin()

        def poll(self):
            return None

        def terminate(self):
            pass

        def wait(self, timeout=None):
            return 0

        def kill(self):
            pass

    monkeypatch.setattr("dr_magu.mcp_runtime.manager.MCPRuntimeManager._resolve_command", lambda self, command: "/usr/bin/npx")
    monkeypatch.setattr("dr_magu.mcp_runtime.manager.subprocess.Popen", lambda *args, **kwargs: FakeProcess())

    manager = MCPRuntimeManager(tmp_path)
    started = manager.start("playwright")
    assert started.success is True
    assert started.data["pid"] == 4242
    assert (tmp_path / ".dr-magu" / "mcp_runtime" / "processes.json").exists()

    status = MCPRuntimeManager(tmp_path).status("playwright")
    assert status.success is True
    assert status.data["running"] is True
    assert status.data["pid"] == 4242
    assert "state_path" in status.data
    assert "stderr_path" in status.data

    stopped = manager.stop("playwright")
    assert stopped.success is True


def test_mcp_start_reports_immediate_process_exit(tmp_path, monkeypatch):
    registry = MCPServerRegistry(tmp_path)
    registry.initialize_config()
    registry.set_enabled("playwright", True)

    class FakeProcess:
        pid = 5151
        stdin = None

        def poll(self):
            return 1

    monkeypatch.setattr("dr_magu.mcp_runtime.manager.MCPRuntimeManager._resolve_command", lambda self, command: "/usr/bin/npx")
    monkeypatch.setattr("dr_magu.mcp_runtime.manager.subprocess.Popen", lambda *args, **kwargs: FakeProcess())

    result = MCPRuntimeManager(tmp_path).start("playwright")

    assert result.success is False
    assert result.data["status"] == "exited"
    assert result.data["exit_code"] == 1

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


def test_research_provider_selection_uses_fallback_when_disabled(tmp_path):
    MCPServerRegistry(tmp_path).initialize_config()

    result = WebResearchRunner(tmp_path, provider_name="brave-search").search("operational mcp runtime", limit=2)

    assert result.success
    assert result.data["provider"] == "fallback-deterministic"
    assert result.data["fallback_used"] is True
    assert result.data["source_count"] == 2

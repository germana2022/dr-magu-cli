from pathlib import Path

from typer.testing import CliRunner

from dr_magu.cli import app
from dr_magu.commands.context import CommandContext
from dr_magu.commands.processor import CommandProcessor
from dr_magu.commands.registry import registry
from dr_magu.mcp_runtime.client import MCPClient
from dr_magu.mcp_runtime.models import MCPServerConfig
from dr_magu.mcp_runtime.registry import MCPServerRegistry
from dr_magu.plugins.registry import PluginRegistry
from dr_magu.research.mcp_provider import MCPResearchProvider
from dr_magu.research.runner import WebResearchRunner


def test_mcp_registry_returns_default_server(tmp_path: Path):
    data = MCPServerRegistry(tmp_path).to_dict()

    assert data["count"] >= 1
    assert "servers" in data


def test_mcp_client_simulates_web_search(tmp_path: Path):
    server = MCPServerConfig(id="web-search", name="Web Search", enabled=True, capabilities=["web_search"])

    result = MCPClient(tmp_path, simulation_enabled=True).call_tool(server, "web.search", {"query": "CRM systems", "limit": 3})

    assert result.success is True
    assert result.simulated is True
    assert result.data["count"] == 3


def test_mcp_research_provider_uses_simulated_mcp_when_server_enabled(tmp_path: Path):
    config_dir = tmp_path / ".dr-magu" / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "mcp_servers.json").write_text(
        '{"servers":[{"id":"web-search","name":"Web Search","enabled":true,"capabilities":["web_search"]}]}',
        encoding="utf-8",
    )

    result = MCPResearchProvider(tmp_path, simulation_enabled=True).search("CRM systems", limit=2)

    assert result.provider == "mcp-simulated"
    assert len(result.sources) == 2
    assert result.sources[0].url.startswith("mcp://web-search")


def test_web_research_runner_defaults_to_mcp_provider(tmp_path: Path):
    config_dir = tmp_path / ".dr-magu" / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "mcp_servers.json").write_text(
        '{"servers":[{"id":"web-search","name":"Web Search","enabled":true,"capabilities":["web_search"]}]}',
        encoding="utf-8",
    )

    result = WebResearchRunner(tmp_path, simulation_enabled=True).search("CRM systems", limit=2)

    assert result.success is True
    assert result.data["provider"] == "mcp-simulated"
    assert result.data["source_count"] == 2


def test_command_processor_routes_mcp_servers(tmp_path: Path):
    context = CommandContext(workspace_path=str(tmp_path), output_format="human", config={})

    result = CommandProcessor(registry).execute_line("mcp.servers", context)

    assert result.success is True
    assert result.tool == "mcp.servers"


def test_command_processor_routes_mcp_call(tmp_path: Path, monkeypatch):
    config_dir = tmp_path / ".dr-magu" / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "mcp_servers.json").write_text(
        '{"servers":[{"id":"web-search","name":"Web Search","enabled":true,"capabilities":["web_search"]}]}',
        encoding="utf-8",
    )
    context = CommandContext(workspace_path=str(tmp_path), output_format="human", config={})

    class FakeResponse:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self):
            return b'<a class="result__a" href="https://example.org/crm">CRM</a><div class="result__snippet">CRM summary</div>'

    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: FakeResponse())

    result = CommandProcessor(registry).execute_line("mcp.call CRM systems --limit 2", context)

    assert result.success is True
    assert result.data["data"]["count"] == 1
    assert result.data["simulated"] is False


def test_cli_exposes_mcp_servers_command():
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "mcp-servers" in result.output


def test_mcp_research_runtime_plugin_is_discovered():
    plugins = PluginRegistry(".").list()
    assert any(plugin.id == "mcp-research-runtime" for plugin in plugins)


def test_mcp_enable_dot_syntax_persists_config(tmp_path: Path):
    context = CommandContext(workspace_path=str(tmp_path))

    result = CommandProcessor(registry).execute_line("mcp.enable playwright", context)

    assert result.success is True
    assert result.tool == "mcp.enable"
    assert result.data["id"] == "playwright"
    assert result.data["enabled"] is True
    assert (tmp_path / ".dr-magu" / "config" / "mcp_servers.json").exists()


def test_mcp_enable_space_syntax_is_command_first(tmp_path: Path):
    context = CommandContext(workspace_path=str(tmp_path))

    result = CommandProcessor(registry).execute_line("mcp enable playwright", context)

    assert result.success is True
    assert result.tool == "mcp.enable"
    assert result.data["id"] == "playwright"
    assert result.data["enabled"] is True


def test_operational_enable_disable_space_syntax_normalization():
    assert CommandProcessor.parse_line("mcp enable playwright")["command_name"] == "mcp.enable"
    assert CommandProcessor.parse_line("mcp disable playwright")["command_name"] == "mcp.disable"
    assert CommandProcessor.parse_line("agent enable repository-analyzer")["command_name"] == "agent.enable"
    assert CommandProcessor.parse_line("agent disable repository-analyzer")["command_name"] == "agent.disable"
    assert CommandProcessor.parse_line("schedule enable task-1")["command_name"] == "schedule.enable"
    assert CommandProcessor.parse_line("schedule disable task-1")["command_name"] == "schedule.disable"


def test_mcp_research_provider_real_filesystem_provider_by_default(tmp_path: Path):
    (tmp_path / "README.md").write_text("hello", encoding="utf-8")
    config_dir = tmp_path / ".dr-magu" / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "mcp_servers.json").write_text(
        '{"servers":[{"id":"filesystem","name":"Filesystem MCP","enabled":true,"capabilities":["filesystem","research"]}]}',
        encoding="utf-8",
    )

    result = MCPResearchProvider(tmp_path, provider_name="filesystem").search(".", limit=2)

    assert result.provider == "filesystem"
    assert result.fallback_used is False
    assert "README.md" in result.sources[0].summary or result.sources[0].url


def test_mcp_research_provider_simulation_is_explicit(tmp_path: Path):
    config_dir = tmp_path / ".dr-magu" / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "mcp_servers.json").write_text(
        '{"servers":[{"id":"web-search","name":"Web Search","enabled":true,"capabilities":["web_search"]}]}',
        encoding="utf-8",
    )

    result = MCPResearchProvider(tmp_path, simulation_enabled=True).search("CRM systems", limit=2)

    assert result.provider == "mcp-simulated"
    assert len(result.sources) == 2


def test_playwright_provider_parses_real_web_results_without_simulation(tmp_path: Path, monkeypatch):
    config_dir = tmp_path / ".dr-magu" / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "mcp_servers.json").write_text(
        '{"servers":[{"id":"playwright","name":"Playwright MCP","enabled":true,"capabilities":["web_search","browser"]}]}',
        encoding="utf-8",
    )

    class FakeResponse:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self):
            return b'<a class="result__a" href="https://example.org/ai">AI News</a><div class="result__snippet">Live AI summary</div>'

    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: FakeResponse())

    result = MCPResearchProvider(tmp_path, provider_name="playwright").search("AI news", limit=1)

    assert result.provider == "playwright"
    assert result.fallback_used is False
    assert result.sources[0].url == "https://example.org/ai"
    assert "Live AI" in result.sources[0].summary


def test_research_debug_persists_latest_debug_and_exposes_fallback_reason(tmp_path: Path):
    config_dir = tmp_path / ".dr-magu" / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "mcp_servers.json").write_text(
        '{"servers":[{"id":"playwright","name":"Playwright MCP","enabled":true,"capabilities":["web_search","browser"]}]}',
        encoding="utf-8",
    )

    result = WebResearchRunner(tmp_path, provider_name="playwright", debug_enabled=True).search("AI news", limit=1, debug=True)

    assert result.success is True
    assert "debug" in result.data
    assert result.data["mcp_client_attempted"] is True
    assert result.data["debug_path"]
    assert (tmp_path / ".dr-magu" / "research" / "debug" / "latest-debug.json").exists()


def test_command_processor_research_passes_provider_and_debug(tmp_path: Path):
    (tmp_path / "README.md").write_text("hello", encoding="utf-8")
    config_dir = tmp_path / ".dr-magu" / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "mcp_servers.json").write_text(
        '{"servers":[{"id":"filesystem","name":"Filesystem MCP","enabled":true,"capabilities":["filesystem","research"]}]}',
        encoding="utf-8",
    )
    context = CommandContext(workspace_path=str(tmp_path), output_format="human", config={})

    result = CommandProcessor(registry).execute_line("research . --provider filesystem --debug", context)

    assert result.success is True
    assert result.data["provider"] == "filesystem"
    assert "debug" in result.data


def test_mcp_debug_space_syntax_is_command_first(tmp_path: Path):
    context = CommandContext(workspace_path=str(tmp_path), output_format="human", config={})

    result = CommandProcessor(registry).execute_line("mcp debug playwright", context)

    assert result.tool == "mcp.debug"


def test_stdio_mcp_debug_flags_are_exposed(tmp_path: Path, monkeypatch):
    from dr_magu.mcp_runtime.models import MCPToolResult

    config_dir = tmp_path / ".dr-magu" / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "mcp_servers.json").write_text(
        '{"servers":[{"id":"playwright","name":"Playwright MCP","enabled":true,"transport":"stdio","command":"npx","args":["-y","@playwright/mcp"],"capabilities":["web_search","browser"]}]}',
        encoding="utf-8",
    )

    def fake_call_tool(self, server, tool_name, arguments):
        return MCPToolResult(
            True,
            server.id,
            tool_name,
            data={"query": arguments["query"], "results": [{"title": "AI", "url": "https://example.org/ai", "summary": "MCP result", "score": 1.0}], "count": 1},
            debug={
                "mcp_client_attempted": True,
                "mcp_client_connected": True,
                "mcp_stdio_session_attempted": True,
                "mcp_tool_called": "browser_navigate",
            },
        )

    monkeypatch.setattr("dr_magu.mcp_runtime.client.MCPClient.call_tool", fake_call_tool)
    result = MCPResearchProvider(tmp_path, provider_name="playwright", debug_enabled=True).search("AI news", limit=1)

    assert result.provider == "playwright"
    assert result.debug["debug_version"] == "2.4.0"
    assert result.debug["mcp_client_connected"] is True
    assert result.debug["mcp_stdio_session_attempted"] is True


def test_parse_links_from_stdio_snapshot_text():
    from dr_magu.mcp_runtime.stdio_client import parse_links_from_text

    text = "Result [OpenAI News](https://openai.com/news) and https://example.org/ai"
    results = parse_links_from_text(text, 2)

    assert results[0]["title"] == "OpenAI News"
    assert results[0]["url"] == "https://openai.com/news"



def test_mcp_handshake_command_uses_direct_client(tmp_path: Path, monkeypatch):
    from dr_magu.mcp_runtime.models import MCPToolResult

    config_dir = tmp_path / ".dr-magu" / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "mcp_servers.json").write_text(
        '{"servers":[{"id":"playwright","name":"Playwright MCP","enabled":true,"transport":"stdio","command":"npx","args":["-y","@playwright/mcp"],"capabilities":["web_search","browser"]}]}',
        encoding="utf-8",
    )

    def fake_handshake(self, server):
        return MCPToolResult(True, server.id, "mcp.handshake", data={"initialized": True}, debug={"mcp_client_connected": True})

    monkeypatch.setattr("dr_magu.mcp_runtime.client.MCPClient.handshake", fake_handshake)
    context = CommandContext(workspace_path=str(tmp_path), output_format="human", config={})

    result = CommandProcessor(registry).execute_line("mcp.handshake playwright", context)

    assert result.success is True
    assert result.tool == "mcp.handshake"
    assert result.data["data"]["initialized"] is True


def test_mcp_test_command_uses_target_argument(tmp_path: Path, monkeypatch):
    from dr_magu.mcp_runtime.models import MCPToolResult

    config_dir = tmp_path / ".dr-magu" / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "mcp_servers.json").write_text(
        '{"servers":[{"id":"playwright","name":"Playwright MCP","enabled":true,"transport":"stdio","command":"npx","args":["-y","@playwright/mcp"],"capabilities":["web_search","browser"]}]}',
        encoding="utf-8",
    )

    seen = {}
    def fake_test_server(self, server, target="https://www.google.com"):
        seen["target"] = target
        return MCPToolResult(True, server.id, "mcp.test", data={"test_target": target, "validation": "playwright_navigate_snapshot"}, debug={"mcp_client_connected": True})

    monkeypatch.setattr("dr_magu.mcp_runtime.client.MCPClient.test_server", fake_test_server)
    context = CommandContext(workspace_path=str(tmp_path), output_format="human", config={})

    result = CommandProcessor(registry).execute_line("mcp.test playwright www.google.com", context)

    assert result.success is True
    assert result.tool == "mcp.test"
    assert seen["target"] == "www.google.com"
    assert result.data["data"]["validation"] == "playwright_navigate_snapshot"


def test_playwright_research_uses_concrete_mcp_tool_mapping(tmp_path: Path, monkeypatch):
    from dr_magu.mcp_runtime.models import MCPToolResult

    config_dir = tmp_path / ".dr-magu" / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "mcp_servers.json").write_text(
        '{"servers":[{"id":"playwright","name":"Playwright MCP","enabled":true,"transport":"stdio","command":"npx","args":["-y","@playwright/mcp"],"capabilities":["web_search","browser"]}]}',
        encoding="utf-8",
    )

    seen = {}
    def fake_call_tool(self, server, tool_name, arguments):
        seen["tool_name"] = tool_name
        return MCPToolResult(
            True,
            server.id,
            "browser_navigate",
            data={
                "query": arguments["query"],
                "results": [{"title": "AI News", "url": "https://example.org/ai", "summary": "Real MCP result", "score": 1.0}],
                "count": 1,
                "primary_tool": "browser_navigate",
                "tool_sequence": ["browser_navigate", "browser_snapshot"],
            },
            debug={
                "mcp_client_attempted": True,
                "mcp_client_connected": True,
                "mcp_stdio_session_attempted": True,
                "mcp_tool_called": "browser_navigate",
                "mcp_snapshot_tool_called": "browser_snapshot",
                "mcp_tool_invocation_success": True,
                "mcp_tool_response_received": True,
            },
        )

    monkeypatch.setattr("dr_magu.mcp_runtime.client.MCPClient.call_tool", fake_call_tool)
    result = MCPResearchProvider(tmp_path, provider_name="playwright", debug_enabled=True).search("AI news", limit=1)

    assert seen["tool_name"] == "browser_navigate"
    assert result.provider == "playwright"
    assert result.debug["mcp_tool_called"] == "browser_navigate"
    assert result.debug["mcp_snapshot_tool_called"] == "browser_snapshot"
    assert result.debug["mcp_tool_invocation_success"] is True
    assert result.sources[0].url == "https://example.org/ai"


def test_multi_provider_research_aggregates_and_deduplicates_sources(tmp_path: Path, monkeypatch):
    from dr_magu.mcp_runtime.models import MCPToolResult

    config_dir = tmp_path / ".dr-magu" / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "mcp_servers.json").write_text(
        '{"servers":['
        '{"id":"playwright","name":"Playwright MCP","enabled":true,"transport":"stdio","command":"npx","args":["-y","@playwright/mcp"],"capabilities":["web_search","browser"]},'
        '{"id":"filesystem","name":"Filesystem MCP","enabled":true,"transport":"stdio","command":"npx","args":["-y","@modelcontextprotocol/server-filesystem","."],"capabilities":["filesystem","research"]}'
        ']}',
        encoding="utf-8",
    )

    def fake_call_tool(self, server, tool_name, arguments):
        if server.id == "playwright":
            return MCPToolResult(
                True,
                server.id,
                tool_name,
                data={"results": [
                    {"title": "AI News", "url": "https://example.org/ai", "summary": "Playwright result", "score": 1.0},
                    {"title": "Duplicate", "url": "https://example.org/shared", "summary": "Shared result", "score": 0.8},
                ]},
                debug={"mcp_client_connected": True, "mcp_stdio_session_attempted": True, "mcp_tool_invocation_success": True},
            )
        return MCPToolResult(
            True,
            server.id,
            tool_name,
            data={"results": [
                {"title": "Duplicate from Filesystem", "url": "https://example.org/shared", "summary": "Duplicate should be removed", "score": 1.0},
                {"title": "Local Architecture", "url": "mcp://filesystem/result", "summary": "Filesystem result", "score": 0.9},
            ]},
            debug={"mcp_client_connected": True, "mcp_stdio_session_attempted": False},
        )

    monkeypatch.setattr("dr_magu.mcp_runtime.client.MCPClient.call_tool", fake_call_tool)

    result = MCPResearchProvider(tmp_path, provider_name="multi", debug_enabled=True).search("AI news", limit=5)

    assert result.provider == "multi-provider"
    assert result.fallback_used is False
    assert result.provider_chain == ["playwright", "filesystem"]
    assert result.debug["providers_successful"] == ["playwright", "filesystem"]
    assert result.debug["deduplication_enabled"] is True
    assert [source.url for source in result.sources].count("https://example.org/shared") == 1
    assert len(result.sources) == 3


def test_auto_provider_uses_deterministic_fallback_only_when_all_providers_fail(tmp_path: Path, monkeypatch):
    from dr_magu.mcp_runtime.models import MCPToolResult

    config_dir = tmp_path / ".dr-magu" / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "mcp_servers.json").write_text(
        '{"servers":[{"id":"playwright","name":"Playwright MCP","enabled":true,"capabilities":["web_search","browser"]}]}',
        encoding="utf-8",
    )

    def fake_call_tool(self, server, tool_name, arguments):
        return MCPToolResult(False, server.id, tool_name, error="provider unavailable", debug={"mcp_client_attempted": True})

    monkeypatch.setattr("dr_magu.mcp_runtime.client.MCPClient.call_tool", fake_call_tool)

    result = MCPResearchProvider(tmp_path, provider_name="auto", debug_enabled=True).search("AI news", limit=2)

    assert result.provider == "fallback-deterministic"
    assert result.fallback_used is True
    assert result.provider_chain == ["playwright", "fallback-deterministic"]
    assert result.debug["fallback_reason"] == "provider unavailable"

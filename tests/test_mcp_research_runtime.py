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

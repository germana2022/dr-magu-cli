from pathlib import Path

from typer.testing import CliRunner

from dr_magu.cli import app
from dr_magu.commands.context import CommandContext
from dr_magu.commands.processor import CommandProcessor
from dr_magu.commands.registry import registry
from dr_magu.mcp_integrations.runtime import MCPIntegrationRuntime
from dr_magu.mcp_runtime.registry import MCPServerRegistry
from dr_magu.plugins.registry import PluginRegistry


def _write_enabled_servers(tmp_path: Path) -> None:
    config_dir = tmp_path / ".dr-magu" / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "mcp_servers.json").write_text(
        """
{
  "servers": [
    {"id":"playwright","name":"Playwright MCP","enabled":true,"capabilities":["website_analysis","web_search"]},
    {"id":"github","name":"GitHub MCP","enabled":true,"capabilities":["repository"]},
    {"id":"filesystem","name":"Filesystem MCP","enabled":true,"capabilities":["filesystem"]},
    {"id":"brave-search","name":"Brave Search MCP","enabled":true,"capabilities":["web_search","research"]}
  ]
}
""".strip(),
        encoding="utf-8",
    )


def _mock_html(monkeypatch) -> None:
    class FakeResponse:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self):
            return b"<html><title>Example</title><h1>Example Domain</h1></html>"

    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: FakeResponse())


def _mock_github(monkeypatch) -> None:
    class FakeResponse:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self):
            return b'{"full_name":"owner/repo","html_url":"https://github.com/owner/repo","description":"Repo summary","default_branch":"main","language":"Python","stargazers_count":1,"topics":["ai"]}'

    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: FakeResponse())


def test_registry_lists_real_mcp_templates(tmp_path: Path):
    servers = MCPServerRegistry(tmp_path).list_servers()
    ids = {server.id for server in servers}

    assert {"playwright", "brave-search", "github", "filesystem"}.issubset(ids)


def test_website_analyze_uses_playwright_capability(tmp_path: Path, monkeypatch):
    _mock_html(monkeypatch)
    _write_enabled_servers(tmp_path)

    result = MCPIntegrationRuntime(tmp_path).website_analyze("https://example.com")

    assert result.success is True
    assert result.tool == "website.analyze"
    assert result.data["server_id"] == "playwright"
    assert result.data["simulated"] is False
    assert result.data["data"]["results"][0]["url"] == "https://example.com"


def test_repository_read_uses_github_capability(tmp_path: Path, monkeypatch):
    _mock_github(monkeypatch)
    _write_enabled_servers(tmp_path)

    result = MCPIntegrationRuntime(tmp_path).repository_read("owner/repo")

    assert result.success is True
    assert result.data["server_id"] == "github"
    assert result.data["data"]["repository"] == "owner/repo"


def test_filesystem_search_uses_filesystem_capability(tmp_path: Path):
    _write_enabled_servers(tmp_path)

    result = MCPIntegrationRuntime(tmp_path).filesystem_search("src")

    assert result.success is True
    assert result.data["server_id"] == "filesystem"


def test_command_processor_routes_website_analyze(tmp_path: Path, monkeypatch):
    _mock_html(monkeypatch)
    _write_enabled_servers(tmp_path)
    context = CommandContext(workspace_path=str(tmp_path), output_format="human", config={})

    result = CommandProcessor(registry).execute_line("website.analyze https://example.com", context)

    assert result.success is True
    assert result.tool == "website.analyze"


def test_command_processor_routes_repository_read(tmp_path: Path, monkeypatch):
    _mock_github(monkeypatch)
    _write_enabled_servers(tmp_path)
    context = CommandContext(workspace_path=str(tmp_path), output_format="human", config={})

    result = CommandProcessor(registry).execute_line("repository.read owner/repo", context)

    assert result.success is True
    assert result.tool == "repository.read"


def test_cli_exposes_real_mcp_commands():
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "website-analyze" in result.output
    assert "repository-read" in result.output


def test_real_mcp_integrations_plugin_is_discovered():
    plugins = PluginRegistry(".").list()
    assert any(plugin.id == "real-mcp-integrations" for plugin in plugins)

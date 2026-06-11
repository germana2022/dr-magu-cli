from pathlib import Path

from typer.testing import CliRunner

from dr_magu.cli import app
from dr_magu.commands.context import CommandContext
from dr_magu.commands.processor import CommandProcessor
from dr_magu.commands.registry import registry
from dr_magu.conversational_router.router import route_prompt
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


def _mock_urlopen(monkeypatch) -> None:
    class FakeResponse:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self):
            return b"<html><title>HubSpot</title><h1>CRM Platform</h1></html>"

    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: FakeResponse())


def test_router_maps_website_prompt_to_website_analyze():
    route = route_prompt("Analyze hubspot.com and summarize its business model")

    assert route.intent == "website_analysis"
    assert route.command == 'website.analyze "https://hubspot.com"'
    assert route.confidence >= 0.9


def test_router_maps_github_prompt_to_repository_read():
    route = route_prompt("Analyze repository https://github.com/microsoft/vscode")

    assert route.intent == "repository_analysis"
    assert route.command == 'repository.read "microsoft/vscode"'


def test_router_maps_research_prompt_to_research_search():
    route = route_prompt("Research the top 10 CRM systems for small businesses")

    assert route.intent == "research"
    assert route.command.startswith("research.search")


def test_router_maps_file_search_prompt_to_filesystem_search():
    route = route_prompt("Find files in src")

    assert route.intent == "filesystem_search"
    assert route.command.startswith("filesystem.search")


def test_router_route_command_returns_command(tmp_path: Path):
    context = CommandContext(workspace_path=str(tmp_path), output_format="human", config={})
    result = CommandProcessor(registry).execute_line("router.route Analyze hubspot.com", context)

    assert result.success is True
    assert result.data["command"] == 'website.analyze "https://hubspot.com"'


def test_router_execute_runs_resolved_website_command(tmp_path: Path, monkeypatch):
    _mock_urlopen(monkeypatch)
    _write_enabled_servers(tmp_path)
    context = CommandContext(workspace_path=str(tmp_path), output_format="human", config={})

    result = CommandProcessor(registry).execute_line("router.execute Analyze hubspot.com", context)

    assert result.success is True
    assert result.data["routing"]["intent"] == "website_analysis"
    assert result.data["result"]["tool"] == "website.analyze"


def test_brain_ask_uses_conversational_command_router_for_website(tmp_path: Path, monkeypatch):
    _mock_urlopen(monkeypatch)
    _write_enabled_servers(tmp_path)
    context = CommandContext(workspace_path=str(tmp_path), output_format="human", config={})

    result = CommandProcessor(registry).execute_line("brain.ask Analyze hubspot.com", context)

    assert result.success is True
    assert result.data["routing"]["intent"] == "website_analysis"
    assert result.data["route_result"]["tool"] == "website.analyze"


def test_cli_exposes_route_commands():
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "route" in result.output
    assert "route-execute" in result.output


def test_cli_route_command_outputs_resolved_command():
    result = CliRunner().invoke(app, ["route", "Analyze hubspot.com"])

    assert result.exit_code == 0
    assert "website.analyze" in result.output


def test_conversational_command_router_plugin_is_discovered():
    plugins = PluginRegistry(".").list()

    assert any(plugin.id == "conversational-command-router" for plugin in plugins)

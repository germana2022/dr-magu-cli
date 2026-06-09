from pathlib import Path

from dr_magu.commands.context import CommandContext
from dr_magu.commands.processor import CommandProcessor
from dr_magu.commands.registry import registry
from dr_magu.plugins.registry import PluginRegistry
from dr_magu.research.provider import DeterministicResearchProvider
from dr_magu.research.runner import WebResearchRunner


def test_deterministic_research_provider_returns_sources():
    result = DeterministicResearchProvider().search("AI developer tools", limit=5)

    assert result.topic == "AI developer tools"
    assert len(result.sources) == 5
    assert result.sources[0].title


def test_web_research_runner_persists_latest_research(tmp_path: Path):
    result = WebResearchRunner(tmp_path).search("LangGraph", limit=3)

    assert result.success is True
    assert result.data["source_count"] == 3
    assert (tmp_path / ".dr-magu" / "research" / "latest-research.json").exists()


def test_command_processor_routes_research_search(tmp_path: Path):
    context = CommandContext(workspace_path=str(tmp_path), output_format="human", config={})
    result = CommandProcessor(registry).execute_line("research.search LangGraph", context)

    assert result.success is True
    assert result.data["topic"] == "LangGraph"


def test_research_plugin_is_discovered():
    plugins = PluginRegistry(".").list()
    assert any(plugin.id == "research" for plugin in plugins)

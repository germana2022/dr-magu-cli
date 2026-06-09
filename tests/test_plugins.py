from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from dr_magu.cli import app
from dr_magu.plugins.manager import PluginManager
from dr_magu.plugins.registry import PluginRegistry
from dr_magu.agents.registry import AgentRegistry
from dr_magu.brain.context_loader import BrainContextLoader


def create_plugin(workspace: Path) -> None:
    plugin_dir = workspace / ".dr-magu" / "plugins" / "research"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "plugin.yaml").write_text(
        """
id: research
name: Research
version: 0.1.0
enabled: true
domain: research
description: Research agents and workflows.

provides:
  agents:
    - web-researcher
  workflows:
    - research.web
  tools:
    - web.search
permissions:
  external_network: restricted
""".strip(),
        encoding="utf-8",
    )
    (plugin_dir / "agents.yaml").write_text(
        """
agents:
  web-researcher:
    name: Web Researcher
    description: Search and summarize web content.
    role: research
    workflow: repository.context
    enabled: true
    requires_llm: true
    capabilities:
      - search_web
      - summarize_content
""".strip(),
        encoding="utf-8",
    )


def test_plugin_registry_discovers_workspace_plugins(tmp_path: Path) -> None:
    create_plugin(tmp_path)

    registry = PluginRegistry(tmp_path)
    plugins = registry.list()

    assert [plugin.id for plugin in plugins] == ["approval", "autonomous-execution-loop", "background-worker", "conversational-brain", "conversational-command-router", "execution-runtime", "llm-runtime", "mcp-research-runtime", "multi-agent-orchestrator", "platform-stabilization", "real-mcp-integrations", "reporting", "research", "scheduler", "software-dev", "software-development", "website-builder", "workflow-engine"]
    assert next(plugin for plugin in plugins if plugin.id == "research").provides.agents == ["web-researcher"]


def test_plugin_manager_validates_plugins(tmp_path: Path) -> None:
    create_plugin(tmp_path)

    result = PluginManager(tmp_path).validate_plugin("research")

    assert result.success is True
    assert result.data["valid"] is True


def test_agent_registry_loads_agents_from_enabled_plugins(tmp_path: Path) -> None:
    create_plugin(tmp_path)

    agents = AgentRegistry(tmp_path).list()

    assert any(agent.id == "web-researcher" for agent in agents)
    agent = AgentRegistry(tmp_path).get("web-researcher")
    assert agent.plugin_id == "research"


def test_brain_context_includes_plugins(tmp_path: Path) -> None:
    create_plugin(tmp_path)

    snapshot = BrainContextLoader(tmp_path).load()

    assert snapshot.summary["plugin_count"] == 18
    assert any(plugin["id"] == "research" for plugin in snapshot.plugins)
    assert any(agent["id"] == "web-researcher" for agent in snapshot.agents)


def test_plugin_cli_list(tmp_path: Path) -> None:
    create_plugin(tmp_path)
    runner = CliRunner()

    result = runner.invoke(app, ["plugin", "list", "--workspace", str(tmp_path)])

    assert result.exit_code == 0
    assert "research" in result.output

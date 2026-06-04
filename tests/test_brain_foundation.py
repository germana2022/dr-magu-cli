from __future__ import annotations

from dr_magu.agents.registry import AgentRegistry
from dr_magu.agents.runner import AgentRunner
from dr_magu.brain.context_loader import BrainContextLoader
from dr_magu.brain.model_config import ModelConfigLoader, ModelResolver
from dr_magu.commands.context import CommandContext
from dr_magu.commands.processor import CommandProcessor
from dr_magu.commands.registry import registry
from dr_magu.security.permission_context import PermissionContextReader
from dr_magu.tools.registry import ToolRegistry


def test_default_model_uses_environment_fallback(monkeypatch, tmp_path):
    monkeypatch.setenv("LLM_PROVIDER", "opencode")
    monkeypatch.setenv("LLM_BASE_URL", "https://opencode.ai/zen/go/v1")
    monkeypatch.setenv("LLM_MODEL", "deepseek-v4-flash")
    monkeypatch.setenv("LLM_TEMPERATURE", "0.1")
    monkeypatch.setenv("LLM_API_KEY", "test-key")

    model = ModelConfigLoader(tmp_path).default_model()

    assert model.provider == "opencode"
    assert model.base_url == "https://opencode.ai/zen/go/v1"
    assert model.model == "deepseek-v4-flash"
    assert model.temperature == 0.1
    assert model.api_key_configured is True


def test_model_resolver_uses_agent_overrides():
    default_model = ModelConfigLoader(".").default_model()
    resolved = ModelResolver(default_model).resolve({"model": "custom-model", "temperature": 0.0})

    assert resolved.provider == default_model.provider
    assert resolved.model == "custom-model"
    assert resolved.temperature == 0.0
    assert resolved.source == "agent override"


def test_agent_registry_loads_repository_analyzer():
    agents = AgentRegistry(".").list()

    assert any(agent.id == "repository-analyzer" for agent in agents)
    repository_analyzer = AgentRegistry(".").get("repository-analyzer")
    assert repository_analyzer.workflow == "repository.context"
    assert repository_analyzer.model.model


def test_tool_registry_lists_formal_tools():
    tools = ToolRegistry().list_tools()
    names = {tool.name for tool in tools}

    assert "files.read" in names
    assert "workflow.run" in names
    assert "brain.context" in names


def test_permission_context_reader_reads_config():
    permissions = PermissionContextReader({
        "permissions": {"file_read": True, "shell_run": True},
        "blocked_shell_patterns": ["rm -rf"],
    }).read()

    assert permissions.file_read is True
    assert permissions.shell_run is True
    assert "rm -rf" in permissions.blocked_shell_patterns


def test_brain_context_loader_includes_runtime_inventory(tmp_path):
    snapshot = BrainContextLoader(tmp_path).load()

    assert snapshot.summary["brain_ready"] is True
    assert snapshot.summary["command_count"] > 0
    assert snapshot.summary["tool_count"] > 0
    assert snapshot.summary["agent_count"] >= 1
    assert snapshot.default_model["model"]


def test_command_processor_supports_brain_and_agent_commands(tmp_path):
    context = CommandContext(workspace_path=str(tmp_path), output_format="human", config={})
    processor = CommandProcessor(registry)

    brain_result = processor.execute_line("brain.context", context)
    agent_result = processor.execute_line("agent.list", context)
    tools_result = processor.execute_line("tools.list", context)
    permissions_result = processor.execute_line("permissions.show", context)

    assert brain_result.success is True
    assert agent_result.success is True
    assert tools_result.success is True
    assert permissions_result.success is True


def test_agent_runner_delegates_to_workflow(tmp_path):
    (tmp_path / "README.md").write_text("# Test Project\n", encoding="utf-8")
    result = AgentRunner(tmp_path).run_agent("repository-analyzer")

    assert result.success is True
    assert result.data["agent"]["id"] == "repository-analyzer"
    assert result.data["workflow_success"] is True

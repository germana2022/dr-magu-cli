from pathlib import Path

from typer.testing import CliRunner

from dr_magu.brain.conversation import ConversationalBrain
from dr_magu.brain.models import ResolvedModelConfig
from dr_magu.cli import app
from dr_magu.commands.context import CommandContext
from dr_magu.commands.processor import CommandProcessor
from dr_magu.commands.registry import registry
from dr_magu.llm_runtime.models import LLMMessage, LLMResponse
from dr_magu.llm_runtime.openai_compatible import OpenAICompatibleProvider
from dr_magu.llm_runtime.runtime import LLMRuntime
from dr_magu.plugins.registry import PluginRegistry


class FakeProvider:
    def chat(self, model_config: ResolvedModelConfig, messages: list[LLMMessage], timeout_seconds: int = 60) -> LLMResponse:
        return LLMResponse(
            content=f"fake response to: {messages[-1].content}",
            provider=model_config.provider,
            model=model_config.model,
            raw={"fake": True},
        )


def test_llm_runtime_chat_uses_provider(tmp_path: Path):
    result = LLMRuntime(tmp_path, provider=FakeProvider()).chat("hello")

    assert result.success is True
    assert result.tool == "llm.chat"
    assert result.data["llm_used"] is True
    assert "raw" not in result.data["response"]
    assert "fake response" in result.data["response"]["content"]


def test_openai_compatible_provider_requires_api_key(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    config = ResolvedModelConfig(
        provider="opencode",
        base_url="https://example.com/v1",
        model="demo-model",
        temperature=0.1,
        api_key_env="LLM_API_KEY",
        api_key_configured=False,
        source="test",
    )

    response = OpenAICompatibleProvider().chat(config, [LLMMessage(role="user", content="hello")])

    assert response.success is False
    assert "Missing API key" in response.error


def test_command_processor_routes_llm_chat(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    context = CommandContext(workspace_path=str(tmp_path), output_format="human", config={})

    result = CommandProcessor(registry).execute_line('llm.chat "hello"', context)

    assert result.success is False
    assert result.tool == "llm.chat"
    assert "Missing API key" in result.errors[0]


def test_conversational_brain_general_chat_uses_llm_runtime_failure_path(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    result = ConversationalBrain(tmp_path).ask("hello")

    assert result.success is False
    assert result.tool == "brain.ask"
    assert result.data["llm_used"] is False
    assert "Missing API key" in result.errors[0]


def test_conversational_brain_research_route_does_not_call_llm(tmp_path: Path):
    result = ConversationalBrain(tmp_path).ask("What are the best CRM systems for small businesses?")

    assert result.success is True
    assert result.data["llm_used"] is False
    assert result.data["route_result"]["tool"] == "research.search"


def test_cli_exposes_llm_chat_command():
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "llm-chat" in result.output
    assert "tui" in result.output


def test_llm_runtime_plugin_is_discovered():
    plugins = PluginRegistry(".").list()
    assert any(plugin.id == "llm-runtime" for plugin in plugins)

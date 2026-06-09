from pathlib import Path

from typer.testing import CliRunner

from dr_magu.brain.conversation import ConversationalBrain
from dr_magu.brain.intent_models import INTENT_RESEARCH_ACTION
from dr_magu.brain.intent_router import classify_prompt
from dr_magu.cli import app
from dr_magu.commands.context import CommandContext
from dr_magu.commands.processor import CommandProcessor
from dr_magu.commands.registry import registry
from dr_magu.plugins.registry import PluginRegistry


def test_intent_router_classifies_best_crm_question_as_research():
    result = classify_prompt("What are the best CRM systems for small businesses?")

    assert result.intent == INTENT_RESEARCH_ACTION
    assert "crm" in result.matched_keywords or "best" in result.matched_keywords


def test_conversational_brain_routes_crm_question_to_research(tmp_path: Path):
    result = ConversationalBrain(tmp_path).ask("What are the best CRM systems for small businesses?")

    assert result.success is True
    assert result.data["classification"]["intent"] == INTENT_RESEARCH_ACTION
    assert result.data["routed_command"].startswith("research.search")
    assert result.data["route_result"]["tool"] == "research.search"
    assert result.data["llm_used"] is False
    assert "default_model" in result.data


def test_conversational_brain_general_chat_returns_model_context(tmp_path: Path):
    result = ConversationalBrain(tmp_path).ask("Hello there")

    assert result.success is True
    assert result.data["classification"]["intent"] == "general_chat"
    assert result.data["llm_used"] is False
    assert "default_model" in result.data


def test_command_processor_routes_brain_ask(tmp_path: Path):
    context = CommandContext(workspace_path=str(tmp_path), output_format="human", config={})
    result = CommandProcessor(registry).execute_line('brain.ask "What are the best CRM systems for small businesses?"', context)

    assert result.success is True
    assert result.tool == "brain.ask"
    assert result.data["route_result"]["tool"] == "research.search"


def test_command_processor_routes_ask_alias(tmp_path: Path):
    context = CommandContext(workspace_path=str(tmp_path), output_format="human", config={})
    result = CommandProcessor(registry).execute_line('ask "Research the top 10 CRM systems"', context)

    assert result.success is True
    assert result.data["classification"]["intent"] == INTENT_RESEARCH_ACTION


def test_cli_exposes_tui_command():
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "tui" in result.output


def test_cli_exposes_brain_ask_command():
    result = CliRunner().invoke(app, ["brain-ask", "What are the best CRM systems for small businesses?"])

    assert result.exit_code == 0
    assert "research.search" in result.output


def test_conversational_brain_plugin_is_discovered():
    plugins = PluginRegistry(".").list()
    assert any(plugin.id == "conversational-brain" for plugin in plugins)

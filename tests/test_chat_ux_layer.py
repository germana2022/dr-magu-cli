from typer.testing import CliRunner

from dr_magu.chat_ux.renderer import extract_chat_text, render_user_facing_result
from dr_magu.cli import app
from dr_magu.result import ToolResult


def test_extract_chat_text_from_brain_ask_response():
    result = ToolResult(
        success=True,
        tool="brain.ask",
        data={
            "response": "Hi! I'm Dr Magu.",
            "llm_response": {"content": "Hi! I'm Dr Magu.", "provider": "opencode"},
        },
    )

    assert extract_chat_text(result) == "Hi! I'm Dr Magu."


def test_render_user_facing_result_hides_metadata_by_default():
    result = ToolResult(
        success=True,
        tool="brain.ask",
        data={
            "classification": {"intent": "general_chat"},
            "default_model": {"model": "deepseek-v4-flash"},
            "response": "Hello cleanly.",
            "llm_response": {"content": "Hello cleanly.", "provider": "opencode"},
        },
    )

    rendered = render_user_facing_result(result)

    assert rendered == "Hello cleanly."


def test_render_user_facing_result_shows_debug_when_requested():
    result = ToolResult(
        success=True,
        tool="brain.ask",
        data={
            "classification": {"intent": "general_chat"},
            "response": "Hello cleanly.",
        },
    )

    rendered = render_user_facing_result(result, debug=True)

    assert isinstance(rendered, dict)
    assert rendered["classification"]["intent"] == "general_chat"


def test_extract_chat_text_from_llm_chat_response():
    result = ToolResult(
        success=True,
        tool="llm.chat",
        data={"response": {"content": "LLM says hello.", "model": "demo"}},
    )

    assert extract_chat_text(result) == "LLM says hello."


def test_cli_exposes_brain_ask_debug_option():
    result = CliRunner().invoke(app, ["brain-ask", "--help"])

    assert result.exit_code == 0
    assert "debug" in result.output


def test_cli_exposes_llm_chat_debug_option():
    result = CliRunner().invoke(app, ["llm-chat", "--help"])

    assert result.exit_code == 0
    assert "debug" in result.output

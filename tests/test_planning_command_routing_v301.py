from pathlib import Path

from dr_magu.commands.context import CommandContext
from dr_magu.commands.processor import CommandProcessor
from dr_magu.commands.registry import registry
from dr_magu.tui_app import _is_registered_command_line


def _context(tmp_path: Path) -> CommandContext:
    return CommandContext(workspace_path=str(tmp_path), output_format="human", config={})


def test_space_style_plan_commands_normalize_to_registered_commands() -> None:
    assert CommandProcessor.parse_line("plan list")["command_name"] == "plan.list"
    assert CommandProcessor.parse_line("plan create Analyze repository")["command_name"] == "plan.create"
    assert CommandProcessor.parse_line("plan show plan-1")["command_name"] == "plan.show"
    assert CommandProcessor.parse_line("plan run plan-1")["command_name"] == "plan.run"
    assert CommandProcessor.parse_line("plan status plan-1")["command_name"] == "plan.status"
    assert CommandProcessor.parse_line("plan approve plan-1")["command_name"] == "plan.approve"
    assert CommandProcessor.parse_line("plan cancel plan-1")["command_name"] == "plan.cancel"


def test_tui_command_detection_accepts_normalized_plan_commands() -> None:
    processor = CommandProcessor(registry)
    assert _is_registered_command_line("plan list", processor, registry) is True
    assert _is_registered_command_line("plan create Analyze this repository", processor, registry) is True
    assert _is_registered_command_line("plan run demo-plan", processor, registry) is True
    assert _is_registered_command_line("tell me a joke", processor, registry) is False


def test_plan_list_executes_real_command_not_chat(tmp_path: Path) -> None:
    result = CommandProcessor(registry).execute_line("plan list", _context(tmp_path))
    assert result.tool == "plan.list"
    assert result.success is True
    assert result.data["count"] == 0

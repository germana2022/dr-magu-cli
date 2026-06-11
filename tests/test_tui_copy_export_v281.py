from pathlib import Path

from dr_magu.result import ToolResult
from dr_magu.tui.clipboard import format_tool_result_for_copy, write_text_artifact, workspace_tui_dir


def test_format_tool_result_for_copy_includes_plain_payload() -> None:
    result = ToolResult(success=True, tool="team.run", data={"summary": "4 completed, 0 failed"})

    text = format_tool_result_for_copy('team.run repo-analysis "Analyze"', result)

    assert '"command": "team.run repo-analysis \\"Analyze\\""' in text
    assert '"tool": "team.run"' in text
    assert '"success": true' in text
    assert '4 completed, 0 failed' in text


def test_write_text_artifact_creates_workspace_tui_folder(tmp_path: Path) -> None:
    output = write_text_artifact(tmp_path, "session-transcript.txt", "hello")

    assert output == workspace_tui_dir(tmp_path) / "session-transcript.txt"
    assert output.read_text(encoding="utf-8") == "hello"

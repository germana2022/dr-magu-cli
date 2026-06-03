from dr_magu.commands.context import CommandContext
from dr_magu.commands.processor import CommandProcessor


def test_parse_files_read_command_line():
    parsed = CommandProcessor.parse_line("files.read README.md")

    assert parsed["command_name"] == "files.read"
    assert parsed["args"]["path"] == "README.md"


def test_parse_search_code_command_line():
    parsed = CommandProcessor.parse_line('search.code "ToolResult" src')

    assert parsed["command_name"] == "search.code"
    assert parsed["args"]["query"] == "ToolResult"
    assert parsed["args"]["path"] == "src"


def test_execute_files_list_through_processor(tmp_path):
    (tmp_path / "README.md").write_text("hello", encoding="utf-8")
    processor = CommandProcessor()
    context = CommandContext(workspace_path=str(tmp_path))

    result = processor.execute("files.list", {"path": "."}, context)

    assert result.success is True
    assert result.tool == "files.list"
    assert "README.md" in result.data["files"]


def test_execute_line_files_read_through_processor(tmp_path):
    (tmp_path / "README.md").write_text("hello", encoding="utf-8")
    processor = CommandProcessor()
    context = CommandContext(workspace_path=str(tmp_path))

    result = processor.execute_line("files.read README.md", context)

    assert result.success is True
    assert result.data["content"] == "hello"


def test_unknown_command_returns_error(tmp_path):
    processor = CommandProcessor()
    context = CommandContext(workspace_path=str(tmp_path))

    result = processor.execute("unknown.command", {}, context)

    assert result.success is False
    assert "Unknown command" in result.errors[0]

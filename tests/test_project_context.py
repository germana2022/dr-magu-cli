from __future__ import annotations

import json
from pathlib import Path

from dr_magu.commands.context import CommandContext
from dr_magu.commands.processor import CommandProcessor
from dr_magu.commands.registry import registry
from dr_magu.project_context.generator import generate_project_context, get_context_path, show_project_context


def test_generate_project_context_creates_markdown_and_json_files(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        """
[project]
name = "sample-cli"
dependencies = ["typer", "textual", "pytest"]
""",
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text("# Sample CLI", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()

    result = generate_project_context(str(tmp_path))

    assert result.success
    context_dir = tmp_path / ".dr-magu" / "context"
    assert (context_dir / "PROJECT_CONTEXT.md").exists()
    assert (context_dir / "TECH_STACK.md").exists()
    assert (context_dir / "REPOSITORY_MAP.md").exists()
    assert (context_dir / "ARCHITECTURE_NOTES.md").exists()
    assert (context_dir / "dr-magu-context.json").exists()

    data = json.loads((context_dir / "dr-magu-context.json").read_text(encoding="utf-8"))
    assert data["project_name"] == tmp_path.name
    assert data["project_type"] in {"Python CLI/TUI application", "Python package"}


def test_show_project_context_returns_error_when_missing(tmp_path: Path) -> None:
    result = show_project_context(str(tmp_path))

    assert not result.success
    assert "Run 'dr-magu context generate' first" in result.errors[0]


def test_context_path_reports_expected_location(tmp_path: Path) -> None:
    result = get_context_path(str(tmp_path))

    assert result.success
    assert result.data["context_dir"].endswith(".dr-magu/context")
    assert result.data["exists"] is False


def test_context_generate_is_registered_in_command_processor(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Demo", encoding="utf-8")
    context = CommandContext(workspace_path=str(tmp_path), output_format="human", config={})
    processor = CommandProcessor(registry)

    result = processor.execute_line("context.generate", context)

    assert result.success
    assert result.tool == "context.generate"
    assert (tmp_path / ".dr-magu" / "context" / "PROJECT_CONTEXT.md").exists()


def test_context_generate_refresh_flag_is_parsed(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Demo", encoding="utf-8")
    parsed = CommandProcessor.parse_line("context.generate --refresh true")

    assert parsed["command_name"] == "context.generate"
    assert parsed["args"]["refresh"] == "true"

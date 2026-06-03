from pathlib import Path

from dr_magu.scanner.repository_scanner import scan_repository
from dr_magu.scanner.models import RepositoryScan
from dr_magu.scanner.writers import write_latest_scan


def test_scan_repository_detects_python_cli_project(tmp_path: Path):
    (tmp_path / "src" / "sample").mkdir(parents=True)
    (tmp_path / "tests").mkdir()
    (tmp_path / "README.md").write_text("# Sample", encoding="utf-8")
    (tmp_path / "src" / "sample" / "cli.py").write_text("print('hello')", encoding="utf-8")
    (tmp_path / "tests" / "test_cli.py").write_text("def test_ok(): assert True", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        """
[build-system]
requires = ["setuptools>=69.0.0"]

[project]
name = "sample"
dependencies = ["typer>=0.12", "textual>=0.85", "rich>=13", "pytest>=8"]
""".strip(),
        encoding="utf-8",
    )

    result = scan_repository(str(tmp_path))

    assert result.success is True
    assert result.tool == "repo.scan"
    assert result.data["primary_language"] == "Python"
    assert result.data["project_type"] == "Python CLI/TUI application"
    assert "Typer" in result.data["frameworks"]
    assert "Textual" in result.data["frameworks"]
    assert "pytest" in result.data["test_frameworks"]


def test_write_latest_scan_persists_scan_json(tmp_path: Path):
    result = scan_repository(str(tmp_path))
    scan = RepositoryScan.model_validate(result.data)

    output_path = write_latest_scan(str(tmp_path), scan)

    assert output_path == tmp_path / ".dr-magu" / "scans" / "latest-scan.json"
    assert output_path.exists()
    assert "workspace_path" in output_path.read_text(encoding="utf-8")

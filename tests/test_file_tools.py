from pathlib import Path
from dr_magu.tools.file_tools import read_file, list_files


def test_read_file_returns_content(tmp_path: Path):
    readme = tmp_path / "README.md"
    readme.write_text("hello", encoding="utf-8")

    result = read_file(str(tmp_path), "README.md")

    assert result.success is True
    assert result.data["content"] == "hello"


def test_list_files_returns_files(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("print('hi')", encoding="utf-8")

    result = list_files(str(tmp_path), ".")

    assert result.success is True
    assert "src/app.py" in result.data["files"]

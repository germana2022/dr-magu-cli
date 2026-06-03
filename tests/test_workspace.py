from pathlib import Path
import pytest
from dr_magu.workspace import Workspace


def test_resolve_allows_paths_inside_workspace(tmp_path: Path):
    workspace = Workspace(tmp_path)
    file_path = workspace.resolve("README.md")
    assert file_path == tmp_path / "README.md"


def test_resolve_blocks_paths_outside_workspace(tmp_path: Path):
    workspace = Workspace(tmp_path)
    with pytest.raises(ValueError):
        workspace.resolve("../outside.txt")

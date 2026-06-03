from __future__ import annotations

from pathlib import Path


class Workspace:
    def __init__(self, root: str | Path = ".") -> None:
        self.root = Path(root).resolve()

    def resolve(self, path: str | Path) -> Path:
        candidate = (self.root / path).resolve()
        if not self.is_inside(candidate):
            raise ValueError(f"Path escapes workspace: {path}")
        return candidate

    def is_inside(self, path: Path) -> bool:
        try:
            path.resolve().relative_to(self.root)
            return True
        except ValueError:
            return False

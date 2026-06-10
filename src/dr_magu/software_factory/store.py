from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class SoftwareFactoryStore:
    """Stores software factory artifacts under .dr-magu/factory."""

    def __init__(self, workspace_path: str | Path):
        self.workspace_path = Path(workspace_path).resolve()
        self.root = self.workspace_path / ".dr-magu" / "factory"
        self.root.mkdir(parents=True, exist_ok=True)

    def write_markdown(self, filename: str, title: str, body: str) -> dict[str, Any]:
        path = self.root / filename
        path.write_text(body, encoding="utf-8")
        return {"path": str(path), "filename": filename, "title": title, "artifact_type": "markdown"}

    def write_json(self, filename: str, payload: dict[str, Any]) -> dict[str, Any]:
        path = self.root / filename
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return {"path": str(path), "filename": filename, "artifact_type": "json"}

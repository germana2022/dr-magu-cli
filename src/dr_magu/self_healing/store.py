from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class HealingStore:
    """Stores self-healing reports under .dr-magu/healing."""

    def __init__(self, workspace_path: str | Path):
        self.workspace_path = Path(workspace_path).resolve()
        self.root = self.workspace_path / ".dr-magu" / "healing"
        self.root.mkdir(parents=True, exist_ok=True)

    def write_report(self, report: dict[str, Any], filename: str = "latest-healing-report.json") -> dict[str, Any]:
        path = self.root / filename
        path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        return {"path": str(path), "filename": filename, "artifact_type": "json"}

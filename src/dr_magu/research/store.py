from __future__ import annotations

import json
from pathlib import Path

from .models import ResearchResult


class ResearchStore:
    """Persist research outputs inside the workspace .dr-magu directory."""

    def __init__(self, workspace_path: str | Path):
        self.workspace_path = Path(workspace_path).resolve()
        self.research_dir = self.workspace_path / ".dr-magu" / "research"

    def save_latest(self, result: ResearchResult) -> Path:
        self.research_dir.mkdir(parents=True, exist_ok=True)
        output_path = self.research_dir / "latest-research.json"
        output_path.write_text(json.dumps(result.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        return output_path

    def latest_path(self) -> Path:
        return self.research_dir / "latest-research.json"

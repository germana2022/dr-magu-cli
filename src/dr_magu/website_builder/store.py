from __future__ import annotations

import json
from pathlib import Path

from .models import WebsiteArchitectureOption, WebsiteBuilderResult


class WebsiteBuilderStore:
    """Persist Website Builder workflow artifacts."""

    def __init__(self, workspace_path: str | Path):
        self.workspace_path = Path(workspace_path).resolve()
        self.base_dir = self.workspace_path / ".dr-magu" / "website-builder"

    def save_proposal(self, topic: str, body: str) -> Path:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        path = self.base_dir / "website-proposal.md"
        path.write_text(body, encoding="utf-8")
        return path

    def save_architecture_options(self, options: list[WebsiteArchitectureOption]) -> Path:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        path = self.base_dir / "architecture-options.json"
        path.write_text(json.dumps([option.to_dict() for option in options], indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def save_result(self, result: WebsiteBuilderResult) -> Path:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        path = self.base_dir / "latest-website-builder-result.json"
        path.write_text(json.dumps(result.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        return path

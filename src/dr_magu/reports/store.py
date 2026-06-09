from __future__ import annotations

import json
from pathlib import Path

from .models import ReportDocument
from .renderers import HtmlReportRenderer, MarkdownReportRenderer


class ReportStore:
    """Persist generated reports inside the workspace .dr-magu directory."""

    def __init__(self, workspace_path: str | Path):
        self.workspace_path = Path(workspace_path).resolve()
        self.reports_dir = self.workspace_path / ".dr-magu" / "reports"

    def save(self, document: ReportDocument, base_name: str = "report") -> dict[str, str]:
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        md_path = self.reports_dir / f"{base_name}.md"
        html_path = self.reports_dir / f"{base_name}.html"
        json_path = self.reports_dir / f"{base_name}.json"

        md_path.write_text(MarkdownReportRenderer().render(document), encoding="utf-8")
        html_path.write_text(HtmlReportRenderer().render(document), encoding="utf-8")
        json_path.write_text(json.dumps(document.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

        return {
            "markdown": str(md_path),
            "html": str(html_path),
            "json": str(json_path),
        }

from __future__ import annotations

import json
from pathlib import Path

from dr_magu.result import ToolResult

from .models import ReportDocument, ReportSection
from .store import ReportStore


class ReportGenerator:
    """Generate Markdown, HTML and JSON reports."""

    def __init__(self, workspace_path: str | Path):
        self.workspace_path = Path(workspace_path).resolve()
        self.store = ReportStore(self.workspace_path)

    def generate(self, title: str, summary: str, sections: list[ReportSection] | None = None, source: str = "manual") -> ToolResult:
        if not title.strip():
            return ToolResult(success=False, tool="report.create", errors=["Report title is required."])

        document = ReportDocument(
            title=title.strip(),
            summary=summary.strip() or "No summary provided.",
            sections=sections or [],
            source=source,
        )
        output_paths = self.store.save(document)

        return ToolResult(
            success=True,
            tool="report.create",
            data={
                "title": document.title,
                "source": document.source,
                "outputs": output_paths,
                "section_count": len(document.sections),
            },
        )

    def generate_from_latest_research(self) -> ToolResult:
        research_path = self.workspace_path / ".dr-magu" / "research" / "latest-research.json"
        if not research_path.exists():
            return ToolResult(
                success=False,
                tool="report.from_research",
                errors=["No latest research file found. Run research.search first."],
            )

        payload = json.loads(research_path.read_text(encoding="utf-8"))
        topic = str(payload.get("topic") or payload.get("query") or "Research Report")
        sources = payload.get("sources", []) or []

        sections = [
            ReportSection(
                title=str(source.get("title") or "Untitled Source"),
                body=f"{source.get('summary', '')}\n\nURL: {source.get('url', '')}",
            )
            for source in sources
        ]

        return self.generate(
            title=f"Research Report: {topic}",
            summary=f"Generated from {len(sections)} research source(s).",
            sections=sections,
            source="research.latest",
        )

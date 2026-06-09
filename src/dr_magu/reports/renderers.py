from __future__ import annotations

import html

from .models import ReportDocument


class MarkdownReportRenderer:
    """Render a report document as Markdown."""

    def render(self, document: ReportDocument) -> str:
        lines = [
            f"# {document.title}",
            "",
            f"Generated at: {document.generated_at}",
            f"Source: {document.source}",
            "",
            "## Summary",
            "",
            document.summary,
            "",
        ]

        for section in document.sections:
            lines.extend([
                f"## {section.title}",
                "",
                section.body,
                "",
            ])

        return "\n".join(lines).rstrip() + "\n"


class HtmlReportRenderer:
    """Render a report document as a simple standalone HTML document."""

    def render(self, document: ReportDocument) -> str:
        sections = "\n".join(
            f"<section><h2>{html.escape(section.title)}</h2><p>{html.escape(section.body)}</p></section>"
            for section in document.sections
        )
        return (
            "<!doctype html>\n"
            "<html lang=\"en\">\n"
            "<head><meta charset=\"utf-8\"><title>"
            + html.escape(document.title)
            + "</title></head>\n"
            "<body>\n"
            f"<h1>{html.escape(document.title)}</h1>\n"
            f"<p><strong>Generated at:</strong> {html.escape(document.generated_at)}</p>\n"
            f"<p><strong>Source:</strong> {html.escape(document.source)}</p>\n"
            "<h2>Summary</h2>\n"
            f"<p>{html.escape(document.summary)}</p>\n"
            f"{sections}\n"
            "</body>\n</html>\n"
        )

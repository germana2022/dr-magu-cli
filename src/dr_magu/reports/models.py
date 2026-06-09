from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class ReportSection:
    """A report section with a title and body."""

    title: str
    body: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "body": self.body,
        }


@dataclass(frozen=True)
class ReportDocument:
    """Structured report document used by report renderers."""

    title: str
    summary: str
    sections: list[ReportSection] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str = "manual"

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "summary": self.summary,
            "generated_at": self.generated_at,
            "source": self.source,
            "sections": [section.to_dict() for section in self.sections],
        }

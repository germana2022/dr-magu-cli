from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class WebsiteArchitectureOption:
    """Architecture option generated for a website proposal."""

    id: str
    title: str
    description: str
    stack: list[str] = field(default_factory=list)
    tradeoffs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "stack": self.stack,
            "tradeoffs": self.tradeoffs,
        }


@dataclass(frozen=True)
class WebsiteBuilderResult:
    """Result produced by the Website Builder workflow foundation."""

    topic: str
    status: str
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    research_output_path: str | None = None
    proposal_path: str | None = None
    architecture_options_path: str | None = None
    approval_id: str | None = None
    report_outputs: dict[str, str] = field(default_factory=dict)
    architecture_options: list[WebsiteArchitectureOption] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "topic": self.topic,
            "status": self.status,
            "generated_at": self.generated_at,
            "research_output_path": self.research_output_path,
            "proposal_path": self.proposal_path,
            "architecture_options_path": self.architecture_options_path,
            "approval_id": self.approval_id,
            "report_outputs": self.report_outputs,
            "architecture_options": [option.to_dict() for option in self.architecture_options],
        }

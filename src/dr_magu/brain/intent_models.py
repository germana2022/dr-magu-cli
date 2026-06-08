from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


INTENT_WORKSPACE_ACTION = "workspace_action"
INTENT_GENERAL_CHAT = "general_chat"
INTENT_RESEARCH_ACTION = "research_action"
INTENT_DOCUMENT_ACTION = "document_action"
INTENT_SOFTWARE_ACTION = "software_action"
INTENT_SCHEDULE_ACTION = "schedule_action"
INTENT_UNKNOWN = "unknown"


@dataclass(frozen=True)
class IntentClassification:
    """Classification result produced by the Intent Router."""

    intent: str
    language: str
    confidence: float
    reason: str
    suggested_route: str
    matched_keywords: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "language": self.language,
            "confidence": self.confidence,
            "reason": self.reason,
            "suggested_route": self.suggested_route,
            "matched_keywords": self.matched_keywords,
            "metadata": self.metadata,
        }

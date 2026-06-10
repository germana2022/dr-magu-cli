from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class ResearchSource:
    """Single source returned by a research provider."""

    title: str
    url: str
    summary: str
    score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {"title": self.title, "url": self.url, "summary": self.summary, "score": self.score}


@dataclass(frozen=True)
class ResearchResult:
    """Research result payload persisted and rendered by Dr Magu."""

    topic: str
    query: str
    sources: list[ResearchSource] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    provider: str = "deterministic"
    provider_chain: list[str] = field(default_factory=list)
    fallback_used: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "topic": self.topic,
            "query": self.query,
            "generated_at": self.generated_at,
            "provider": self.provider,
            "provider_chain": self.provider_chain,
            "fallback_used": self.fallback_used,
            "sources": [source.to_dict() for source in self.sources],
        }

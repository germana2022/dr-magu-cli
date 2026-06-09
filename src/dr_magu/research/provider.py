from __future__ import annotations

from .models import ResearchResult, ResearchSource


class DeterministicResearchProvider:
    """Deterministic research provider used until live web search is configured."""

    def search(self, topic: str, limit: int = 5) -> ResearchResult:
        safe_limit = max(1, min(limit, 10))
        sources = [
            ResearchSource(
                title=f"{topic} reference source {index}",
                url=f"https://example.com/research/{index}",
                summary=(
                    f"Deterministic summary for {topic}. "
                    "Replace this provider with a real web connector in a future version."
                ),
                score=round(1.0 - (index - 1) * 0.05, 2),
            )
            for index in range(1, safe_limit + 1)
        ]
        return ResearchResult(topic=topic, query=topic, sources=sources)

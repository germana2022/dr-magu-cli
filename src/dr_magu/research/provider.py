from __future__ import annotations

from .models import ResearchResult, ResearchSource


class DeterministicResearchProvider:
    """Deterministic research provider used as an explicit fallback."""

    def __init__(self, provider: str = "deterministic"):
        self.provider = provider

    def search(self, topic: str, limit: int = 5) -> ResearchResult:
        safe_limit = max(1, min(limit, 10))
        sources = [
            ResearchSource(
                title=f"{topic} reference source {index}",
                url=f"https://example.com/research/{index}",
                summary=(
                    f"Deterministic fallback summary for {topic}. "
                    "Configure Brave Search, Playwright, GitHub, or Filesystem MCP for live results."
                ),
                score=round(1.0 - (index - 1) * 0.05, 2),
            )
            for index in range(1, safe_limit + 1)
        ]
        return ResearchResult(topic=topic, query=topic, sources=sources, provider=self.provider, provider_chain=[self.provider])

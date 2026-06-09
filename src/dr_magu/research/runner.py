from __future__ import annotations

from pathlib import Path

from dr_magu.result import ToolResult

from .provider import DeterministicResearchProvider
from .store import ResearchStore


class WebResearchRunner:
    """Run web research workflows through a provider boundary."""

    def __init__(self, workspace_path: str | Path):
        self.workspace_path = Path(workspace_path).resolve()
        self.provider = DeterministicResearchProvider()
        self.store = ResearchStore(self.workspace_path)

    def search(self, topic: str, limit: int = 5, persist: bool = True) -> ToolResult:
        if not topic.strip():
            return ToolResult(success=False, tool="research.search", errors=["Research topic is required."])

        result = self.provider.search(topic.strip(), limit=limit)
        output_path = self.store.save_latest(result) if persist else None

        return ToolResult(
            success=True,
            tool="research.search",
            data={
                "topic": result.topic,
                "query": result.query,
                "provider": result.provider,
                "source_count": len(result.sources),
                "sources": [source.to_dict() for source in result.sources],
                "output_path": str(output_path) if output_path else None,
            },
        )

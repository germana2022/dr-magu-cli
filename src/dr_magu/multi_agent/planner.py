from __future__ import annotations

from .models import AgentTask, OrchestrationPlan


SDLC_PIPELINE = [
    AgentTask("repository-analyzer", "sdlc.agent.run repository-analyzer", "Analyze repository structure."),
    AgentTask("architecture-planner", "sdlc.agent.run architecture-planner", "Generate architecture options.", ["repository-analyzer"]),
    AgentTask("ticket-generator", "sdlc.agent.run ticket-generator", "Generate implementation tickets.", ["architecture-planner"]),
    AgentTask("test-generator", "sdlc.agent.run test-generator", "Generate test strategy.", ["ticket-generator"]),
    AgentTask("documentation-writer", "sdlc.agent.run documentation-writer", "Generate documentation plan.", ["test-generator"]),
    AgentTask("release-notes-generator", "sdlc.agent.run release-notes-generator", "Generate release notes.", ["documentation-writer"]),
]

RESEARCH_TO_BUILD_PIPELINE = [
    AgentTask("web-researcher", "research.search", "Research source material."),
    AgentTask("website-analyzer", "website.analyze", "Analyze selected website.", ["web-researcher"]),
    AgentTask("architecture-planner", "sdlc.agent.run architecture-planner", "Plan implementation architecture.", ["website-analyzer"]),
    AgentTask("ticket-generator", "sdlc.agent.run ticket-generator", "Create prioritized tickets.", ["architecture-planner"]),
]


class MultiAgentPlanner:
    """Build predefined multi-agent plans."""

    def create_plan(self, name: str = "sdlc.pipeline", mode: str = "sequential") -> OrchestrationPlan:
        if name in {"sdlc.pipeline", "software.pipeline", "software-factory"}:
            return OrchestrationPlan(name=name, mode=mode, tasks=SDLC_PIPELINE)
        if name in {"research.build", "website.research", "website.pipeline"}:
            return OrchestrationPlan(name=name, mode=mode, tasks=RESEARCH_TO_BUILD_PIPELINE)
        return OrchestrationPlan(name=name, mode=mode, tasks=SDLC_PIPELINE)

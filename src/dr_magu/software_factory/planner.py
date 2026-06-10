from __future__ import annotations

from .models import FactoryPlan, FactoryStage


class SoftwareFactoryPlanner:
    """Build end-to-end software delivery plans."""

    def create_plan(self, idea: str, name: str = "software.factory") -> FactoryPlan:
        idea = idea.strip() or "Build a software product"
        quoted = idea.replace('"', '\"')
        stages = [
            FactoryStage(
                id="idea-intake",
                title="Idea Intake",
                command=f'factory.stage "{quoted}" --stage idea-intake',
                description="Capture the product idea, assumptions, goals and constraints.",
                artifact_name="01-idea-intake.md",
            ),
            FactoryStage(
                id="research",
                title="Research",
                command=f'research.search "{quoted}"',
                description="Research the market, users, competitors and source material.",
                artifact_name="02-research.md",
                depends_on=["idea-intake"],
            ),
            FactoryStage(
                id="architecture",
                title="Architecture",
                command="sdlc.agent.run architecture-planner",
                description="Generate architecture options, trade-offs and recommendations.",
                artifact_name="03-architecture.md",
                depends_on=["research"],
            ),
            FactoryStage(
                id="tickets",
                title="Tickets",
                command="sdlc.agent.run ticket-generator",
                description="Generate implementation tickets and a prioritized delivery plan.",
                artifact_name="04-tickets.json",
                depends_on=["architecture"],
            ),
            FactoryStage(
                id="code-plan",
                title="Code Plan",
                command=f'factory.stage "{quoted}" --stage code-plan',
                description="Generate code implementation plan, modules, commands and file boundaries.",
                artifact_name="05-code-plan.md",
                depends_on=["tickets"],
            ),
            FactoryStage(
                id="tests",
                title="Tests",
                command="sdlc.agent.run test-generator",
                description="Generate test strategy and suggested test coverage.",
                artifact_name="06-tests.md",
                depends_on=["code-plan"],
            ),
            FactoryStage(
                id="documentation",
                title="Documentation",
                command="sdlc.agent.run documentation-writer",
                description="Generate documentation plan and developer/user docs outline.",
                artifact_name="07-documentation.md",
                depends_on=["tests"],
            ),
            FactoryStage(
                id="release-notes",
                title="Release Notes",
                command="sdlc.agent.run release-notes-generator",
                description="Generate release notes and final delivery summary.",
                artifact_name="08-release-notes.md",
                depends_on=["documentation"],
            ),
        ]
        return FactoryPlan(name=name, idea=idea, stages=stages)

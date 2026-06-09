from __future__ import annotations

from pathlib import Path

from dr_magu.hitl.engine import ApprovalEngine
from dr_magu.hitl.models import ApprovalOption
from dr_magu.reports.generator import ReportGenerator
from dr_magu.reports.models import ReportSection
from dr_magu.research.runner import WebResearchRunner
from dr_magu.result import ToolResult
from dr_magu.sdlc.agents import SoftwareAgentRunner

from .models import WebsiteArchitectureOption, WebsiteBuilderResult
from .store import WebsiteBuilderStore


class WebsiteBuilderWorkflow:
    """Deterministic Website Builder workflow foundation.

    v0.18.0 creates a traceable proposal and approval workflow. Real code
    generation is intentionally left for later versions after the Workflow Engine.
    """

    def __init__(self, workspace_path: str | Path):
        self.workspace_path = Path(workspace_path).resolve()
        self.store = WebsiteBuilderStore(self.workspace_path)

    def generate(self, topic: str, research_limit: int = 5) -> ToolResult:
        if not topic.strip():
            return ToolResult(success=False, tool="website.build", errors=["Website topic is required."])

        topic = topic.strip()

        research_result = WebResearchRunner(self.workspace_path).search(topic, limit=research_limit)
        if not research_result.success:
            return research_result

        SoftwareAgentRunner(self.workspace_path).run("architecture-planner")
        SoftwareAgentRunner(self.workspace_path).run("ticket-generator")
        SoftwareAgentRunner(self.workspace_path).run("documentation-writer")

        options = self._architecture_options(topic)
        options_path = self.store.save_architecture_options(options)
        proposal_path = self.store.save_proposal(topic, self._proposal_markdown(topic, options))

        approval_result = ApprovalEngine(self.workspace_path).request(
            title=f"Select website architecture for {topic}",
            description="Choose one of the generated architecture options before code generation.",
            action="website.generate",
            risk_level="high",
            options=[
                ApprovalOption(
                    id=option.id,
                    title=option.title,
                    description=option.description,
                    metadata={"stack": option.stack, "tradeoffs": option.tradeoffs},
                )
                for option in options
            ],
        )

        report_result = ReportGenerator(self.workspace_path).generate(
            title=f"Website Builder Proposal: {topic}",
            summary="Generated deterministic website proposal from research and architecture options.",
            sections=[
                ReportSection(
                    title="Architecture Options",
                    body="\n".join(f"- {option.title}: {option.description}" for option in options),
                ),
                ReportSection(
                    title="Human Approval",
                    body=f"Approval request: {approval_result.data['approval']['id']}",
                ),
            ],
            source="website-builder",
        )

        result = WebsiteBuilderResult(
            topic=topic,
            status="waiting_for_approval",
            research_output_path=research_result.data.get("output_path"),
            proposal_path=str(proposal_path),
            architecture_options_path=str(options_path),
            approval_id=approval_result.data["approval"]["id"],
            report_outputs=report_result.data.get("outputs", {}),
            architecture_options=options,
        )
        result_path = self.store.save_result(result)

        return ToolResult(
            success=True,
            tool="website.build",
            data={
                "result": result.to_dict(),
                "result_path": str(result_path),
            },
        )

    def _architecture_options(self, topic: str) -> list[WebsiteArchitectureOption]:
        return [
            WebsiteArchitectureOption(
                id="static-marketing",
                title="Static Marketing Website",
                description="A fast static website suitable for landing pages and informational content.",
                stack=["HTML", "CSS", "JavaScript", "Static Hosting"],
                tradeoffs=["Very fast", "Low cost", "Limited dynamic behavior"],
            ),
            WebsiteArchitectureOption(
                id="nextjs-app-router",
                title="Next.js App Router Website",
                description="A modern React-based architecture for SEO, routing and future backend integration.",
                stack=["Next.js", "React", "TypeScript", "Tailwind CSS"],
                tradeoffs=["Scalable", "Good SEO", "Requires Node.js ecosystem"],
            ),
            WebsiteArchitectureOption(
                id="headless-cms",
                title="Headless CMS Website",
                description="A content-driven architecture for teams that need frequent content updates.",
                stack=["Next.js", "Headless CMS", "TypeScript", "API Integration"],
                tradeoffs=["Content flexibility", "More integrations", "Higher setup complexity"],
            ),
            WebsiteArchitectureOption(
                id="custom-user-option",
                title="Custom User-Suggested Architecture",
                description="Reserved option for a human-proposed architecture before generation.",
                stack=["User-defined"],
                tradeoffs=["Flexible", "Requires manual definition"],
            ),
        ]

    def _proposal_markdown(self, topic: str, options: list[WebsiteArchitectureOption]) -> str:
        lines = [
            f"# Website Proposal: {topic}",
            "",
            "## Goal",
            "",
            f"Create a website proposal for `{topic}` using research, architecture planning and HITL selection.",
            "",
            "## Architecture Options",
            "",
        ]

        for option in options:
            lines.extend([
                f"### {option.title}",
                "",
                option.description,
                "",
                "Stack:",
                "",
                *[f"- {item}" for item in option.stack],
                "",
                "Tradeoffs:",
                "",
                *[f"- {item}" for item in option.tradeoffs],
                "",
            ])

        lines.extend([
            "## Next Step",
            "",
            "A human approval request has been created. Select an architecture option before code generation.",
            "",
        ])

        return "\n".join(lines)

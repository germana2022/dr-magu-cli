from __future__ import annotations

from dr_magu.result import ToolResult

from .models import WorkflowDefinition, WorkflowStep


class WorkflowEngine:
    """Workflow definition factory and validator."""

    def website_builder_definition(self, topic: str) -> WorkflowDefinition:
        topic = topic.strip() or "Website"
        return WorkflowDefinition(
            id="website-builder",
            name="Website Builder",
            description="Research, propose architecture, request approval and generate report.",
            steps=[
                WorkflowStep(
                    id="research",
                    name="Research Websites",
                    type="command",
                    command=f"research.search {topic}",
                    description="Collect deterministic research sources for the website topic.",
                ),
                WorkflowStep(
                    id="website-proposal",
                    name="Generate Website Proposal",
                    type="command",
                    command=f"website.build {topic}",
                    description="Generate proposal, architecture options, HITL request and report.",
                ),
            ],
        )

    def validate(self, definition: WorkflowDefinition) -> ToolResult:
        errors: list[str] = []
        if not definition.id.strip():
            errors.append("Workflow id is required.")
        if not definition.steps:
            errors.append("Workflow requires at least one step.")
        for step in definition.steps:
            if step.type != "command":
                errors.append(f"Unsupported step type: {step.type}")
            if not step.command.strip():
                errors.append(f"Step command is required: {step.id}")

        return ToolResult(
            success=not errors,
            tool="workflow.engine.validate",
            data={"workflow": definition.to_dict()},
            errors=errors,
        )

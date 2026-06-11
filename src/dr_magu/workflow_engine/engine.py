from __future__ import annotations

import json
from pathlib import Path
from string import Template
from typing import Any

import yaml

from dr_magu.result import ToolResult

from .models import WorkflowDefinition, WorkflowStep


class WorkflowEngine:
    """Workflow definition catalog, loader and validator.

    v2.5.0 promotes the earlier foundation into an operational workflow
    orchestration engine. Definitions can be built in or loaded from
    `.dr-magu/workflows/*.json|*.yaml|*.yml` inside the workspace.
    """

    def __init__(self, workspace_path: str | Path = ".") -> None:
        self.workspace_path = Path(workspace_path).resolve()

    def built_in_definitions(self) -> list[WorkflowDefinition]:
        return [
            self.website_builder_definition("${topic}"),
            self.research_brief_definition("${topic}"),
            self.repository_context_definition(),
        ]

    def website_builder_definition(self, topic: str) -> WorkflowDefinition:
        topic = topic.strip() or "Website"
        return WorkflowDefinition(
            id="website-builder",
            name="Website Builder",
            description="Research, propose architecture, request approval and generate report.",
            version="2.5.0",
            tags=["research", "website", "report"],
            inputs={"topic": "Website topic"},
            steps=[
                WorkflowStep(
                    id="research",
                    name="Research Websites",
                    type="command",
                    command=f"research.search {topic}",
                    description="Collect research sources for the website topic.",
                    output_key="research",
                ),
                WorkflowStep(
                    id="website-proposal",
                    name="Generate Website Proposal",
                    type="command",
                    command=f"website.build {topic}",
                    description="Generate proposal, architecture options, HITL request and report.",
                    output_key="website_proposal",
                ),
            ],
        )

    def research_brief_definition(self, topic: str) -> WorkflowDefinition:
        topic = topic.strip() or "${topic}"
        return WorkflowDefinition(
            id="research-brief",
            name="Research Brief",
            description="Run multi-provider research and persist a concise research result.",
            version="2.5.0",
            tags=["research", "mcp", "multi-provider"],
            inputs={"topic": "Research topic"},
            steps=[
                WorkflowStep(
                    id="research",
                    name="Run Research",
                    type="command",
                    command=f"research.search {topic} --provider auto --allow-fallback",
                    description="Collect sources through the active MCP research providers.",
                    output_key="research",
                ),
            ],
        )

    def repository_context_definition(self) -> WorkflowDefinition:
        return WorkflowDefinition(
            id="repository-context",
            name="Repository Context",
            description="Scan the workspace and generate deterministic project context.",
            version="2.5.0",
            tags=["repository", "context", "filesystem"],
            steps=[
                WorkflowStep(
                    id="repo-scan",
                    name="Scan Repository",
                    type="command",
                    command="repo.scan .",
                    description="Scan repository metadata.",
                    output_key="repo_scan",
                ),
                WorkflowStep(
                    id="context-generate",
                    name="Generate Context",
                    type="command",
                    command="context.generate",
                    description="Generate PROJECT_CONTEXT artifacts from scan metadata.",
                    output_key="project_context",
                ),
            ],
        )

    def list_definitions(self) -> list[WorkflowDefinition]:
        definitions = {definition.id: definition for definition in self.built_in_definitions()}
        for definition in self.load_workspace_definitions():
            definitions[definition.id] = definition
        return sorted(definitions.values(), key=lambda item: item.id)

    def get_definition(self, workflow_id: str, variables: dict[str, Any] | None = None) -> WorkflowDefinition:
        workflow_id = (workflow_id or "website-builder").strip()
        aliases = {
            "website.build": "website-builder",
            "site": "website-builder",
            "research": "research-brief",
            "research.multi": "research-brief",
            "repo.context": "repository-context",
            "repository.context": "repository-context",
        }
        resolved = aliases.get(workflow_id, workflow_id)
        definitions = {definition.id: definition for definition in self.list_definitions()}
        if resolved not in definitions:
            available = ", ".join(sorted(definitions))
            raise KeyError(f"Unknown workflow '{workflow_id}'. Available workflows: {available}")
        definition = definitions[resolved]
        return self.render_definition(definition, variables or {})

    def load_workspace_definitions(self) -> list[WorkflowDefinition]:
        directory = self.workspace_path / ".dr-magu" / "workflows"
        if not directory.exists():
            return []
        definitions: list[WorkflowDefinition] = []
        for path in sorted(list(directory.glob("*.json")) + list(directory.glob("*.yaml")) + list(directory.glob("*.yml"))):
            payload = self._read_definition_file(path)
            definitions.append(WorkflowDefinition.from_dict(payload))
        return definitions

    def _read_definition_file(self, path: Path) -> dict[str, Any]:
        raw = path.read_text(encoding="utf-8")
        if path.suffix.lower() == ".json":
            return json.loads(raw)
        return yaml.safe_load(raw) or {}

    def render_definition(self, definition: WorkflowDefinition, variables: dict[str, Any]) -> WorkflowDefinition:
        rendered_steps: list[WorkflowStep] = []
        safe_variables = {key: str(value) for key, value in variables.items() if value is not None}
        for step in definition.steps:
            command = Template(step.command).safe_substitute(safe_variables)
            rendered_steps.append(
                WorkflowStep(
                    id=step.id,
                    name=Template(step.name).safe_substitute(safe_variables),
                    type=step.type,
                    command=command,
                    description=Template(step.description).safe_substitute(safe_variables),
                    enabled=step.enabled,
                    requires_approval=step.requires_approval,
                    timeout_seconds=step.timeout_seconds,
                    continue_on_error=step.continue_on_error,
                    output_key=step.output_key,
                )
            )
        return WorkflowDefinition(
            id=definition.id,
            name=Template(definition.name).safe_substitute(safe_variables),
            description=Template(definition.description).safe_substitute(safe_variables),
            version=definition.version,
            tags=definition.tags,
            inputs=definition.inputs,
            steps=rendered_steps,
        )

    def plan(self, definition: WorkflowDefinition) -> ToolResult:
        validation = self.validate(definition)
        return ToolResult(
            success=validation.success,
            tool="workflow.engine.plan",
            data={
                "workflow": definition.to_dict(),
                "step_count": len(definition.steps),
                "steps": [
                    {
                        "index": index,
                        "id": step.id,
                        "name": step.name,
                        "type": step.type,
                        "command": step.command,
                        "enabled": step.enabled,
                        "requires_approval": step.requires_approval,
                    }
                    for index, step in enumerate(definition.steps)
                ],
            },
            errors=validation.errors,
        )

    def validate(self, definition: WorkflowDefinition) -> ToolResult:
        errors: list[str] = []
        seen_step_ids: set[str] = set()
        if not definition.id.strip():
            errors.append("Workflow id is required.")
        if not definition.steps:
            errors.append("Workflow requires at least one step.")
        for step in definition.steps:
            if not step.id.strip():
                errors.append("Step id is required.")
            if step.id in seen_step_ids:
                errors.append(f"Duplicate step id: {step.id}")
            seen_step_ids.add(step.id)
            if step.type != "command":
                errors.append(f"Unsupported step type: {step.type}")
            if step.enabled and not step.command.strip():
                errors.append(f"Step command is required: {step.id}")

        return ToolResult(
            success=not errors,
            tool="workflow.engine.validate",
            data={"workflow": definition.to_dict()},
            errors=errors,
        )

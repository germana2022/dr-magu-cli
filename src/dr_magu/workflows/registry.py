from __future__ import annotations

from dr_magu.workflows.models import WorkflowDefinition


class WorkflowRegistry:
    """In-memory workflow registry used by CLI, TUI, and the command processor."""

    def __init__(self) -> None:
        self._workflows: dict[str, WorkflowDefinition] = {}
        self._aliases: dict[str, str] = {}

    def register(self, workflow: WorkflowDefinition) -> None:
        self._workflows[workflow.name] = workflow
        for alias in workflow.aliases:
            self._aliases[alias] = workflow.name

    def resolve(self, name: str) -> str:
        return self._aliases.get(name, name)

    def get(self, name: str) -> WorkflowDefinition:
        resolved = self.resolve(name)
        if resolved not in self._workflows:
            available = ", ".join(sorted(self._workflows))
            raise KeyError(f"Unknown workflow '{name}'. Available workflows: {available}")
        return self._workflows[resolved]

    def list(self) -> list[WorkflowDefinition]:
        return sorted(self._workflows.values(), key=lambda item: item.name)


workflow_registry = WorkflowRegistry()
workflow_registry.register(WorkflowDefinition(
    name="repository.context",
    aliases=["repo.context", "rc"],
    description="Run repository scan and generate deterministic project context.",
    workflow_type="deterministic",
    requires_llm=False,
))

from __future__ import annotations

from pathlib import Path

from dr_magu.agents.models import AgentDefinition
from dr_magu.workflows.registry import workflow_registry
from dr_magu.workflow_engine.engine import WorkflowEngine


class AgentValidator:
    """Validates agent definitions before they are registered or executed."""

    def __init__(self, workspace_path: str | Path) -> None:
        self.workspace_path = Path(workspace_path).resolve()

    def validate(self, agent: AgentDefinition) -> list[str]:
        errors: list[str] = []
        if not agent.id.strip():
            errors.append("Agent id is required.")
        if not agent.name.strip():
            errors.append("Agent name is required.")
        if not agent.workflow.strip():
            errors.append("Agent workflow is required.")
        else:
            try:
                workflow_registry.get(agent.workflow)
            except KeyError:
                try:
                    WorkflowEngine(self.workspace_path).get_definition(agent.workflow)
                except Exception:
                    errors.append(f"Agent references unknown workflow '{agent.workflow}'.")
        if not isinstance(agent.capabilities, list):
            errors.append("Agent capabilities must be a list.")
        if agent.model and not isinstance(agent.model, dict):
            errors.append("Agent model configuration must be a mapping.")
        return errors

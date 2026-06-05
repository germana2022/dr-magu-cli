from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from dr_magu.agents.models import AgentDefinition
from dr_magu.agents.registry import AgentRegistry
from dr_magu.agents.store import WorkspaceAgentStore
from dr_magu.agents.validator import AgentValidator
from dr_magu.result import ToolResult


class AgentManager:
    """Manages agent lifecycle operations through workspace-level overrides."""

    def __init__(self, workspace_path: str | Path) -> None:
        self.workspace_path = str(Path(workspace_path).resolve())
        self.store = WorkspaceAgentStore(self.workspace_path)
        self.validator = AgentValidator(self.workspace_path)

    def _registry(self) -> AgentRegistry:
        return AgentRegistry(self.workspace_path)

    def _definition_from_file(self, file_path: str | Path) -> AgentDefinition:
        path = Path(file_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Agent file not found: {path}")
        with path.open("r", encoding="utf-8") as file:
            payload = yaml.safe_load(file) or {}

        if "agents" in payload:
            agents = payload.get("agents") or {}
            if len(agents) != 1:
                raise ValueError("Agent file with 'agents' must contain exactly one agent definition.")
            agent_id, agent_payload = next(iter(agents.items()))
        else:
            agent_id = payload.get("id")
            agent_payload = payload
        if not agent_id:
            raise ValueError("Agent file must include an agent id or one entry under 'agents'.")
        agent_payload = agent_payload or {}
        return AgentDefinition(
            id=str(agent_id),
            name=str(agent_payload.get("name") or agent_id),
            description=str(agent_payload.get("description") or ""),
            role=str(agent_payload.get("role") or "general"),
            workflow=str(agent_payload.get("workflow") or ""),
            enabled=bool(agent_payload.get("enabled", True)),
            deleted=bool(agent_payload.get("deleted", False)),
            requires_llm=bool(agent_payload.get("requires_llm", False)),
            capabilities=list(agent_payload.get("capabilities", []) or []),
            aliases=list(agent_payload.get("aliases", []) or []),
            model=dict(agent_payload.get("model", {}) or {}),
            plugin_id=str(agent_payload.get("plugin_id")) if agent_payload.get("plugin_id") else None,
            source="workspace",
        )

    def add_from_file(self, file_path: str | Path) -> ToolResult:
        try:
            agent = self._definition_from_file(file_path)
            errors = self.validator.validate(agent)
            if errors:
                return ToolResult(success=False, tool="agent.add", data=agent.model_dump(), errors=errors)
            try:
                self._registry().get(agent.id, include_deleted=True)
                return ToolResult(success=False, tool="agent.add", errors=[f"Agent '{agent.id}' already exists. Use agent update instead."])
            except KeyError:
                pass
            self.store.upsert(agent)
            return ToolResult(success=True, tool="agent.add", data={"agent": agent.model_dump(), "store_path": str(self.store.path)})
        except Exception as exc:
            return ToolResult(success=False, tool="agent.add", errors=[str(exc)])

    def update_from_file(self, agent_id: str, file_path: str | Path) -> ToolResult:
        try:
            agent = self._definition_from_file(file_path)
            if agent.id != agent_id:
                agent = agent.model_copy(update={"id": agent_id})
            errors = self.validator.validate(agent)
            if errors:
                return ToolResult(success=False, tool="agent.update", data=agent.model_dump(), errors=errors)
            self.store.upsert(agent)
            return ToolResult(success=True, tool="agent.update", data={"agent": agent.model_dump(), "store_path": str(self.store.path)})
        except Exception as exc:
            return ToolResult(success=False, tool="agent.update", errors=[str(exc)])

    def _base_agent_definition(self, agent_id: str) -> AgentDefinition:
        resolved = self._registry().get(agent_id, include_deleted=True)
        return AgentDefinition(
            id=resolved.id,
            name=resolved.name,
            description=resolved.description,
            role=resolved.role,
            workflow=resolved.workflow,
            enabled=resolved.enabled,
            deleted=resolved.deleted,
            requires_llm=resolved.requires_llm,
            capabilities=list(resolved.capabilities),
            aliases=list(resolved.aliases),
            model=resolved.model.model_dump(exclude={"api_key_configured", "source"}),
            plugin_id=resolved.plugin_id,
            source="workspace",
        )

    def _patch(self, agent_id: str, updates: dict[str, Any], tool: str) -> ToolResult:
        try:
            base = self._base_agent_definition(agent_id)
            agent = self.store.patch(base.id, updates, base=base)
            errors = self.validator.validate(agent)
            if errors:
                return ToolResult(success=False, tool=tool, data=agent.model_dump(), errors=errors)
            resolved = self._registry().get(base.id, include_deleted=True)
            return ToolResult(success=True, tool=tool, data={"agent": resolved.model_dump(), "store_path": str(self.store.path)})
        except Exception as exc:
            return ToolResult(success=False, tool=tool, errors=[str(exc)])

    def enable(self, agent_id: str) -> ToolResult:
        return self._patch(agent_id, {"enabled": True, "deleted": False}, "agent.enable")

    def disable(self, agent_id: str) -> ToolResult:
        return self._patch(agent_id, {"enabled": False}, "agent.disable")

    def delete(self, agent_id: str) -> ToolResult:
        return self._patch(agent_id, {"enabled": False, "deleted": True}, "agent.delete")

    def validate(self, agent_id: str) -> ToolResult:
        try:
            resolved = self._registry().get(agent_id, include_deleted=True)
            agent = self._base_agent_definition(resolved.id)
            errors = self.validator.validate(agent)
            return ToolResult(
                success=not errors,
                tool="agent.validate",
                data={"agent": resolved.model_dump(), "valid": not errors, "errors": errors},
                errors=errors,
            )
        except Exception as exc:
            return ToolResult(success=False, tool="agent.validate", errors=[str(exc)])

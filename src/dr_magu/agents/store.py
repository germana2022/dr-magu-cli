from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from dr_magu.agents.loader import AgentConfigLoader
from dr_magu.agents.models import AgentDefinition


class WorkspaceAgentStore:
    """Stores user-managed workspace agent overrides in .dr-magu/agents/agents.yaml."""

    def __init__(self, workspace_path: str | Path) -> None:
        self.workspace_path = Path(workspace_path).resolve()
        self.path = AgentConfigLoader(self.workspace_path).workspace_agent_store_path

    def load_raw(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"agents": {}}
        with self.path.open("r", encoding="utf-8") as file:
            return yaml.safe_load(file) or {"agents": {}}

    def save_raw(self, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as file:
            yaml.safe_dump(payload, file, sort_keys=True, allow_unicode=True)

    def upsert(self, agent: AgentDefinition) -> None:
        payload = self.load_raw()
        agents = payload.setdefault("agents", {})
        agents[agent.id] = {
            "name": agent.name,
            "description": agent.description,
            "role": agent.role,
            "workflow": agent.workflow,
            "enabled": agent.enabled,
            "deleted": agent.deleted,
            "requires_llm": agent.requires_llm,
            "capabilities": list(agent.capabilities),
            "skills": list(getattr(agent, "skills", [])),
            "aliases": list(agent.aliases),
            "model": dict(agent.model),
            "plugin_id": agent.plugin_id,
            "source": "workspace",
        }
        self.save_raw(payload)

    def patch(self, agent_id: str, updates: dict[str, Any], base: AgentDefinition | None = None) -> AgentDefinition:
        payload = self.load_raw()
        agents = payload.setdefault("agents", {})
        current = agents.get(agent_id, {})
        if not current and base is not None:
            current = {
                "name": base.name,
                "description": base.description,
                "role": base.role,
                "workflow": base.workflow,
                "enabled": base.enabled,
                "deleted": base.deleted,
                "requires_llm": base.requires_llm,
                "capabilities": list(base.capabilities),
                "skills": list(getattr(base, "skills", [])),
                "aliases": list(base.aliases),
                "model": dict(base.model),
                "plugin_id": base.plugin_id,
                "source": "workspace",
            }
        if not current:
            raise KeyError(f"Agent '{agent_id}' does not exist and no base definition was provided.")
        current.update(updates)
        current["source"] = "workspace"
        agents[agent_id] = current
        self.save_raw(payload)
        return AgentDefinition(
            id=agent_id,
            name=str(current.get("name") or agent_id),
            description=str(current.get("description") or ""),
            role=str(current.get("role") or "general"),
            workflow=str(current.get("workflow") or ""),
            enabled=bool(current.get("enabled", True)),
            deleted=bool(current.get("deleted", False)),
            requires_llm=bool(current.get("requires_llm", False)),
            capabilities=list(current.get("capabilities", []) or []),
            skills=list(current.get("skills", []) or []),
            aliases=list(current.get("aliases", []) or []),
            model=dict(current.get("model", {}) or {}),
            plugin_id=str(current.get("plugin_id")) if current.get("plugin_id") else None,
            source="workspace",
        )

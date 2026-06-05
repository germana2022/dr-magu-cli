from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from dr_magu.agents.models import AgentDefinition
from dr_magu.plugins.loader import PluginLoader


class AgentConfigLoader:
    """Loads agent definitions from enabled plugins, project config, and workspace overrides.

    Precedence is intentionally ordered from least-specific to most-specific:
    enabled plugins -> project config -> workspace config -> workspace agent store.
    This allows a workspace to override, disable, or soft-delete plugin agents
    without modifying plugin files.
    """

    def __init__(self, workspace_path: str | Path, config_path: str | Path | None = None) -> None:
        self.workspace_path = Path(workspace_path).resolve()
        self.config_path = Path(config_path) if config_path else None

    @property
    def workspace_agent_store_path(self) -> Path:
        return self.workspace_path / ".dr-magu" / "agents" / "agents.yaml"

    def _candidate_paths(self) -> list[tuple[Path, str | None, str]]:
        candidates: list[tuple[Path, str | None, str]] = []

        for plugin in PluginLoader(self.workspace_path).load():
            if not plugin.enabled:
                continue
            candidates.append((Path(plugin.path) / "agents.yaml", plugin.id, "plugin"))

        candidates.append((Path("config/agents.yaml"), None, "project"))
        candidates.append((self.workspace_path / ".dr-magu" / "config" / "agents.yaml", None, "workspace"))
        candidates.append((self.workspace_agent_store_path, None, "workspace"))

        if self.config_path:
            candidates.append((self.config_path, None, "explicit"))

        return candidates

    def _load_yaml(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        with path.open("r", encoding="utf-8") as file:
            return yaml.safe_load(file) or {}

    def load_raw(self) -> dict[str, Any]:
        merged: dict[str, Any] = {"agents": {}}
        for path, _plugin_id, _source in self._candidate_paths():
            payload = self._load_yaml(path)
            raw_agents = payload.get("agents", {}) or {}
            merged["agents"].update(raw_agents)
        return merged

    def load(self) -> list[AgentDefinition]:
        agents_by_id: dict[str, AgentDefinition] = {}
        for path, plugin_id, source in self._candidate_paths():
            payload = self._load_yaml(path)
            raw_agents = (payload.get("agents", {}) or {})
            for agent_id, agent_payload in raw_agents.items():
                agent_payload = agent_payload or {}
                agents_by_id[str(agent_id)] = AgentDefinition(
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
                    plugin_id=str(agent_payload.get("plugin_id") or plugin_id) if (agent_payload.get("plugin_id") or plugin_id) else None,
                    source=str(agent_payload.get("source") or source),
                )
        return list(agents_by_id.values())

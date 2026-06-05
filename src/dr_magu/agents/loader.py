from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from dr_magu.agents.models import AgentDefinition
from dr_magu.plugins.loader import PluginLoader


class AgentConfigLoader:
    """Loads agent definitions from workspace, project, and enabled local plugins."""

    def __init__(self, workspace_path: str | Path, config_path: str | Path | None = None) -> None:
        self.workspace_path = Path(workspace_path).resolve()
        self.config_path = Path(config_path) if config_path else None

    def _candidate_paths(self) -> list[tuple[Path, str | None]]:
        candidates: list[tuple[Path, str | None]] = []
        if self.config_path:
            candidates.append((self.config_path, None))

        candidates.extend([
            (self.workspace_path / ".dr-magu" / "config" / "agents.yaml", None),
            (Path("config/agents.yaml"), None),
        ])

        for plugin in PluginLoader(self.workspace_path).load():
            if not plugin.enabled:
                continue
            agents_path = Path(plugin.path) / "agents.yaml"
            candidates.append((agents_path, plugin.id))

        return candidates

    def _load_yaml(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        with path.open("r", encoding="utf-8") as file:
            return yaml.safe_load(file) or {}

    def load_raw(self) -> dict[str, Any]:
        merged: dict[str, Any] = {"agents": {}}
        for path, _plugin_id in self._candidate_paths():
            payload = self._load_yaml(path)
            raw_agents = payload.get("agents", {}) or {}
            merged["agents"].update(raw_agents)
        return merged

    def load(self) -> list[AgentDefinition]:
        agents_by_id: dict[str, AgentDefinition] = {}
        for path, plugin_id in self._candidate_paths():
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
                    requires_llm=bool(agent_payload.get("requires_llm", False)),
                    capabilities=list(agent_payload.get("capabilities", []) or []),
                    aliases=list(agent_payload.get("aliases", []) or []),
                    model=dict(agent_payload.get("model", {}) or {}),
                    plugin_id=plugin_id,
                )
        return list(agents_by_id.values())

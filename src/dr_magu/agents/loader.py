from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from dr_magu.agents.models import AgentDefinition


class AgentConfigLoader:
    """Loads agent definitions from YAML without hardcoding agents in Python code."""

    def __init__(self, workspace_path: str | Path, config_path: str | Path | None = None) -> None:
        self.workspace_path = Path(workspace_path).resolve()
        self.config_path = Path(config_path) if config_path else None

    def _candidate_paths(self) -> list[Path]:
        candidates: list[Path] = []
        if self.config_path:
            candidates.append(self.config_path)
        candidates.extend([
            self.workspace_path / ".dr-magu" / "config" / "agents.yaml",
            Path("config/agents.yaml"),
        ])
        return candidates

    def load_raw(self) -> dict[str, Any]:
        for path in self._candidate_paths():
            if path.exists():
                with path.open("r", encoding="utf-8") as file:
                    return yaml.safe_load(file) or {}
        return {"agents": {}}

    def load(self) -> list[AgentDefinition]:
        raw_agents = (self.load_raw().get("agents", {}) or {})
        agents: list[AgentDefinition] = []
        for agent_id, payload in raw_agents.items():
            payload = payload or {}
            agents.append(AgentDefinition(
                id=str(agent_id),
                name=str(payload.get("name") or agent_id),
                description=str(payload.get("description") or ""),
                role=str(payload.get("role") or "general"),
                workflow=str(payload.get("workflow") or ""),
                enabled=bool(payload.get("enabled", True)),
                requires_llm=bool(payload.get("requires_llm", False)),
                capabilities=list(payload.get("capabilities", []) or []),
                aliases=list(payload.get("aliases", []) or []),
                model=dict(payload.get("model", {}) or {}),
            ))
        return agents

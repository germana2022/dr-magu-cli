from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class AgentSkillStore:
    """Persists workspace agent-to-skill bindings."""

    def __init__(self, workspace_path: str | Path) -> None:
        self.workspace_path = Path(workspace_path).resolve()
        self.path = self.workspace_path / ".dr-magu" / "skills" / "agent_skills.yaml"

    def load_raw(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"version": "2.7.0", "agents": {}}
        return yaml.safe_load(self.path.read_text(encoding="utf-8")) or {"version": "2.7.0", "agents": {}}

    def save_raw(self, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload.setdefault("version", "2.7.0")
        payload.setdefault("agents", {})
        self.path.write_text(yaml.safe_dump(payload, sort_keys=True, allow_unicode=True), encoding="utf-8")

    def get_skills(self, agent_id: str) -> list[str]:
        payload = self.load_raw()
        raw = (payload.get("agents", {}) or {}).get(agent_id, []) or []
        return list(dict.fromkeys(str(item) for item in raw))

    def set_skills(self, agent_id: str, skills: list[str]) -> list[str]:
        payload = self.load_raw()
        agents = payload.setdefault("agents", {})
        agents[agent_id] = list(dict.fromkeys(skills))
        self.save_raw(payload)
        return agents[agent_id]

    def attach(self, agent_id: str, skill_id: str) -> list[str]:
        skills = self.get_skills(agent_id)
        if skill_id not in skills:
            skills.append(skill_id)
        return self.set_skills(agent_id, skills)

    def detach(self, agent_id: str, skill_id: str) -> list[str]:
        return self.set_skills(agent_id, [skill for skill in self.get_skills(agent_id) if skill != skill_id])

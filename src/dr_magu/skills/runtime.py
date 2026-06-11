from __future__ import annotations

from pathlib import Path
from typing import Any

from dr_magu.agents.registry import AgentRegistry
from dr_magu.result import ToolResult
from dr_magu.skills.registry import SkillRegistry
from dr_magu.skills.store import AgentSkillStore


class SkillRuntime:
    """Operational Agent Skills Framework introduced in v2.7.0."""

    def __init__(self, workspace_path: str | Path) -> None:
        self.workspace_path = Path(workspace_path).resolve()
        self.registry = SkillRegistry(self.workspace_path)
        self.store = AgentSkillStore(self.workspace_path)
        self.agents = AgentRegistry(self.workspace_path)

    def list_skills(self, include_disabled: bool = True) -> ToolResult:
        skills = [skill.model_dump() for skill in self.registry.list(include_disabled=include_disabled)]
        return ToolResult(success=True, tool="skill.list", data={"skills": skills, "count": len(skills)})

    def show_skill(self, skill_id: str) -> ToolResult:
        try:
            skill = self.registry.get(skill_id, include_disabled=True)
            return ToolResult(success=True, tool="skill.show", data={"skill": skill.model_dump()})
        except Exception as exc:
            return ToolResult(success=False, tool="skill.show", errors=[str(exc)])

    def attach(self, agent_id: str, skill_id: str) -> ToolResult:
        try:
            agent = self.agents.get(agent_id)
            skill = self.registry.get(skill_id, include_disabled=False)
            skills = self.store.attach(agent.id, skill.id)
            return ToolResult(
                success=True,
                tool="skill.attach",
                data={
                    "agent_id": agent.id,
                    "skill_id": skill.id,
                    "skills": skills,
                    "skill": skill.model_dump(),
                    "store_path": str(self.store.path),
                },
            )
        except Exception as exc:
            return ToolResult(success=False, tool="skill.attach", errors=[str(exc)])

    def detach(self, agent_id: str, skill_id: str) -> ToolResult:
        try:
            agent = self.agents.get(agent_id, include_deleted=True)
            self.registry.get(skill_id, include_disabled=True)
            skills = self.store.detach(agent.id, skill_id)
            return ToolResult(
                success=True,
                tool="skill.detach",
                data={"agent_id": agent.id, "skill_id": skill_id, "skills": skills, "store_path": str(self.store.path)},
            )
        except Exception as exc:
            return ToolResult(success=False, tool="skill.detach", errors=[str(exc)])

    def agent_skills(self, agent_id: str, *, ensure_defaults: bool = True) -> ToolResult:
        try:
            agent = self.agents.get(agent_id, include_deleted=True)
            skills = self.store.get_skills(agent.id)
            if ensure_defaults and not skills:
                skills = self.registry.default_skills_for_role(agent.role)
                self.store.set_skills(agent.id, skills)
            resolved = []
            missing = []
            for skill_id in skills:
                try:
                    resolved.append(self.registry.get(skill_id, include_disabled=True).model_dump())
                except Exception:
                    missing.append(skill_id)
            aggregate = self._aggregate(resolved)
            return ToolResult(
                success=True,
                tool="agent.skills",
                data={
                    "agent_id": agent.id,
                    "agent": agent.model_dump(),
                    "skills": resolved,
                    "skill_ids": skills,
                    "missing_skills": missing,
                    "aggregate": aggregate,
                    "store_path": str(self.store.path),
                },
            )
        except Exception as exc:
            return ToolResult(success=False, tool="agent.skills", errors=[str(exc)])

    def bootstrap_agent_defaults(self, agent_id: str, role: str) -> list[str]:
        current = self.store.get_skills(agent_id)
        if current:
            return current
        defaults = self.registry.default_skills_for_role(role)
        return self.store.set_skills(agent_id, defaults)

    @staticmethod
    def _aggregate(skills: list[dict[str, Any]]) -> dict[str, list[str]]:
        capabilities: list[str] = []
        commands: list[str] = []
        mcp_servers: list[str] = []
        workflows: list[str] = []
        risk_levels: list[str] = []
        for skill in skills:
            capabilities.extend(skill.get("capabilities", []) or [])
            commands.extend(skill.get("commands", []) or [])
            mcp_servers.extend(skill.get("mcp_servers", []) or [])
            workflows.extend(skill.get("workflows", []) or [])
            risk_levels.append(str(skill.get("risk_level") or "low"))
        dedupe = lambda values: sorted(dict.fromkeys(str(item) for item in values if item))
        return {
            "capabilities": dedupe(capabilities),
            "commands": dedupe(commands),
            "mcp_servers": dedupe(mcp_servers),
            "workflows": dedupe(workflows),
            "risk_levels": dedupe(risk_levels),
        }

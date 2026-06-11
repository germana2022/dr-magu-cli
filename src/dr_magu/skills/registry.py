from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from dr_magu.skills.models import SkillDefinition


def _default_skills() -> list[SkillDefinition]:
    return [
        SkillDefinition(
            id="research",
            name="Research Skill",
            description="Collect structured research using configured MCP research providers.",
            category="research",
            capabilities=["research", "web_search", "provider_selection"],
            commands=["research.search", "mcp.test", "mcp.tools"],
            mcp_servers=["playwright", "brave-search"],
            workflows=["research-brief"],
            compatible_roles=["researcher", "general", "analyst"],
            requires_llm=False,
            risk_level="low",
        ),
        SkillDefinition(
            id="filesystem",
            name="Filesystem Skill",
            description="Inspect, read, search, and write workspace files within permission boundaries.",
            category="filesystem",
            capabilities=["filesystem", "files_read", "files_write", "workspace"],
            commands=["fs.list", "fs.read", "fs.write", "filesystem.search"],
            mcp_servers=["filesystem"],
            compatible_roles=["developer", "architect", "reviewer", "general"],
            risk_level="medium",
        ),
        SkillDefinition(
            id="github",
            name="GitHub Skill",
            description="Read repository metadata and prepare GitHub-oriented analysis.",
            category="repository",
            capabilities=["github", "repository", "pull_request", "issues"],
            commands=["repository.read", "git.status", "git.diff", "git.log"],
            mcp_servers=["github"],
            compatible_roles=["developer", "reviewer", "architect", "general"],
            risk_level="medium",
        ),
        SkillDefinition(
            id="documentation",
            name="Documentation Skill",
            description="Generate project context, summaries, and reusable technical documentation.",
            category="documentation",
            capabilities=["documentation", "project_context", "reporting"],
            commands=["context.generate", "context.show", "report.create", "report.from_research"],
            workflows=["repository.context"],
            compatible_roles=["documenter", "architect", "reporter", "general"],
            requires_llm=False,
            risk_level="low",
        ),
        SkillDefinition(
            id="architecture",
            name="Architecture Skill",
            description="Analyze systems and produce architecture-oriented context and decisions.",
            category="architecture",
            capabilities=["architecture", "analysis", "workflow"],
            commands=["workflow.engine.plan", "workflow.engine.run", "context.generate"],
            workflows=["repository.context", "research-brief"],
            compatible_roles=["architect", "reviewer", "general"],
            requires_llm=False,
            risk_level="low",
        ),
        SkillDefinition(
            id="code-review",
            name="Code Review Skill",
            description="Inspect diffs, repository structure, and risk indicators for code review tasks.",
            category="quality",
            capabilities=["code_review", "git", "filesystem", "analysis"],
            commands=["git.diff", "git.status", "search.code", "fs.read"],
            compatible_roles=["reviewer", "developer", "security", "general"],
            risk_level="medium",
        ),
        SkillDefinition(
            id="report",
            name="Report Skill",
            description="Create persisted Markdown, HTML, and JSON report artifacts from runtime outputs.",
            category="reporting",
            capabilities=["reporting", "artifact_generation"],
            commands=["report.create", "report.from_research"],
            compatible_roles=["reporter", "documenter", "general"],
            risk_level="low",
        ),
        SkillDefinition(
            id="workflow",
            name="Workflow Skill",
            description="Plan, run, inspect, resume, cancel, and export workflow executions.",
            category="workflow",
            capabilities=["workflow", "orchestration", "runtime"],
            commands=["workflow.engine.list", "workflow.engine.run", "workflow.runtime.inspect", "workflow.runtime.resume", "workflow.runtime.cancel"],
            compatible_roles=["orchestrator", "architect", "general"],
            risk_level="medium",
        ),
        SkillDefinition(
            id="mcp",
            name="MCP Skill",
            description="Operate MCP servers, diagnostics, tool discovery, and direct tool validation.",
            category="mcp",
            capabilities=["mcp", "tools", "diagnostics"],
            commands=["mcp.servers", "mcp.status", "mcp.tools", "mcp.test", "mcp.diagnose"],
            compatible_roles=["operator", "developer", "general"],
            risk_level="medium",
        ),
    ]


class SkillRegistry:
    """Loads built-in and workspace-defined skills."""

    def __init__(self, workspace_path: str | Path) -> None:
        self.workspace_path = Path(workspace_path).resolve()
        self.workspace_skills_path = self.workspace_path / ".dr-magu" / "skills" / "skills.yaml"
        self._skills = self._load()

    def _load_workspace(self) -> list[SkillDefinition]:
        if not self.workspace_skills_path.exists():
            return []
        payload = yaml.safe_load(self.workspace_skills_path.read_text(encoding="utf-8")) or {}
        raw_skills = payload.get("skills", {}) or {}
        skills: list[SkillDefinition] = []
        for skill_id, raw in raw_skills.items():
            raw = raw or {}
            skills.append(
                SkillDefinition(
                    id=str(skill_id),
                    name=str(raw.get("name") or skill_id),
                    description=str(raw.get("description") or ""),
                    category=str(raw.get("category") or "custom"),
                    capabilities=list(raw.get("capabilities", []) or []),
                    commands=list(raw.get("commands", []) or []),
                    mcp_servers=list(raw.get("mcp_servers", []) or []),
                    workflows=list(raw.get("workflows", []) or []),
                    compatible_roles=list(raw.get("compatible_roles", []) or []),
                    requires_llm=bool(raw.get("requires_llm", False)),
                    risk_level=str(raw.get("risk_level") or "medium"),
                    enabled=bool(raw.get("enabled", True)),
                )
            )
        return skills

    def _load(self) -> dict[str, SkillDefinition]:
        skills = {skill.id: skill for skill in _default_skills()}
        for skill in self._load_workspace():
            skills[skill.id] = skill
        return skills

    def list(self, include_disabled: bool = True) -> list[SkillDefinition]:
        values = list(self._skills.values())
        if not include_disabled:
            values = [skill for skill in values if skill.enabled]
        return sorted(values, key=lambda skill: skill.id)

    def get(self, skill_id: str, include_disabled: bool = True) -> SkillDefinition:
        if skill_id not in self._skills:
            available = ", ".join(sorted(self._skills)) or "none"
            raise KeyError(f"Unknown skill '{skill_id}'. Available skills: {available}")
        skill = self._skills[skill_id]
        if not include_disabled and not skill.enabled:
            raise KeyError(f"Skill '{skill_id}' is disabled.")
        return skill

    def default_skills_for_role(self, role: str) -> list[str]:
        role = (role or "general").lower()
        defaults: dict[str, list[str]] = {
            "researcher": ["research", "mcp", "report"],
            "architect": ["architecture", "documentation", "filesystem", "research"],
            "reviewer": ["code-review", "filesystem", "github", "report"],
            "developer": ["filesystem", "github", "workflow", "mcp"],
            "reporter": ["report", "documentation", "research"],
            "security": ["code-review", "filesystem", "github"],
            "general": ["research", "workflow", "mcp"],
        }
        return list(defaults.get(role, defaults["general"]))

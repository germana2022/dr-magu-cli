from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from dr_magu.agents.runner import AgentRunner
from dr_magu.mcp_runtime.registry import MCPServerRegistry
from dr_magu.multi_agent.team import TeamRuntime
from dr_magu.result import ToolResult
from dr_magu.skills.runtime import SkillRuntime
from dr_magu.workflow_engine.engine import WorkflowEngine


@dataclass(frozen=True)
class BootstrapDefaultAgent:
    id: str
    role: str
    workflow: str
    skills: list[str]
    capabilities: list[str]
    description: str


DEFAULT_AGENTS: list[BootstrapDefaultAgent] = [
    BootstrapDefaultAgent(
        id="researcher",
        role="researcher",
        workflow="research-brief",
        skills=["research", "mcp", "report"],
        capabilities=["workflow", "mcp", "context", "research"],
        description="Collects structured research using the configured MCP research providers.",
    ),
    BootstrapDefaultAgent(
        id="architect",
        role="architect",
        workflow="repository-context",
        skills=["architecture", "documentation", "filesystem", "research"],
        capabilities=["workflow", "filesystem", "architecture", "context"],
        description="Analyzes repository structure and produces architecture-oriented context.",
    ),
    BootstrapDefaultAgent(
        id="reviewer",
        role="reviewer",
        workflow="repository-context",
        skills=["code-review", "filesystem", "github", "report"],
        capabilities=["workflow", "filesystem", "github", "code_review"],
        description="Reviews repository structure, diffs, risks, and quality indicators.",
    ),
    BootstrapDefaultAgent(
        id="reporter",
        role="reporter",
        workflow="research-brief",
        skills=["report", "documentation", "research"],
        capabilities=["workflow", "reporting", "documentation", "context"],
        description="Produces concise technical reports from workflow and research outputs.",
    ),
]

DEFAULT_TEAMS: dict[str, list[str]] = {
    "repo-analysis": ["researcher", "architect", "reviewer", "reporter"],
    "research-team": ["researcher", "reporter"],
}


class WorkspaceBootstrap:
    """Bootstrap a ready-to-use dr-magu workspace.

    v2.9.0 turns an empty folder into an operational AI OS workspace with
    default MCP configuration, agents, skills, workflows, teams, runtime
    folders, and diagnostics.
    """

    def __init__(self, workspace_path: str | Path = ".") -> None:
        self.workspace_path = Path(workspace_path).resolve()
        self.root = self.workspace_path / ".dr-magu"

    def init(self, *, force: bool = False, enable_safe_mcp: bool = True) -> ToolResult:
        created: list[str] = []
        updated: list[str] = []
        skipped: list[str] = []
        errors: list[str] = []

        for directory in self._directories():
            if not directory.exists():
                directory.mkdir(parents=True, exist_ok=True)
                created.append(str(directory))
            else:
                skipped.append(str(directory))

        env_result = self._write_env_example(force=force)
        self._record_file_result(env_result, created, updated, skipped)

        try:
            mcp_path = self._bootstrap_mcp_config(force=force, enable_safe_mcp=enable_safe_mcp)
            if force or not mcp_path.exists():
                created.append(str(mcp_path))
            else:
                updated.append(str(mcp_path))
        except Exception as exc:  # pragma: no cover - defensive diagnostics
            errors.append(f"MCP config bootstrap failed: {exc}")

        for workflow_result in self._write_workflow_templates(force=force):
            self._record_file_result(workflow_result, created, updated, skipped)

        agent_results: list[dict[str, Any]] = []
        for agent in DEFAULT_AGENTS:
            result = self._ensure_agent(agent, force=force)
            agent_results.append(self._compact_result(result))
            if result.success:
                updated.append(f"agent:{agent.id}")
            else:
                if "already exists" in "; ".join(result.errors).lower():
                    skipped.append(f"agent:{agent.id}")
                else:
                    errors.extend(result.errors)

        skill_results: list[dict[str, Any]] = []
        for agent in DEFAULT_AGENTS:
            for skill_id in agent.skills:
                result = SkillRuntime(self.workspace_path).attach(agent.id, skill_id)
                skill_results.append(self._compact_result(result))
                if not result.success:
                    errors.extend(result.errors)

        team_results: list[dict[str, Any]] = []
        for team_id, agents in DEFAULT_TEAMS.items():
            result = self._ensure_team(team_id, agents, force=force)
            team_results.append(self._compact_result(result))
            if not result.success:
                errors.extend(result.errors)

        manifest_path = self._write_manifest(force=True)
        updated.append(str(manifest_path))

        doctor = self.doctor()
        data = {
            "version": "2.9.0",
            "workspace": str(self.workspace_path),
            "root": str(self.root),
            "created": created,
            "updated": updated,
            "skipped": skipped,
            "agents": agent_results,
            "skills": skill_results,
            "teams": team_results,
            "doctor": doctor.data,
            "next_commands": [
                "dr-magu doctor",
                "dr-magu team list",
                "dr-magu team show repo-analysis",
                "dr-magu team run repo-analysis \"Analyze this repository\" --dry-run",
            ],
        }
        return ToolResult(success=not errors, tool="workspace.init", data=data, errors=errors)

    def doctor(self) -> ToolResult:
        checks: list[dict[str, Any]] = []

        def add_check(name: str, ok: bool, message: str, path: Path | None = None) -> None:
            checks.append({"name": name, "ok": ok, "message": message, "path": str(path) if path else None})

        add_check("workspace.exists", self.workspace_path.exists(), "Workspace path exists.", self.workspace_path)
        add_check("dr_magu.root", self.root.exists(), ".dr-magu root exists.", self.root)
        for directory in self._directories():
            add_check(f"dir.{directory.relative_to(self.workspace_path).as_posix()}", directory.exists(), "Required workspace directory exists.", directory)

        mcp_path = MCPServerRegistry(self.workspace_path).config_path()
        add_check("mcp.config", mcp_path.exists(), "MCP server configuration exists.", mcp_path)
        if mcp_path.exists():
            try:
                servers = MCPServerRegistry(self.workspace_path).list_servers()
                enabled = [server.id for server in servers if server.enabled]
                add_check("mcp.safe_defaults", {"playwright", "filesystem"}.issubset(set(enabled)), f"Enabled MCP servers: {enabled}", mcp_path)
            except Exception as exc:
                add_check("mcp.config.parse", False, f"Could not parse MCP configuration: {exc}", mcp_path)

        agent_runner = AgentRunner(self.workspace_path)
        agents_result = agent_runner.list_agents()
        agents = (agents_result.data or {}).get("agents", []) if agents_result.success else []
        agent_ids = {agent.get("id") for agent in agents}
        for agent_id in [agent.id for agent in DEFAULT_AGENTS]:
            add_check(f"agent.{agent_id}", agent_id in agent_ids, f"Default agent '{agent_id}' is configured.")

        skill_runtime = SkillRuntime(self.workspace_path)
        for agent in DEFAULT_AGENTS:
            try:
                skill_result = skill_runtime.agent_skills(agent.id)
                actual = set(((skill_result.data or {}).get("skill_ids") or [])) if skill_result.success else set()
                add_check(f"skills.{agent.id}", set(agent.skills).issubset(actual), f"Agent '{agent.id}' has default skills: {sorted(actual)}")
            except Exception as exc:
                add_check(f"skills.{agent.id}", False, f"Skill check failed: {exc}")

        team_runtime = TeamRuntime(self.workspace_path)
        team_list = team_runtime.list()
        teams = (team_list.data or {}).get("teams", []) if team_list.success else []
        team_ids = {team.get("id") for team in teams}
        for team_id in DEFAULT_TEAMS:
            add_check(f"team.{team_id}", team_id in team_ids, f"Default team '{team_id}' is configured.")

        workflow_ids = {definition.id for definition in WorkflowEngine(self.workspace_path).list_definitions()}
        for workflow_id in ["research-brief", "repository-context", "repo-analysis"]:
            add_check(f"workflow.{workflow_id}", workflow_id in workflow_ids, f"Workflow '{workflow_id}' is available.")

        ok = all(check["ok"] for check in checks)
        return ToolResult(
            success=ok,
            tool="workspace.doctor",
            data={
                "version": "2.9.0",
                "workspace": str(self.workspace_path),
                "ok": ok,
                "checks": checks,
                "summary": {"total": len(checks), "passed": len([item for item in checks if item["ok"]]), "failed": len([item for item in checks if not item["ok"]])},
            },
            errors=[] if ok else ["Workspace bootstrap validation failed."],
        )

    def _directories(self) -> list[Path]:
        return [
            self.root,
            self.root / "config",
            self.root / "agents",
            self.root / "agent-runtime" / "runs",
            self.root / "skills",
            self.root / "teams" / "runs",
            self.root / "workflows",
            self.root / "workflow-runs",
            self.root / "mcp_runtime" / "logs",
            self.root / "research",
            self.root / "reports",
            self.workspace_path / "outputs",
            self.workspace_path / "logs",
            self.workspace_path / "workspaces",
        ]

    def _write_env_example(self, *, force: bool) -> dict[str, Any]:
        path = self.workspace_path / ".env.example"
        content = """# dr-magu workspace configuration
LLM_PROVIDER=opencode
LLM_MODEL=deepseek-v4-flash

# Optional provider credentials
OPENAI_API_KEY=
GITHUB_TOKEN=
BRAVE_API_KEY=

# Workspace and MCP defaults
DR_MAGU_HOME=.dr-magu
MCP_PLAYWRIGHT_ENABLED=true
MCP_FILESYSTEM_ENABLED=true
MCP_GITHUB_ENABLED=false
MCP_BRAVE_SEARCH_ENABLED=false
"""
        return self._write_text(path, content, force=force)

    def _bootstrap_mcp_config(self, *, force: bool, enable_safe_mcp: bool) -> Path:
        registry = MCPServerRegistry(self.workspace_path)
        path = registry.initialize_config(overwrite=force)
        servers = registry.list_servers()
        if enable_safe_mcp:
            servers = [server.with_enabled(server.id in {"playwright", "filesystem"} or server.enabled) for server in servers]
            registry.save_servers(servers)
        return path

    def _write_workflow_templates(self, *, force: bool) -> list[dict[str, Any]]:
        workflows = {
            "repo-analysis.yaml": {
                "id": "repo-analysis",
                "name": "Repository Analysis",
                "description": "Run repository context generation and a research brief as a bootstrap multi-agent workflow template.",
                "version": "2.9.0",
                "tags": ["repository", "analysis", "bootstrap"],
                "inputs": {"topic": "Repository or objective to analyze"},
                "steps": [
                    {"id": "repository-context", "name": "Generate Repository Context", "type": "command", "command": "context.generate", "description": "Generate deterministic project context.", "output_key": "repository_context"},
                    {"id": "research-brief", "name": "Collect Research", "type": "command", "command": "research.search ${topic} --provider auto --allow-fallback", "description": "Collect research for the requested objective.", "continue_on_error": True, "output_key": "research"},
                ],
            },
            "security-review.yaml": {
                "id": "security-review",
                "name": "Security Review",
                "description": "Bootstrap security-oriented repository review template.",
                "version": "2.9.0",
                "tags": ["security", "repository", "review"],
                "steps": [
                    {"id": "repo-scan", "name": "Scan Repository", "type": "command", "command": "repo.scan .", "description": "Scan repository metadata.", "output_key": "repo_scan"},
                    {"id": "git-status", "name": "Git Status", "type": "command", "command": "git.status", "description": "Collect git status.", "continue_on_error": True, "output_key": "git_status"},
                ],
            },
        }
        results: list[dict[str, Any]] = []
        target_dir = self.root / "workflows"
        target_dir.mkdir(parents=True, exist_ok=True)
        for filename, payload in workflows.items():
            results.append(self._write_text(target_dir / filename, yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), force=force))
        return results

    def _ensure_agent(self, agent: BootstrapDefaultAgent, *, force: bool) -> ToolResult:
        runner = AgentRunner(self.workspace_path)
        try:
            existing = runner.show_agent(agent.id)
        except Exception:
            existing = ToolResult(success=False, tool="agent.show", errors=["not found"])
        if existing.success and not force:
            return ToolResult(success=True, tool="agent.create", data={"agent": existing.data, "skipped": True})
        if existing.success and force:
            runner.delete_agent(agent.id)
        return runner.create_agent(
            agent.id,
            name=agent.id.replace("-", " ").title(),
            role=agent.role,
            workflow=agent.workflow,
            description=agent.description,
            capabilities=agent.capabilities,
            skills=agent.skills,
            requires_llm=False,
        )

    def _ensure_team(self, team_id: str, agents: list[str], *, force: bool) -> ToolResult:
        runtime = TeamRuntime(self.workspace_path)
        existing = runtime.show(team_id)
        if existing.success and force:
            runtime.delete(team_id)
            existing = ToolResult(success=False, tool="team.show", errors=["deleted for force recreation"])
        if not existing.success:
            created = runtime.create(team_id, mode="sequential", description=f"Bootstrap team for {team_id}.")
            if not created.success:
                return created
        added: list[dict[str, Any]] = []
        errors: list[str] = []
        for agent_id in agents:
            result = runtime.add(team_id, agent_id)
            added.append(self._compact_result(result))
            if not result.success:
                errors.extend(result.errors)
        show = runtime.show(team_id)
        return ToolResult(success=not errors and show.success, tool="team.bootstrap", data={"team_id": team_id, "agents": agents, "added": added, "team": show.data}, errors=errors + show.errors)

    def _write_manifest(self, *, force: bool) -> Path:
        path = self.root / "bootstrap.json"
        payload = {
            "version": "2.9.0",
            "workspace": str(self.workspace_path),
            "default_agents": [agent.id for agent in DEFAULT_AGENTS],
            "default_teams": DEFAULT_TEAMS,
            "default_workflows": ["research-brief", "repository-context", "repo-analysis", "security-review"],
            "recommended_next_commands": ["dr-magu doctor", "dr-magu team run repo-analysis \"Analyze this repository\" --dry-run"],
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        if force or not path.exists():
            path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return path

    @staticmethod
    def _compact_result(result: ToolResult) -> dict[str, Any]:
        return {"success": result.success, "tool": result.tool, "errors": result.errors, "data": result.data or {}}

    @staticmethod
    def _record_file_result(result: dict[str, Any], created: list[str], updated: list[str], skipped: list[str]) -> None:
        if result["status"] == "created":
            created.append(result["path"])
        elif result["status"] == "updated":
            updated.append(result["path"])
        else:
            skipped.append(result["path"])

    @staticmethod
    def _write_text(path: Path, content: str, *, force: bool) -> dict[str, Any]:
        existed = path.exists()
        if existed and not force:
            return {"path": str(path), "status": "skipped"}
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return {"path": str(path), "status": "updated" if existed else "created"}

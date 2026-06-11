from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from dr_magu.agents.manager import AgentManager
from dr_magu.agents.models import AgentDefinition, ResolvedAgentDefinition
from dr_magu.agents.registry import AgentRegistry
from dr_magu.agents.store import WorkspaceAgentStore
from dr_magu.result import ToolResult
from dr_magu.workflow_engine.runner import WorkflowRunner as WorkflowEngineRunner
from dr_magu.skills.runtime import SkillRuntime
from dr_magu.workflows.runner import WorkflowRunner as LegacyWorkflowRunner


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class AgentRuntimeStore:
    """Persists observable agent runtime state and execution history."""

    def __init__(self, workspace_path: str | Path) -> None:
        self.workspace_path = Path(workspace_path).resolve()
        self.root = self.workspace_path / ".dr-magu" / "agent-runtime"
        self.runs_dir = self.root / "runs"
        self.state_path = self.root / "state.json"

    def _ensure(self) -> None:
        self.runs_dir.mkdir(parents=True, exist_ok=True)

    def load_state(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return {"version": "2.7.0", "agents": {}}
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def save_state(self, state: dict[str, Any]) -> None:
        self._ensure()
        state.setdefault("version", "2.7.0")
        self.state_path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")

    def update_agent_state(self, agent_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        state = self.load_state()
        agents = state.setdefault("agents", {})
        current = agents.setdefault(agent_id, {"status": "idle", "updated_at": _utc_now()})
        current.update(updates)
        current["updated_at"] = _utc_now()
        agents[agent_id] = current
        self.save_state(state)
        return current

    def agent_state(self, agent_id: str) -> dict[str, Any]:
        state = self.load_state()
        return dict(state.get("agents", {}).get(agent_id, {"status": "idle"}))

    def save_run(self, record: dict[str, Any]) -> Path:
        self._ensure()
        path = self.runs_dir / f"{record['run_id']}.json"
        path.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")
        return path

    def list_runs(self, agent_id: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        if not self.runs_dir.exists():
            return []
        runs: list[dict[str, Any]] = []
        for path in sorted(self.runs_dir.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if agent_id and record.get("agent_id") != agent_id:
                continue
            runs.append(record)
            if len(runs) >= limit:
                break
        return runs


class AgentRuntime:
    """Operational Agent Runtime introduced in v2.7.0.

    The runtime promotes the existing agent registry into an observable execution
    boundary with direct create/run/status/stop operations, persisted runtime
    state, execution history, workflow access and MCP capability metadata.
    """

    def __init__(self, workspace_path: str | Path) -> None:
        self.workspace_path = Path(workspace_path).resolve()
        self.registry = AgentRegistry(self.workspace_path)
        self.manager = AgentManager(self.workspace_path)
        self.runtime_store = AgentRuntimeStore(self.workspace_path)
        self.workspace_store = WorkspaceAgentStore(self.workspace_path)
        self.skill_runtime = SkillRuntime(self.workspace_path)

    def _registry(self) -> AgentRegistry:
        return AgentRegistry(self.workspace_path)

    def create(
        self,
        agent_id: str,
        *,
        name: str | None = None,
        role: str = "general",
        workflow: str = "research-brief",
        description: str = "",
        capabilities: list[str] | None = None,
        skills: list[str] | None = None,
        aliases: list[str] | None = None,
        requires_llm: bool = False,
    ) -> ToolResult:
        agent_id = agent_id.strip()
        if not agent_id:
            return ToolResult(success=False, tool="agent.create", errors=["Agent id is required."])
        try:
            self._registry().get(agent_id, include_deleted=True)
            return ToolResult(success=False, tool="agent.create", errors=[f"Agent '{agent_id}' already exists."])
        except KeyError:
            pass

        agent = AgentDefinition(
            id=agent_id,
            name=name or agent_id.replace("-", " ").title(),
            description=description or f"Workspace-managed {role} agent.",
            role=role,
            workflow=workflow,
            enabled=True,
            deleted=False,
            requires_llm=requires_llm,
            capabilities=capabilities or self._default_capabilities(role),
            skills=skills or self.skill_runtime.registry.default_skills_for_role(role),
            aliases=aliases or [],
            model={},
            source="workspace",
        )
        errors = self.manager.validator.validate(agent)
        if errors:
            return ToolResult(success=False, tool="agent.create", data={"agent": agent.model_dump()}, errors=errors)
        self.workspace_store.upsert(agent)
        self.skill_runtime.bootstrap_agent_defaults(agent.id, agent.role)
        self.runtime_store.update_agent_state(
            agent.id,
            {
                "status": "idle",
                "created_at": _utc_now(),
                "last_run_id": None,
                "last_result": None,
            },
        )
        resolved = AgentRegistry(self.workspace_path).get(agent.id, include_deleted=True)
        return ToolResult(
            success=True,
            tool="agent.create",
            data={
                "agent": resolved.model_dump(),
                "runtime_state": self.runtime_store.agent_state(agent.id),
                "store_path": str(self.workspace_store.path),
                "state_path": str(self.runtime_store.state_path),
            },
        )

    def run(self, agent_id: str, prompt: str = "", *, dry_run: bool = False) -> ToolResult:
        try:
            agent = self._registry().get(agent_id)
        except Exception as exc:
            return ToolResult(success=False, tool="agent.run", errors=[str(exc)])
        if agent.deleted:
            return ToolResult(success=False, tool="agent.run", errors=[f"Agent '{agent.id}' is deleted."])
        if not agent.enabled:
            return ToolResult(success=False, tool="agent.run", errors=[f"Agent '{agent.id}' is disabled."])

        run_id = f"agent-run-{uuid4().hex[:12]}"
        started_at = _utc_now()
        self.runtime_store.update_agent_state(
            agent.id,
            {"status": "running", "current_run_id": run_id, "last_prompt": prompt, "started_at": started_at},
        )
        started = time.perf_counter()
        result = self._run_bound_workflow(agent, prompt, dry_run=dry_run)
        duration_ms = int((time.perf_counter() - started) * 1000)
        completed_at = _utc_now()
        status = "completed" if result.success else "failed"
        workflow_run_id = None
        if isinstance(result.data, dict):
            workflow_run_id = result.data.get("run_id")

        record = {
            "run_id": run_id,
            "agent_id": agent.id,
            "agent_name": agent.name,
            "role": agent.role,
            "workflow": agent.workflow,
            "workflow_run_id": workflow_run_id,
            "prompt": prompt,
            "dry_run": dry_run,
            "status": status,
            "success": result.success,
            "tool": result.tool,
            "errors": result.errors,
            "started_at": started_at,
            "completed_at": completed_at,
            "duration_ms": duration_ms,
        }
        run_path = self.runtime_store.save_run(record)
        self.runtime_store.update_agent_state(
            agent.id,
            {
                "status": status,
                "current_run_id": None,
                "last_run_id": run_id,
                "last_workflow_run_id": workflow_run_id,
                "last_result": "success" if result.success else "error",
                "last_error": "; ".join(result.errors) if result.errors else None,
                "completed_at": completed_at,
            },
        )
        data = {
            "agent": agent.model_dump(),
            "agent_run": record,
            "workflow_result": result.data or {},
            "workflow_success": result.success,
            "run_path": str(run_path),
            "state_path": str(self.runtime_store.state_path),
        }
        return ToolResult(success=result.success, tool="agent.run", data=data, errors=result.errors)

    def stop(self, agent_id: str, reason: str = "Manual stop requested.") -> ToolResult:
        try:
            agent = self._registry().get(agent_id, include_deleted=True)
        except Exception as exc:
            return ToolResult(success=False, tool="agent.stop", errors=[str(exc)])
        state = self.runtime_store.agent_state(agent.id)
        was_running = state.get("status") == "running"
        updated = self.runtime_store.update_agent_state(
            agent.id,
            {
                "status": "stopped",
                "current_run_id": None,
                "stop_requested": True,
                "stop_reason": reason,
                "stopped_at": _utc_now(),
            },
        )
        return ToolResult(
            success=True,
            tool="agent.stop",
            data={"agent": agent.model_dump(), "was_running": was_running, "runtime_state": updated},
        )

    def status(self, agent_id: str) -> ToolResult:
        try:
            agent = self._registry().get(agent_id, include_deleted=True)
        except Exception as exc:
            return ToolResult(success=False, tool="agent.status", errors=[str(exc)])
        skill_result = self.skill_runtime.agent_skills(agent.id)
        skill_data = skill_result.data if skill_result.success else {"skills": [], "aggregate": {}}
        return ToolResult(
            success=True,
            tool="agent.status",
            data={
                "agent": agent.model_dump(),
                "runtime_state": self.runtime_store.agent_state(agent.id),
                "skills": skill_data,
                "permissions": self._permissions(agent, skill_data),
                "mcp_access": self._mcp_access(agent, skill_data),
                "latest_runs": self.runtime_store.list_runs(agent.id, limit=5),
                "state_path": str(self.runtime_store.state_path),
            },
        )

    def history(self, agent_id: str | None = None, limit: int = 20) -> ToolResult:
        return ToolResult(
            success=True,
            tool="agent.history",
            data={"agent_id": agent_id, "count": len(self.runtime_store.list_runs(agent_id, limit)), "runs": self.runtime_store.list_runs(agent_id, limit)},
        )

    def context(self, agent_id: str) -> ToolResult:
        try:
            agent = self._registry().get(agent_id, include_deleted=True)
        except Exception as exc:
            return ToolResult(success=False, tool="agent.context", errors=[str(exc)])
        skill_result = self.skill_runtime.agent_skills(agent.id)
        skill_data = skill_result.data if skill_result.success else {"skills": [], "aggregate": {}}
        return ToolResult(
            success=True,
            tool="agent.context",
            data={
                "agent": agent.model_dump(),
                "runtime_state": self.runtime_store.agent_state(agent.id),
                "workflow": agent.workflow,
                "capabilities": agent.capabilities,
                "skills": skill_data,
                "permissions": self._permissions(agent, skill_data),
                "mcp_access": self._mcp_access(agent, skill_data),
                "workflow_access": {"can_run_workflow": True, "bound_workflow": agent.workflow},
            },
        )

    def _run_bound_workflow(self, agent: ResolvedAgentDefinition, prompt: str, *, dry_run: bool = False) -> ToolResult:
        # Prefer the v2.5 Workflow Orchestration Engine. Fall back to the legacy
        # workflow runner for existing repository.context agents.
        topic = prompt.strip()
        variables = {"topic": topic, "prompt": topic} if topic else {}
        workflow_id = agent.workflow
        try:
            return WorkflowEngineRunner(self.workspace_path).run(workflow_id, topic=topic, variables=variables, dry_run=dry_run)
        except Exception:
            return LegacyWorkflowRunner(str(self.workspace_path)).run(workflow_id)

    def _default_capabilities(self, role: str) -> list[str]:
        normalized = role.lower().strip()
        if "research" in normalized:
            return ["research", "mcp:playwright", "mcp:brave-search", "workflow:research-brief"]
        if "architect" in normalized:
            return ["architecture", "research", "workflow:website-builder"]
        if "review" in normalized:
            return ["review", "filesystem", "github"]
        return ["workflow", "mcp", "context"]

    def _permissions(self, agent: ResolvedAgentDefinition, skill_data: dict[str, Any] | None = None) -> dict[str, Any]:
        skill_capabilities = ((skill_data or {}).get("aggregate", {}) or {}).get("capabilities", [])
        capabilities = set(agent.capabilities) | set(skill_capabilities)
        return {
            "can_use_mcp": any(item.startswith("mcp") or item in {"research", "filesystem", "github"} for item in capabilities),
            "can_run_workflows": True,
            "can_use_llm": bool(agent.requires_llm),
            "can_write_files": "filesystem.write" in capabilities or "write" in capabilities,
            "source": "agent-runtime-defaults",
        }

    def _mcp_access(self, agent: ResolvedAgentDefinition, skill_data: dict[str, Any] | None = None) -> dict[str, Any]:
        aggregate = ((skill_data or {}).get("aggregate", {}) or {})
        capabilities = set(agent.capabilities) | set(aggregate.get("capabilities", []) or [])
        providers: list[str] = list(aggregate.get("mcp_servers", []) or [])
        for capability in capabilities:
            if capability.startswith("mcp:"):
                providers.append(capability.split(":", 1)[1])
        if "research" in capabilities and not providers:
            providers.extend(["playwright", "brave-search"])
        if "filesystem" in capabilities:
            providers.append("filesystem")
        if "github" in capabilities:
            providers.append("github")
        return {"enabled": bool(providers), "providers": sorted(set(providers))}

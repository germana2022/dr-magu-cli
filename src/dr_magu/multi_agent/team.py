from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml

from dr_magu.agents.registry import AgentRegistry
from dr_magu.agents.runner import AgentRunner
from dr_magu.result import ToolResult
from dr_magu.multi_agent.artifacts import TeamArtifactStore


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class TeamDefinition:
    """Workspace-managed multi-agent team definition."""

    id: str
    name: str
    description: str = "Workspace-managed multi-agent team."
    agents: list[str] = field(default_factory=list)
    mode: str = "sequential"
    enabled: bool = True
    deleted: bool = False
    source: str = "workspace"
    created_at: str = field(default_factory=_utc_now)
    updated_at: str = field(default_factory=_utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "agents": list(self.agents),
            "mode": self.mode,
            "enabled": self.enabled,
            "deleted": self.deleted,
            "source": self.source,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, team_id: str, payload: dict[str, Any]) -> "TeamDefinition":
        return cls(
            id=team_id,
            name=str(payload.get("name") or team_id.replace("-", " ").title()),
            description=str(payload.get("description") or "Workspace-managed multi-agent team."),
            agents=list(payload.get("agents") or []),
            mode=str(payload.get("mode") or "sequential"),
            enabled=bool(payload.get("enabled", True)),
            deleted=bool(payload.get("deleted", False)),
            source=str(payload.get("source") or "workspace"),
            created_at=str(payload.get("created_at") or _utc_now()),
            updated_at=str(payload.get("updated_at") or _utc_now()),
        )


class TeamStore:
    """Persists teams and multi-agent run history under .dr-magu."""

    def __init__(self, workspace_path: str | Path) -> None:
        self.workspace_path = Path(workspace_path).resolve()
        self.root = self.workspace_path / ".dr-magu" / "teams"
        self.path = self.root / "teams.yaml"
        self.runs_dir = self.root / "runs"
        self.state_path = self.root / "state.json"

    def _ensure(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self.runs_dir.mkdir(parents=True, exist_ok=True)

    def load_raw(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"teams": {}}
        with self.path.open("r", encoding="utf-8") as file:
            return yaml.safe_load(file) or {"teams": {}}

    def save_raw(self, payload: dict[str, Any]) -> None:
        self._ensure()
        with self.path.open("w", encoding="utf-8") as file:
            yaml.safe_dump(payload, file, sort_keys=True, allow_unicode=True)

    def list(self, include_disabled: bool = True, include_deleted: bool = False) -> list[TeamDefinition]:
        payload = self.load_raw()
        teams: list[TeamDefinition] = []
        for team_id, raw in sorted((payload.get("teams") or {}).items()):
            team = TeamDefinition.from_dict(team_id, raw or {})
            if team.deleted and not include_deleted:
                continue
            if not team.enabled and not include_disabled:
                continue
            teams.append(team)
        return teams

    def get(self, team_id: str, include_deleted: bool = False) -> TeamDefinition:
        payload = self.load_raw()
        teams = payload.get("teams") or {}
        if team_id not in teams:
            raise KeyError(f"Team '{team_id}' is not configured.")
        team = TeamDefinition.from_dict(team_id, teams[team_id] or {})
        if team.deleted and not include_deleted:
            raise KeyError(f"Team '{team_id}' is deleted.")
        return team

    def upsert(self, team: TeamDefinition) -> None:
        payload = self.load_raw()
        teams = payload.setdefault("teams", {})
        current = teams.get(team.id, {}) or {}
        created_at = current.get("created_at") or team.created_at
        saved = team.to_dict()
        saved["created_at"] = created_at
        saved["updated_at"] = _utc_now()
        saved.pop("id", None)
        teams[team.id] = saved
        self.save_raw(payload)

    def patch(self, team_id: str, updates: dict[str, Any]) -> TeamDefinition:
        team = self.get(team_id, include_deleted=True)
        raw = team.to_dict()
        raw.update(updates)
        raw["updated_at"] = _utc_now()
        updated = TeamDefinition.from_dict(team_id, raw)
        self.upsert(updated)
        return updated

    def load_state(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return {"version": "2.8.0", "teams": {}}
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def save_state(self, state: dict[str, Any]) -> None:
        self._ensure()
        state.setdefault("version", "2.8.0")
        self.state_path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")

    def update_state(self, team_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        state = self.load_state()
        teams = state.setdefault("teams", {})
        current = teams.setdefault(team_id, {"status": "idle", "updated_at": _utc_now()})
        current.update(updates)
        current["updated_at"] = _utc_now()
        teams[team_id] = current
        self.save_state(state)
        return current

    def team_state(self, team_id: str) -> dict[str, Any]:
        return dict(self.load_state().get("teams", {}).get(team_id, {"status": "idle"}))

    def save_run(self, record: dict[str, Any]) -> Path:
        self._ensure()
        path = self.runs_dir / f"{record['run_id']}.json"
        path.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")
        return path

    def list_runs(self, team_id: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        if not self.runs_dir.exists():
            return []
        records: list[dict[str, Any]] = []
        for path in sorted(self.runs_dir.glob("*.json"), reverse=True):
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if team_id and record.get("team_id") != team_id:
                continue
            record["path"] = str(path)
            records.append(record)
            if len(records) >= limit:
                break
        return records


class TeamRuntime:
    """Coordinates multiple configured agents as a team."""

    def __init__(self, workspace_path: str | Path) -> None:
        self.workspace_path = Path(workspace_path).resolve()
        self.store = TeamStore(self.workspace_path)
        self.agent_runner = AgentRunner(self.workspace_path)
        self.agent_registry = AgentRegistry(self.workspace_path)
        self.artifacts = TeamArtifactStore(self.workspace_path)

    def create(self, team_id: str, *, name: str | None = None, mode: str = "sequential", description: str = "") -> ToolResult:
        team_id = team_id.strip()
        if not team_id:
            return ToolResult(success=False, tool="team.create", errors=["Team id is required."])
        try:
            self.store.get(team_id, include_deleted=True)
            return ToolResult(success=False, tool="team.create", errors=[f"Team '{team_id}' already exists."])
        except KeyError:
            pass
        team = TeamDefinition(
            id=team_id,
            name=name or team_id.replace("-", " ").title(),
            description=description or "Workspace-managed multi-agent team.",
            mode=mode,
        )
        self.store.upsert(team)
        state = self.store.update_state(team.id, {"status": "idle", "created_at": _utc_now(), "last_run_id": None})
        return ToolResult(success=True, tool="team.create", data={"team": team.to_dict(), "runtime_state": state, "store_path": str(self.store.path), "state_path": str(self.store.state_path)})

    def add(self, team_id: str, agent_id: str) -> ToolResult:
        try:
            team = self.store.get(team_id)
            agent = AgentRegistry(self.workspace_path).get(agent_id)
        except Exception as exc:
            return ToolResult(success=False, tool="team.add", errors=[str(exc)])
        agents = list(team.agents)
        if agent.id not in agents:
            agents.append(agent.id)
        updated = self.store.patch(team.id, {"agents": agents})
        return ToolResult(success=True, tool="team.add", data={"team": updated.to_dict(), "agent": agent.model_dump(), "store_path": str(self.store.path)})

    def remove(self, team_id: str, agent_id: str) -> ToolResult:
        try:
            team = self.store.get(team_id)
        except Exception as exc:
            return ToolResult(success=False, tool="team.remove", errors=[str(exc)])
        agents = [item for item in team.agents if item != agent_id]
        updated = self.store.patch(team.id, {"agents": agents})
        return ToolResult(success=True, tool="team.remove", data={"team": updated.to_dict(), "removed_agent_id": agent_id, "store_path": str(self.store.path)})

    def list(self, include_disabled: bool = True, include_deleted: bool = False) -> ToolResult:
        teams = [team.to_dict() for team in self.store.list(include_disabled=include_disabled, include_deleted=include_deleted)]
        return ToolResult(success=True, tool="team.list", data={"teams": teams, "count": len(teams), "store_path": str(self.store.path)})

    def show(self, team_id: str) -> ToolResult:
        try:
            team = self.store.get(team_id, include_deleted=True)
        except Exception as exc:
            return ToolResult(success=False, tool="team.show", errors=[str(exc)])
        agents: list[dict[str, Any]] = []
        for agent_id in team.agents:
            try:
                agents.append(AgentRegistry(self.workspace_path).get(agent_id, include_deleted=True).model_dump())
            except Exception as exc:
                agents.append({"id": agent_id, "error": str(exc)})
        return ToolResult(success=True, tool="team.show", data={"team": team.to_dict(), "agents": agents, "runtime_state": self.store.team_state(team.id), "store_path": str(self.store.path)})

    def status(self, team_id: str) -> ToolResult:
        try:
            team = self.store.get(team_id, include_deleted=True)
        except Exception as exc:
            return ToolResult(success=False, tool="team.status", errors=[str(exc)])
        return ToolResult(success=True, tool="team.status", data={"team": team.to_dict(), "runtime_state": self.store.team_state(team.id), "recent_runs": self.store.list_runs(team.id, limit=5)})

    def stop(self, team_id: str, reason: str = "Manual team stop requested.") -> ToolResult:
        try:
            team = self.store.get(team_id, include_deleted=True)
        except Exception as exc:
            return ToolResult(success=False, tool="team.stop", errors=[str(exc)])
        state = self.store.update_state(team.id, {"status": "stopped", "stop_requested": True, "stop_reason": reason, "stopped_at": _utc_now()})
        return ToolResult(success=True, tool="team.stop", data={"team": team.to_dict(), "runtime_state": state})

    def history(self, team_id: str | None = None, limit: int = 20) -> ToolResult:
        runs = self.store.list_runs(team_id, limit=limit)
        return ToolResult(success=True, tool="team.history", data={"team_id": team_id, "runs": runs, "count": len(runs)})

    def artifacts_for_run(self, run_id: str) -> ToolResult:
        return ToolResult(success=True, tool="team.artifacts", data=self.artifacts.list_run_artifacts(run_id))

    def delete(self, team_id: str) -> ToolResult:
        try:
            updated = self.store.patch(team_id, {"deleted": True, "enabled": False})
        except Exception as exc:
            return ToolResult(success=False, tool="team.delete", errors=[str(exc)])
        return ToolResult(success=True, tool="team.delete", data={"team": updated.to_dict(), "store_path": str(self.store.path)})

    def run(self, team_id: str, prompt: str = "", *, mode: str | None = None, continue_on_error: bool = False, dry_run: bool = False) -> ToolResult:
        try:
            team = self.store.get(team_id)
        except Exception as exc:
            return ToolResult(success=False, tool="team.run", errors=[str(exc)])
        if not team.enabled:
            return ToolResult(success=False, tool="team.run", errors=[f"Team '{team.id}' is disabled."])
        if not team.agents:
            return ToolResult(success=False, tool="team.run", errors=[f"Team '{team.id}' has no agents."])

        execution_mode = mode or team.mode or "sequential"
        run_id = f"team-run-{uuid4().hex[:12]}"
        started_at = _utc_now()
        self.store.update_state(team.id, {"status": "running", "current_run_id": run_id, "last_prompt": prompt, "started_at": started_at})
        started = time.perf_counter()
        results: list[dict[str, Any]] = []
        failed: list[str] = []
        completed: list[str] = []
        artifact_records: list[dict[str, Any]] = []
        run_context_artifact = self.artifacts.write_run_context(run_id, team=team.to_dict(), prompt=prompt, mode=execution_mode, agents=list(team.agents))
        artifact_records.append(run_context_artifact)
        shared_context = {
            "team_id": team.id,
            "team_run_id": run_id,
            "prompt": prompt,
            "previous_results": [],
            "artifacts": [],
        }

        # v3.0.2 keeps deterministic sequential execution but upgrades the team
        # runtime into a collaboration pipeline: every agent writes an artifact
        # and the next agent receives artifact summaries and paths in context.
        for index, agent_id in enumerate(team.agents, start=1):
            agent_prompt = self._agent_prompt(prompt, agent_id, shared_context, execution_mode)
            result = self.agent_runner.run_agent(agent_id, prompt=agent_prompt, dry_run=dry_run)
            role = self._agent_role(agent_id)
            result_payload = {
                "agent_id": agent_id,
                "prompt": agent_prompt,
                "status": "completed" if result.success else "failed",
                "success": result.success,
                "tool": result.tool,
                "data": result.data,
                "errors": result.errors,
            }
            artifact = self.artifacts.write_agent_artifact(
                run_id,
                index=index,
                agent_id=agent_id,
                role=role,
                prompt=agent_prompt,
                result_payload=result_payload,
                previous_artifacts=list(shared_context.get("artifacts", [])),
            )
            result_payload["artifact"] = artifact
            results.append(result_payload)
            artifact_records.append(artifact)
            shared_context["previous_results"].append({"agent_id": agent_id, "success": result.success, "errors": result.errors, "artifact_id": artifact["id"]})
            shared_context["artifacts"].append({
                "id": artifact["id"],
                "agent_id": agent_id,
                "role": role,
                "title": artifact["title"],
                "summary": artifact["summary"],
                "markdown_path": artifact["markdown_path"],
                "json_path": artifact["json_path"],
            })
            if result.success:
                completed.append(agent_id)
            else:
                failed.append(agent_id)
                if not continue_on_error:
                    break

        duration_ms = int((time.perf_counter() - started) * 1000)
        success = not failed
        status = "completed" if success else "failed"
        completed_at = _utc_now()
        artifact_manifest = self.artifacts.write_manifest(run_id, artifact_records)
        record = {
            "run_id": run_id,
            "team_id": team.id,
            "team_name": team.name,
            "mode": execution_mode,
            "prompt": prompt,
            "dry_run": dry_run,
            "continue_on_error": continue_on_error,
            "status": status,
            "success": success,
            "completed": completed,
            "failed": failed,
            "results": results,
            "artifacts": artifact_records,
            "artifact_manifest": artifact_manifest,
            "started_at": started_at,
            "completed_at": completed_at,
            "duration_ms": duration_ms,
        }
        run_path = self.store.save_run(record)
        self.store.update_state(team.id, {
            "status": status,
            "current_run_id": None,
            "last_run_id": run_id,
            "last_result": "success" if success else "error",
            "last_artifact_manifest": artifact_manifest.get("path"),
            "completed_at": completed_at,
        })
        return ToolResult(
            success=success,
            tool="team.run",
            data={
                "team": team.to_dict(),
                "team_run": record,
                "run_path": str(run_path),
                "state_path": str(self.store.state_path),
                "artifact_manifest": artifact_manifest,
                "artifact_dir": str(self.artifacts.run_dir(run_id)),
                "summary": f"{len(completed)} completed, {len(failed)} failed, {len(artifact_records)} artifacts",
            },
            errors=[] if success else [f"Team run failed: {', '.join(failed)}"],
        )

    def _agent_prompt(self, prompt: str, agent_id: str, shared_context: dict[str, Any], mode: str) -> str:
        prior = ", ".join(item["agent_id"] for item in shared_context.get("previous_results", [])) or "none"
        role = self._agent_role(agent_id)
        directive = self._role_directive(agent_id, role)
        artifact_lines = []
        for artifact in shared_context.get("artifacts", []):
            artifact_lines.append(f"- {artifact.get('title')} from {artifact.get('agent_id')}: {artifact.get('summary')} ({artifact.get('markdown_path')})")
        artifact_block = "\n".join(artifact_lines) if artifact_lines else "none"
        return (
            f"Team objective: {prompt}\n"
            f"Execution mode: {mode}\n"
            f"Current agent: {agent_id}\n"
            f"Current role: {role}\n"
            f"Role directive: {directive}\n"
            f"Previous agents completed: {prior}\n"
            f"Artifacts available to consume:\n{artifact_block}"
        )

    def _agent_role(self, agent_id: str) -> str:
        try:
            return str(self.agent_registry.get(agent_id, include_deleted=True).role or agent_id)
        except Exception:
            return agent_id

    def _role_directive(self, agent_id: str, role: str) -> str:
        normalized = f"{agent_id} {role}".lower()
        if "research" in normalized:
            return "Produce repository findings and evidence that downstream agents can consume."
        if "architect" in normalized:
            return "Consume research artifacts and produce architecture observations, components, boundaries and risks."
        if "review" in normalized:
            return "Consume architecture and research artifacts and produce quality, security and maintainability review findings."
        if "report" in normalized:
            return "Consume all prior artifacts and produce a final synthesized report."
        return "Consume prior artifacts when available and produce a role-specific output artifact."

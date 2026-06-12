from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_id(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "-", value.strip()).strip("-") or "artifact"


class TeamArtifactStore:
    """Persist shared multi-agent collaboration artifacts.

    v3.0.2 introduces an artifact pipeline so each agent produces a concrete
    output that can be consumed by the next agent. Artifacts live under
    .dr-magu/teams/artifacts/<team-run-id>/ and are referenced from the team run
    record, plan execution result and subsequent agent prompts.
    """

    def __init__(self, workspace_path: str | Path) -> None:
        self.workspace_path = Path(workspace_path).resolve()
        self.root = self.workspace_path / ".dr-magu" / "teams" / "artifacts"

    def run_dir(self, run_id: str) -> Path:
        return self.root / _safe_id(run_id)

    def ensure_run(self, run_id: str) -> Path:
        path = self.run_dir(run_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def write_run_context(self, run_id: str, *, team: dict[str, Any], prompt: str, mode: str, agents: list[str]) -> dict[str, Any]:
        run_dir = self.ensure_run(run_id)
        payload = {
            "run_id": run_id,
            "team": team,
            "prompt": prompt,
            "mode": mode,
            "agents": agents,
            "created_at": _utc_now(),
        }
        path = run_dir / "00-run-context.json"
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return {"id": "run-context", "kind": "context", "path": str(path), "title": "Team Run Context"}

    def write_agent_artifact(
        self,
        run_id: str,
        *,
        index: int,
        agent_id: str,
        role: str,
        prompt: str,
        result_payload: dict[str, Any],
        previous_artifacts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        run_dir = self.ensure_run(run_id)
        artifact_id = self.artifact_id_for(agent_id=agent_id, role=role)
        prefix = f"{index:02d}-{_safe_id(agent_id)}"
        title = self.title_for(agent_id=agent_id, role=role)
        summary = self._summary_from_result(result_payload)
        data = {
            "id": artifact_id,
            "agent_id": agent_id,
            "role": role,
            "title": title,
            "prompt": prompt,
            "summary": summary,
            "success": bool(result_payload.get("success")),
            "status": result_payload.get("status"),
            "tool": result_payload.get("tool"),
            "errors": result_payload.get("errors") or [],
            "previous_artifacts": previous_artifacts,
            "result": result_payload.get("data") or {},
            "created_at": _utc_now(),
        }
        json_path = run_dir / f"{prefix}-{artifact_id}.json"
        md_path = run_dir / f"{prefix}-{artifact_id}.md"
        json_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        md_path.write_text(self._render_markdown(data), encoding="utf-8")
        return {
            "id": artifact_id,
            "agent_id": agent_id,
            "role": role,
            "title": title,
            "summary": summary,
            "json_path": str(json_path),
            "markdown_path": str(md_path),
            "success": data["success"],
            "created_at": data["created_at"],
        }

    def write_manifest(self, run_id: str, artifacts: list[dict[str, Any]]) -> dict[str, Any]:
        run_dir = self.ensure_run(run_id)
        manifest = {
            "run_id": run_id,
            "artifact_count": len(artifacts),
            "artifacts": artifacts,
            "updated_at": _utc_now(),
        }
        path = run_dir / "manifest.json"
        path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        manifest["path"] = str(path)
        return manifest

    def list_run_artifacts(self, run_id: str) -> dict[str, Any]:
        run_dir = self.run_dir(run_id)
        manifest_path = run_dir / "manifest.json"
        if manifest_path.exists():
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            payload["path"] = str(manifest_path)
            return payload
        artifacts = []
        if run_dir.exists():
            for path in sorted(run_dir.glob("*.md")):
                artifacts.append({"title": path.stem, "markdown_path": str(path)})
        return {"run_id": run_id, "artifact_count": len(artifacts), "artifacts": artifacts, "path": str(manifest_path)}

    @staticmethod
    def artifact_id_for(*, agent_id: str, role: str) -> str:
        normalized = f"{role} {agent_id}".lower()
        if "research" in normalized:
            return "repository-findings"
        if "architect" in normalized or "architecture" in normalized:
            return "architecture"
        if "review" in normalized:
            return "review"
        if "report" in normalized:
            return "final-report"
        return "agent-output"

    @staticmethod
    def title_for(*, agent_id: str, role: str) -> str:
        artifact_id = TeamArtifactStore.artifact_id_for(agent_id=agent_id, role=role)
        titles = {
            "repository-findings": "Repository Findings",
            "architecture": "Architecture Analysis",
            "review": "Review Findings",
            "final-report": "Final Multi-Agent Report",
            "agent-output": f"{agent_id.title()} Output",
        }
        return titles.get(artifact_id, f"{agent_id.title()} Output")

    @staticmethod
    def _summary_from_result(result_payload: dict[str, Any]) -> str:
        if not result_payload.get("success"):
            return "; ".join(result_payload.get("errors") or []) or "Agent execution failed."
        data = result_payload.get("data") or {}
        if isinstance(data, dict):
            if data.get("summary"):
                return str(data["summary"])
            workflow = data.get("workflow_result") or {}
            context = workflow.get("context") if isinstance(workflow, dict) else None
            if isinstance(context, dict):
                research = context.get("research") or context.get("last_step")
                if isinstance(research, dict):
                    research_data = research.get("data") or {}
                    provider = research_data.get("provider")
                    count = research_data.get("source_count")
                    if provider:
                        return f"Completed using provider {provider}; sources collected: {count}."
            agent_run = data.get("agent_run")
            if isinstance(agent_run, dict):
                duration = agent_run.get("duration_ms")
                workflow_id = agent_run.get("workflow")
                return f"Agent workflow {workflow_id} completed in {duration} ms."
        return "Agent execution completed successfully."

    @staticmethod
    def _render_markdown(data: dict[str, Any]) -> str:
        previous = data.get("previous_artifacts") or []
        lines = [
            f"# {data['title']}",
            "",
            f"- Agent: `{data['agent_id']}`",
            f"- Role: `{data['role']}`",
            f"- Status: `{data.get('status')}`",
            f"- Success: `{data.get('success')}`",
            f"- Created: `{data.get('created_at')}`",
            "",
            "## Summary",
            "",
            str(data.get("summary") or "No summary available."),
            "",
            "## Input Prompt",
            "",
            "```text",
            str(data.get("prompt") or ""),
            "```",
            "",
            "## Previous Artifacts Consumed",
            "",
        ]
        if previous:
            for item in previous:
                lines.append(f"- **{item.get('title', item.get('id', 'artifact'))}** from `{item.get('agent_id', 'unknown')}`: {item.get('summary', '')}")
        else:
            lines.append("- None")
        lines.extend([
            "",
            "## Raw Result Snapshot",
            "",
            "```json",
            json.dumps({
                "tool": data.get("tool"),
                "errors": data.get("errors"),
                "result_keys": sorted((data.get("result") or {}).keys()) if isinstance(data.get("result"), dict) else [],
            }, indent=2, sort_keys=True),
            "```",
            "",
        ])
        return "\n".join(lines)

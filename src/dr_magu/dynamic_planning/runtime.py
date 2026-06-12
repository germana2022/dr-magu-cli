from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dr_magu.commands.context import CommandContext
from dr_magu.config import load_config
from dr_magu.dynamic_planning.models import DynamicPlan, PlannedStep
from dr_magu.result import ToolResult


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class DynamicPlanningEngine:
    """Deterministic goal-to-plan runtime for Dr Magu v3.0.0.

    The engine intentionally starts deterministic and transparent: it maps a user
    goal to existing capabilities (MCP, workflows, agents, skills and teams),
    persists the generated execution graph, and can execute it through the
    command registry. This keeps v3.0.0 safe while creating the foundation for
    later LLM-assisted planning.
    """

    def __init__(self, workspace_path: str) -> None:
        self.workspace_path = str(Path(workspace_path).resolve())
        self.root = Path(self.workspace_path) / ".dr-magu" / "plans"
        self.root.mkdir(parents=True, exist_ok=True)

    def create(self, goal: str, *, approve: bool = False) -> ToolResult:
        goal = goal.strip()
        if not goal:
            return ToolResult(success=False, tool="plan.create", errors=["Goal cannot be empty."])
        plan = self._build_plan(goal)
        if approve:
            plan.status = "approved"
            for step in plan.steps:
                step.status = "approved" if step.requires_approval else step.status
        self._save(plan)
        return ToolResult(success=True, tool="plan.create", data={"plan": plan.model_dump(), "path": str(self._plan_path(plan.id))})

    def show(self, plan_id: str) -> ToolResult:
        plan = self._load(plan_id)
        return ToolResult(success=True, tool="plan.show", data={"plan": plan.model_dump(), "path": str(self._plan_path(plan.id))})

    def list(self) -> ToolResult:
        plans: list[dict[str, Any]] = []
        for path in sorted(self.root.glob("*/plan.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                plan = DynamicPlan.model_validate_json(path.read_text(encoding="utf-8"))
                plans.append({
                    "id": plan.id,
                    "goal": plan.goal,
                    "intent": plan.intent,
                    "status": plan.status,
                    "steps": len(plan.steps),
                    "updated_at": plan.updated_at,
                })
            except Exception:
                continue
        return ToolResult(success=True, tool="plan.list", data={"plans": plans, "count": len(plans)})

    def approve(self, plan_id: str) -> ToolResult:
        plan = self._load(plan_id)
        if plan.status in {"success", "cancelled"}:
            return ToolResult(success=False, tool="plan.approve", errors=[f"Cannot approve plan in status {plan.status}."])
        plan.status = "approved"
        for step in plan.steps:
            if step.status == "pending" and step.requires_approval:
                step.status = "approved"
        plan.updated_at = _now()
        self._save(plan)
        return ToolResult(success=True, tool="plan.approve", data={"plan": plan.model_dump()})

    def cancel(self, plan_id: str, *, reason: str = "Manual cancellation requested.") -> ToolResult:
        plan = self._load(plan_id)
        plan.status = "cancelled"
        for step in plan.steps:
            if step.status in {"pending", "approved", "running"}:
                step.status = "cancelled"
                step.errors.append(reason)
        plan.updated_at = _now()
        self._save(plan)
        return ToolResult(success=True, tool="plan.cancel", data={"plan": plan.model_dump(), "reason": reason})

    def status(self, plan_id: str) -> ToolResult:
        plan = self._load(plan_id)
        counts: dict[str, int] = {}
        for step in plan.steps:
            counts[step.status] = counts.get(step.status, 0) + 1
        return ToolResult(success=True, tool="plan.status", data={
            "id": plan.id,
            "goal": plan.goal,
            "intent": plan.intent,
            "status": plan.status,
            "step_status_counts": counts,
            "latest_run_id": plan.latest_run_id,
            "updated_at": plan.updated_at,
        })

    def run(self, plan_id: str, *, approved: bool = False, continue_on_error: bool = False) -> ToolResult:
        plan = self._load(plan_id)
        if plan.status == "cancelled":
            return ToolResult(success=False, tool="plan.run", errors=["Cannot run a cancelled plan."])
        if plan.approval_required and not approved and plan.status != "approved":
            return ToolResult(
                success=False,
                tool="plan.run",
                data={"plan_id": plan.id, "approval_required": True, "next_command": f"plan.approve {plan.id}"},
                errors=["Plan requires approval before execution."],
            )
        plan.status = "running"
        plan.latest_run_id = uuid.uuid4().hex[:12]
        plan.updated_at = _now()
        self._save(plan)

        from dr_magu.commands.processor import CommandProcessor
        from dr_magu.commands.registry import registry

        context = CommandContext(
            workspace_path=self.workspace_path,
            output_format="human",
            config=load_config(),
        )
        processor = CommandProcessor(registry)
        run_events: list[dict[str, Any]] = []
        all_success = True
        for step in plan.steps:
            if step.status == "cancelled":
                continue
            step.status = "running"
            plan.updated_at = _now()
            self._save(plan)
            result = processor.execute_line(step.command, context)
            step.result = {"success": result.success, "tool": result.tool, "data": result.data, "errors": result.errors}
            step.errors = result.errors
            step.status = "success" if result.success else "failed"
            run_events.append({"step_id": step.id, "command": step.command, "success": result.success, "tool": result.tool, "errors": result.errors})
            if not result.success:
                all_success = False
                if not continue_on_error:
                    break
        plan.status = "success" if all_success else "failed"
        plan.updated_at = _now()
        self._save(plan)
        self._write_run(plan, run_events)
        return ToolResult(success=all_success, tool="plan.run", data={"plan": plan.model_dump(), "events": run_events})

    def _build_plan(self, goal: str) -> DynamicPlan:
        lowered = goal.lower()
        plan_id = self._slug(goal)
        intent = self._detect_intent(lowered)
        steps: list[PlannedStep] = []
        selected_agents: list[str] = []
        selected_skills: list[str] = []
        selected_workflows: list[str] = []
        selected_mcp: list[str] = []
        selected_team: str | None = None
        explanation = "Generated a deterministic execution graph from the goal and available Dr Magu capabilities."

        steps.append(PlannedStep(
            id="doctor",
            name="Workspace readiness check",
            command="workspace.doctor",
            capability="workspace",
            description="Validate bootstrap, configuration, agents, skills, teams, workflows and MCP defaults.",
        ))

        if intent == "repository_analysis":
            selected_team = "repo-analysis"
            selected_agents = ["researcher", "architect", "reviewer", "reporter"]
            selected_skills = ["research", "filesystem", "architecture", "code-review", "reporting"]
            selected_workflows = ["repository.context", "research-brief"]
            selected_mcp = ["filesystem", "playwright", "github"]
            steps.extend([
                PlannedStep(id="mcp-boot", name="Boot MCP providers", command="mcp.boot", capability="mcp", description="Start enabled MCP providers required by the plan."),
                PlannedStep(id="context", name="Generate repository context", command="context.generate", capability="context", description="Create deterministic local repository context artifacts."),
                PlannedStep(id="team-run", name="Run repository analysis team", command=f'team.run {selected_team} "{goal}"', capability="team", description="Run the multi-agent repository analysis team against the goal."),
            ])
            explanation = "Detected a repository analysis goal and selected the repo-analysis team with research, filesystem, architecture, review and reporting skills."
        elif intent == "research":
            selected_agents = ["researcher"]
            selected_skills = ["research", "reporting"]
            selected_workflows = ["research-brief"]
            selected_mcp = ["playwright", "brave-search"]
            steps.extend([
                PlannedStep(id="mcp-boot", name="Boot MCP providers", command="mcp.boot", capability="mcp", description="Start enabled MCP providers required by research."),
                PlannedStep(id="research", name="Run multi-provider research", command=f'research.search "{goal}" --provider auto --debug', capability="research", description="Collect real research sources using configured MCP providers."),
                PlannedStep(id="report", name="Generate research report", command="report.from_research", capability="reporting", description="Generate report artifacts from the latest research output."),
            ])
            explanation = "Detected a research goal and selected the researcher agent, research/reporting skills and MCP research providers."
        else:
            selected_agents = ["researcher", "reporter"]
            selected_skills = ["research", "documentation", "reporting"]
            selected_workflows = ["research-brief"]
            selected_mcp = ["playwright"]
            steps.extend([
                PlannedStep(id="mcp-boot", name="Boot MCP providers", command="mcp.boot", capability="mcp", description="Start enabled MCP providers."),
                PlannedStep(id="agent-run", name="Run researcher agent", command=f'agent.run researcher "{goal}"', capability="agent", description="Use the researcher agent to process the goal."),
            ])
            explanation = "Selected a safe general-purpose plan using the researcher and reporter capabilities."

        return DynamicPlan(
            id=plan_id,
            goal=goal,
            intent=intent,
            status="draft",
            confidence=0.86 if intent != "general" else 0.72,
            workspace_path=self.workspace_path,
            selected_agents=selected_agents,
            selected_team=selected_team,
            selected_skills=selected_skills,
            selected_workflows=selected_workflows,
            selected_mcp_providers=selected_mcp,
            approval_required=False,
            explanation=explanation,
            steps=steps,
        )

    def _detect_intent(self, lowered_goal: str) -> str:
        if any(word in lowered_goal for word in ["repository", "repo", "codebase", "source code", "project architecture", "analyze this repository"]):
            return "repository_analysis"
        if any(word in lowered_goal for word in ["research", "search", "news", "trends", "find information", "investigate"]):
            return "research"
        return "general"

    def _slug(self, goal: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", goal.lower()).strip("-")[:42] or "plan"
        return f"{slug}-{uuid.uuid4().hex[:8]}"

    def _plan_dir(self, plan_id: str) -> Path:
        safe = re.sub(r"[^a-zA-Z0-9_.-]", "-", plan_id)
        return self.root / safe

    def _plan_path(self, plan_id: str) -> Path:
        return self._plan_dir(plan_id) / "plan.json"

    def _save(self, plan: DynamicPlan) -> None:
        path = self._plan_path(plan.id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(plan.model_dump_json(indent=2), encoding="utf-8")

    def _load(self, plan_id: str) -> DynamicPlan:
        path = self._plan_path(plan_id)
        if not path.exists():
            raise FileNotFoundError(f"Plan not found: {plan_id}")
        return DynamicPlan.model_validate_json(path.read_text(encoding="utf-8"))

    def _write_run(self, plan: DynamicPlan, events: list[dict[str, Any]]) -> None:
        if not plan.latest_run_id:
            return
        path = self._plan_dir(plan.id) / f"run-{plan.latest_run_id}.json"
        path.write_text(json.dumps({"plan_id": plan.id, "run_id": plan.latest_run_id, "events": events, "updated_at": plan.updated_at}, indent=2), encoding="utf-8")

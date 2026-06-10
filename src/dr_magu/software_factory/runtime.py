from __future__ import annotations

from pathlib import Path

from dr_magu.commands.context import CommandContext
from dr_magu.commands.processor import CommandProcessor
from dr_magu.commands.registry import registry
from dr_magu.config import load_config
from dr_magu.result import ToolResult

from .planner import SoftwareFactoryPlanner
from .store import SoftwareFactoryStore


class SoftwareFactoryRuntime:
    """End-to-end autonomous software factory foundation."""

    def __init__(self, workspace_path: str | Path):
        self.workspace_path = str(Path(workspace_path).resolve())
        self.store = SoftwareFactoryStore(self.workspace_path)
        self.processor = CommandProcessor(registry)

    def plan(self, idea: str, name: str = "software.factory") -> ToolResult:
        plan = SoftwareFactoryPlanner().create_plan(idea=idea, name=name)
        artifact = self.store.write_json("factory-plan.json", plan.to_dict())
        return ToolResult(
            success=True,
            tool="factory.plan",
            data={"plan": plan.to_dict(), "artifact": artifact},
        )

    def run(self, idea: str, name: str = "software.factory", continue_on_error: bool = False) -> ToolResult:
        plan = SoftwareFactoryPlanner().create_plan(idea=idea, name=name)
        context = CommandContext(workspace_path=self.workspace_path, output_format="human", config=load_config())
        completed: set[str] = set()
        failed: set[str] = set()
        results: list[dict] = []

        plan_artifact = self.store.write_json("factory-plan.json", plan.to_dict())
        self._write_stage_artifact("01-idea-intake.md", "Idea Intake", idea, "Captured idea, goals and assumptions.")
        completed.add("idea-intake")
        results.append({
            "stage": "idea-intake",
            "status": "completed",
            "artifact": str(self.store.root / "01-idea-intake.md"),
        })

        for stage in plan.stages:
            if stage.id == "idea-intake":
                continue

            blocked_by = [dep for dep in stage.depends_on if dep not in completed]
            if blocked_by:
                failed.add(stage.id)
                results.append({
                    "stage": stage.id,
                    "status": "skipped",
                    "reason": f"Dependencies not completed: {', '.join(blocked_by)}",
                })
                if not continue_on_error:
                    break
                continue

            if stage.command.startswith("factory.stage"):
                result = self._run_internal_stage(stage.id, idea, stage.artifact_name)
            else:
                result = self.processor.execute_line(stage.command, context)

            results.append({
                "stage": stage.id,
                "title": stage.title,
                "command": stage.command,
                "status": "completed" if result.success else "failed",
                "result": {
                    "success": result.success,
                    "tool": result.tool,
                    "data": result.data,
                    "errors": result.errors,
                },
            })

            if result.success:
                completed.add(stage.id)
            else:
                failed.add(stage.id)
                if not continue_on_error:
                    break

        summary = {
            "idea": idea,
            "completed": sorted(completed),
            "failed": sorted(failed),
            "result_count": len(results),
            "plan_artifact": plan_artifact,
            "factory_dir": str(self.store.root),
        }
        self.store.write_json("factory-run-summary.json", {"summary": summary, "results": results})

        return ToolResult(
            success=not failed,
            tool="factory.run",
            data={"plan": plan.to_dict(), "summary": summary, "results": results},
            errors=[] if not failed else [f"Factory run failed: {', '.join(sorted(failed))}"],
        )

    def run_stage(self, stage: str, idea: str) -> ToolResult:
        filename = {
            "idea-intake": "01-idea-intake.md",
            "code-plan": "05-code-plan.md",
        }.get(stage, f"{stage}.md")
        return self._run_internal_stage(stage, idea, filename)

    def _run_internal_stage(self, stage: str, idea: str, filename: str) -> ToolResult:
        title = stage.replace("-", " ").title()
        body = self._stage_body(stage, idea)
        artifact = self.store.write_markdown(filename, title, body)
        return ToolResult(success=True, tool="factory.stage", data={"stage": stage, "artifact": artifact})

    def _write_stage_artifact(self, filename: str, title: str, idea: str, summary: str) -> dict:
        body = f"# {title}\n\nIdea: {idea}\n\n## Summary\n\n{summary}\n"
        return self.store.write_markdown(filename, title, body)

    def _stage_body(self, stage: str, idea: str) -> str:
        if stage == "code-plan":
            return (
                "# Code Implementation Plan\n\n"
                f"Idea: {idea}\n\n"
                "## Proposed Modules\n\n"
                "- CLI command boundary\n"
                "- Runtime service\n"
                "- Artifact store\n"
                "- Tests\n\n"
                "## Implementation Notes\n\n"
                "- Keep commands deterministic where possible.\n"
                "- Use LLM/MCP only behind explicit runtime boundaries.\n"
                "- Preserve cross-platform compatibility.\n"
            )
        return (
            f"# {stage.replace('-', ' ').title()}\n\n"
            f"Idea: {idea}\n\n"
            "## Notes\n\n"
            "- Generated by the Autonomous Software Factory foundation.\n"
        )

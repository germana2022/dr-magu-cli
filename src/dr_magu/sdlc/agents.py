from __future__ import annotations

import json
from pathlib import Path

from dr_magu.result import ToolResult

from .artifact_store import SdlcArtifactStore


SOFTWARE_AGENTS = {
    "repository-analyzer": ("repository-analysis.md", "Repository Analysis", "Analyze repository structure, languages and key files."),
    "architecture-planner": ("architecture-proposal.md", "Architecture Proposal", "Generate architecture options and recommendations."),
    "ticket-generator": ("tickets.json", "Implementation Tickets", "Generate implementation tickets from repository context."),
    "code-reviewer": ("review-report.md", "Code Review Report", "Generate a code review report from repository context."),
    "test-generator": ("generated-tests.md", "Generated Test Plan", "Generate a test plan and suggested test cases."),
    "documentation-writer": ("documentation-plan.md", "Documentation Plan", "Generate documentation recommendations."),
    "release-notes-generator": ("release-notes.md", "Release Notes", "Generate release notes from repository context."),
}


class SoftwareAgentRunner:
    """Run deterministic SDLC agent foundations."""

    def __init__(self, workspace_path: str | Path):
        self.workspace_path = Path(workspace_path).resolve()
        self.store = SdlcArtifactStore(self.workspace_path)

    def list_agents(self) -> ToolResult:
        return ToolResult(
            success=True,
            tool="sdlc.agent.list",
            data={
                "count": len(SOFTWARE_AGENTS),
                "agents": [
                    {"id": agent_id, "filename": data[0], "title": data[1], "description": data[2]}
                    for agent_id, data in SOFTWARE_AGENTS.items()
                ],
            },
        )

    def run(self, agent_id: str) -> ToolResult:
        if agent_id not in SOFTWARE_AGENTS:
            return ToolResult(success=False, tool="sdlc.agent.run", errors=[f"Unknown software development agent: {agent_id}"])

        filename, title, description = SOFTWARE_AGENTS[agent_id]
        artifact_type = "json" if filename.endswith(".json") else "markdown"
        body = self._json_body(agent_id, title, description) if artifact_type == "json" else self._markdown_body(agent_id, title, description)
        artifact = self.store.write_text_artifact(agent_id, filename, title, body, artifact_type)

        return ToolResult(success=True, tool="sdlc.agent.run", data={"agent_id": agent_id, "artifact": artifact.to_dict()})

    def _json_body(self, agent_id: str, title: str, description: str) -> str:
        return json.dumps({
            "agent_id": agent_id,
            "title": title,
            "description": description,
            "tickets": [
                {"id": "SDLC-001", "title": "Review repository context"},
                {"id": "SDLC-002", "title": "Create implementation plan"},
            ],
        }, indent=2)

    def _markdown_body(self, agent_id: str, title: str, description: str) -> str:
        visible_files = []
        if self.workspace_path.exists() and self.workspace_path.is_dir():
            visible_files = [p.name for p in self.workspace_path.iterdir() if not p.name.startswith(".")][:20]
        files = "\n".join(f"- {name}" for name in visible_files) or "- No visible files found."
        return (
            f"# {title}\n\n"
            f"Agent: `{agent_id}`\n\n"
            f"Purpose: {description}\n\n"
            "## Workspace Snapshot\n\n"
            f"Workspace: `{self.workspace_path}`\n\n"
            "## Visible Files\n\n"
            f"{files}\n\n"
            "## Next Steps\n\n"
            "- Review generated artifact.\n"
            "- Refine with Brain/LLM execution in future versions.\n"
        )

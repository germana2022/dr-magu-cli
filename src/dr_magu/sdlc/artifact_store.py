from __future__ import annotations

from pathlib import Path

from .models import AgentArtifact


class SdlcArtifactStore:
    """Store software development agent artifacts under .dr-magu/sdlc."""

    def __init__(self, workspace_path: str | Path):
        self.workspace_path = Path(workspace_path).resolve()
        self.base_dir = self.workspace_path / ".dr-magu" / "sdlc"

    def write_text_artifact(self, agent_id: str, filename: str, title: str, body: str, artifact_type: str) -> AgentArtifact:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        path = self.base_dir / filename
        path.write_text(body, encoding="utf-8")
        return AgentArtifact(agent_id=agent_id, title=title, path=str(path), artifact_type=artifact_type)

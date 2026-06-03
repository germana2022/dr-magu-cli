from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from dr_magu.sessions.models import CommandRecord, EventRecord, SessionMetadata


class SessionStore:
    """File-system backed store for Dr Magu persistent sessions."""

    def __init__(self, workspace_path: str | Path) -> None:
        self.workspace_path = Path(workspace_path).resolve()
        self.root_path = self.workspace_path / ".dr-magu"
        self.sessions_path = self.root_path / "sessions"
        self.current_session_path = self.root_path / "current-session"

    def ensure_root(self) -> None:
        self.sessions_path.mkdir(parents=True, exist_ok=True)

    def session_path(self, session_id: str) -> Path:
        return self.sessions_path / session_id

    def session_file(self, session_id: str) -> Path:
        return self.session_path(session_id) / "session.json"

    def commands_file(self, session_id: str) -> Path:
        return self.session_path(session_id) / "commands.jsonl"

    def events_file(self, session_id: str) -> Path:
        return self.session_path(session_id) / "events.jsonl"

    def write_metadata(self, metadata: SessionMetadata) -> None:
        self.ensure_root()
        session_dir = self.session_path(metadata.id)
        session_dir.mkdir(parents=True, exist_ok=True)
        self.session_file(metadata.id).write_text(
            json.dumps(metadata.model_dump(), indent=2),
            encoding="utf-8",
        )

    def read_metadata(self, session_id: str) -> SessionMetadata:
        raw = self.session_file(session_id).read_text(encoding="utf-8")
        return SessionMetadata.model_validate_json(raw)

    def append_command(self, session_id: str, record: CommandRecord) -> None:
        self.ensure_root()
        session_dir = self.session_path(session_id)
        session_dir.mkdir(parents=True, exist_ok=True)
        with self.commands_file(session_id).open("a", encoding="utf-8") as handle:
            handle.write(record.model_dump_json() + "\n")

    def append_event(self, session_id: str, record: EventRecord) -> None:
        self.ensure_root()
        session_dir = self.session_path(session_id)
        session_dir.mkdir(parents=True, exist_ok=True)
        with self.events_file(session_id).open("a", encoding="utf-8") as handle:
            handle.write(record.model_dump_json() + "\n")

    def set_current_session(self, session_id: str) -> None:
        self.ensure_root()
        self.current_session_path.write_text(session_id, encoding="utf-8")

    def get_current_session_id(self) -> str | None:
        if not self.current_session_path.exists():
            return None
        session_id = self.current_session_path.read_text(encoding="utf-8").strip()
        return session_id or None

    def clear_current_session(self) -> None:
        if self.current_session_path.exists():
            self.current_session_path.unlink()

    def list_metadata(self) -> list[SessionMetadata]:
        self.ensure_root()
        sessions: list[SessionMetadata] = []
        for session_file in self.sessions_path.glob("*/session.json"):
            try:
                sessions.append(SessionMetadata.model_validate_json(session_file.read_text(encoding="utf-8")))
            except (ValueError, OSError):
                continue
        return sorted(sessions, key=lambda item: item.updated_at, reverse=True)

    def read_commands(self, session_id: str) -> list[CommandRecord]:
        path = self.commands_file(session_id)
        return list(self._read_jsonl(path, CommandRecord))

    def read_events(self, session_id: str) -> list[EventRecord]:
        path = self.events_file(session_id)
        return list(self._read_jsonl(path, EventRecord))

    @staticmethod
    def _read_jsonl(path: Path, model_type: type[CommandRecord] | type[EventRecord]) -> Iterable[CommandRecord | EventRecord]:
        if not path.exists():
            return []
        rows = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rows.append(model_type.model_validate_json(line))
        return rows

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from dr_magu.result import ToolResult
from dr_magu.sessions.models import CommandRecord, EventRecord, SessionMetadata, utc_now_iso
from dr_magu.sessions.store import SessionStore


class SessionManager:
    """Coordinates persistent Dr Magu sessions for a workspace."""

    def __init__(self, workspace_path: str | Path) -> None:
        self.store = SessionStore(workspace_path)

    def start(self) -> SessionMetadata:
        """Create a new active session and mark it as current."""
        self.store.ensure_root()
        session_id = self._new_session_id()
        now = utc_now_iso()
        metadata = SessionMetadata(
            id=session_id,
            workspace_path=str(self.store.workspace_path),
            created_at=now,
            updated_at=now,
            status="active",
        )
        self.store.write_metadata(metadata)
        self.store.set_current_session(session_id)
        self.record_event(session_id, "session.started")
        return self.store.read_metadata(session_id)

    def get_or_start_current(self) -> SessionMetadata:
        """Return the active current session or create a new one."""
        session_id = self.store.get_current_session_id()
        if session_id:
            try:
                metadata = self.store.read_metadata(session_id)
                if metadata.status == "active":
                    self.record_event(metadata.id, "tui.started")
                    return self.store.read_metadata(metadata.id)
            except FileNotFoundError:
                self.store.clear_current_session()
        metadata = self.start()
        self.record_event(metadata.id, "tui.started")
        return self.store.read_metadata(metadata.id)

    def current(self) -> SessionMetadata | None:
        session_id = self.store.get_current_session_id()
        if not session_id:
            return None
        try:
            return self.store.read_metadata(session_id)
        except FileNotFoundError:
            self.store.clear_current_session()
            return None

    def list(self) -> list[SessionMetadata]:
        return self.store.list_metadata()

    def show(self, session_id: str) -> SessionMetadata:
        return self.store.read_metadata(session_id)

    def resume(self, session_id: str) -> SessionMetadata:
        """Set an existing session as current and mark it active."""
        metadata = self.store.read_metadata(session_id)
        if metadata.status == "deleted":
            raise ValueError(f"Cannot resume deleted session: {session_id}")
        metadata.status = "active"
        metadata.updated_at = utc_now_iso()
        self.store.write_metadata(metadata)
        self.store.set_current_session(session_id)
        self.record_event(session_id, "session.resumed")
        return self.store.read_metadata(session_id)

    def close(self, session_id: str) -> SessionMetadata:
        """Close an existing session without deleting its files."""
        metadata = self.store.read_metadata(session_id)
        self.record_event(metadata.id, "session.closed")
        metadata = self.store.read_metadata(metadata.id)
        metadata.status = "closed"
        metadata.updated_at = utc_now_iso()
        self.store.write_metadata(metadata)
        if self.store.get_current_session_id() == session_id:
            self.store.clear_current_session()
        return metadata

    def close_current(self) -> SessionMetadata | None:
        """Close the current session and clear the current-session pointer."""
        metadata = self.current()
        if metadata is None:
            return None
        return self.close(metadata.id)

    def delete(self, session_id: str) -> SessionMetadata:
        """Soft-delete a session by marking it as deleted.

        The session directory remains on disk so accidental deletion can be
        recovered manually. Dr Magu does not physically remove session files in
        v0.5.2.
        """
        metadata = self.store.read_metadata(session_id)
        self.record_event(metadata.id, "session.deleted")
        metadata = self.store.read_metadata(metadata.id)
        metadata.status = "deleted"
        metadata.updated_at = utc_now_iso()
        self.store.write_metadata(metadata)
        if self.store.get_current_session_id() == session_id:
            self.store.clear_current_session()
        return metadata

    def record_command(self, session_id: str, command_line: str, result: ToolResult) -> SessionMetadata:
        """Persist safe command metadata for a session."""
        duration = result.metadata.get("duration_ms") if result.metadata else None
        duration_ms = int(duration) if duration is not None else None
        record = CommandRecord(
            command=command_line,
            tool=result.tool,
            success=result.success,
            duration_ms=duration_ms,
        )
        self.store.append_command(session_id, record)
        self.record_event(session_id, "command.executed", {"tool": result.tool, "success": result.success})
        metadata = self.store.read_metadata(session_id)
        metadata.command_count += 1
        metadata.updated_at = utc_now_iso()
        self.store.write_metadata(metadata)
        return self.store.read_metadata(session_id)

    def record_event(self, session_id: str, event_type: str, details: dict[str, object] | None = None) -> SessionMetadata:
        """Persist a session event and refresh metadata."""
        record = EventRecord(type=event_type, details=details or {})
        self.store.append_event(session_id, record)
        metadata = self.store.read_metadata(session_id)
        metadata.event_count += 1
        metadata.updated_at = utc_now_iso()
        self.store.write_metadata(metadata)
        return self.store.read_metadata(session_id)

    def read_commands(self, session_id: str) -> list[CommandRecord]:
        return self.store.read_commands(session_id)

    @staticmethod
    def _new_session_id() -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        suffix = uuid4().hex[:6]
        return f"{timestamp}-{suffix}"

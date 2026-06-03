from __future__ import annotations

from dr_magu.result import ToolResult
from dr_magu.sessions.manager import SessionManager


def test_start_creates_persistent_session(tmp_path):
    manager = SessionManager(tmp_path)

    metadata = manager.start()

    assert metadata.status == "active"
    assert metadata.command_count == 0
    assert (tmp_path / ".dr-magu" / "current-session").read_text(encoding="utf-8") == metadata.id
    assert (tmp_path / ".dr-magu" / "sessions" / metadata.id / "session.json").exists()
    assert (tmp_path / ".dr-magu" / "sessions" / metadata.id / "events.jsonl").exists()


def test_record_command_persists_safe_metadata(tmp_path):
    manager = SessionManager(tmp_path)
    metadata = manager.start()
    result = ToolResult(
        success=True,
        tool="git.status",
        data={"stdout": "secret output should not be persisted"},
        metadata={"duration_ms": 12},
    )

    updated = manager.record_command(metadata.id, "git.status", result)
    commands = manager.read_commands(metadata.id)

    assert updated.command_count == 1
    assert commands[0].command == "git.status"
    assert commands[0].tool == "git.status"
    assert commands[0].success is True
    assert commands[0].duration_ms == 12
    commands_file = tmp_path / ".dr-magu" / "sessions" / metadata.id / "commands.jsonl"
    assert "secret output" not in commands_file.read_text(encoding="utf-8")


def test_resume_sets_session_as_current(tmp_path):
    manager = SessionManager(tmp_path)
    first = manager.start()
    second = manager.start()

    resumed = manager.resume(first.id)
    current = manager.current()

    assert second.id != first.id
    assert resumed.id == first.id
    assert current is not None
    assert current.id == first.id
    assert current.status == "active"


def test_close_current_marks_session_closed(tmp_path):
    manager = SessionManager(tmp_path)
    metadata = manager.start()

    closed = manager.close_current()

    assert closed is not None
    assert closed.id == metadata.id
    assert closed.status == "closed"
    assert manager.current() is None


def test_delete_marks_session_deleted_without_removing_files(tmp_path):
    manager = SessionManager(tmp_path)
    metadata = manager.start()

    deleted = manager.delete(metadata.id)

    assert deleted.status == "deleted"
    assert manager.current() is None
    assert (tmp_path / ".dr-magu" / "sessions" / metadata.id / "session.json").exists()


def test_deleted_session_cannot_be_resumed(tmp_path):
    manager = SessionManager(tmp_path)
    metadata = manager.start()
    manager.delete(metadata.id)

    try:
        manager.resume(metadata.id)
    except ValueError as exc:
        assert metadata.id in str(exc)
    else:
        raise AssertionError("Deleted sessions should not be resumable")

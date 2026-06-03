from __future__ import annotations

from datetime import datetime, timezone

from dr_magu.tui_app import (
    _format_command_count,
    _format_relative_time,
    _format_status,
    _short_session_id,
)


def test_short_session_id_uses_time_component():
    assert _short_session_id("20260603-185649-834c45") == "18:56:49"


def test_format_command_count_is_readable():
    assert _format_command_count(1) == "1 command"
    assert _format_command_count(8) == "8 commands"


def test_format_relative_time_uses_human_readable_labels():
    now = datetime(2026, 6, 3, 19, 0, 0, tzinfo=timezone.utc)

    assert _format_relative_time("2026-06-03T18:59:00+00:00", now) == "1 min ago"
    assert _format_relative_time("2026-06-03T18:00:00+00:00", now) == "1 hour ago"
    assert _format_relative_time("2026-06-02T19:00:00+00:00", now) == "1 day ago"


def test_format_status_does_not_rely_on_color_only():
    assert _format_status("active") == "● Active"
    assert _format_status("closed") == "○ Closed"
    assert _format_status("deleted") == "× Deleted"

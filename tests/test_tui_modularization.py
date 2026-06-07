from dr_magu.tui.commands import normalize_command
from dr_magu.tui.models import TuiSettings
from dr_magu.tui.renderers.results import summarize_result_data
from dr_magu.tui.screens.agent_manager import format_agent_state
from dr_magu.tui.screens.control_center import list_control_center_sections
from dr_magu.tui.screens.session_manager import format_session_status
from dr_magu.tui.widgets.labels import command_hint


def test_tui_settings_uses_v095_version():
    settings = TuiSettings(workspace_path=".")
    assert settings.version == "0.9.5"


def test_normalize_slash_run_command():
    assert normalize_command("/run git.status") == "git.status"


def test_normalize_direct_slash_command():
    assert normalize_command("/brain") == "brain"


def test_result_summary_for_git_status():
    summary = summarize_result_data("git.status", {"branch": "main", "status": "clean"})
    assert "main" in summary
    assert "clean" in summary


def test_control_center_sections_include_brain_and_schedules():
    sections = list_control_center_sections()
    assert "Brain" in sections
    assert "Schedules" in sections


def test_session_status_marks_current():
    assert format_session_status("active", is_current=True) == "current active"


def test_agent_state_labels_deleted_agents():
    assert format_agent_state(enabled=False, deleted=True) == "deleted"


def test_command_hint_mentions_brain():
    assert "/brain" in command_hint()

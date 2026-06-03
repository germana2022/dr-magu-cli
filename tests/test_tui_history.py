from dr_magu.tui_history import SessionCommandHistory


def test_history_returns_previous_commands_in_reverse_order() -> None:
    history = SessionCommandHistory()
    history.add("git.status")
    history.add("files.list .")

    assert history.previous() == "files.list ."
    assert history.previous() == "git.status"
    assert history.previous() == "git.status"


def test_history_returns_next_commands_and_clears_after_last_item() -> None:
    history = SessionCommandHistory()
    history.add("git.status")
    history.add("git.diff")

    assert history.previous() == "git.diff"
    assert history.previous() == "git.status"
    assert history.next() == "git.diff"
    assert history.next() == ""
    assert history.next() is None


def test_history_skips_blank_commands_and_duplicate_last_command() -> None:
    history = SessionCommandHistory()
    history.add("  ")
    history.add("git.status")
    history.add("git.status")

    assert history.count == 1
    assert history.previous() == "git.status"

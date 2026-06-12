from pathlib import Path


def test_tui_uses_selectable_log_view() -> None:
    source = Path('src/dr_magu/tui_app.py').read_text(encoding='utf-8')
    assert 'class SelectableLogView(TextArea)' in source
    assert 'RichLog = SelectableLogView' in source
    assert 'def action_copy_selected_output' in source
    assert '/copy-selection' in source


def test_v282_release_notes_document_selectable_logs() -> None:
    notes = Path('RELEASE_v2.8.2.md').read_text(encoding='utf-8')
    assert 'Selectable Log Viewer UX Patch' in notes
    assert 'Ctrl+C' in notes
    assert '/copy-selection' in notes

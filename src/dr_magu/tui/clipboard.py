from __future__ import annotations

import json
import platform
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dr_magu.result import ToolResult


@dataclass(frozen=True)
class ClipboardResult:
    """Result returned by clipboard/export operations used by the TUI."""

    success: bool
    message: str
    path: str | None = None


def format_tool_result_for_copy(command_line: str, result: ToolResult) -> str:
    """Return a plain-text representation of a tool result suitable for copying.

    The TUI renders Rich markup, which is useful visually but difficult to select
    in terminal mouse-capture mode. This formatter preserves the operational
    payload as copy-friendly plain text.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    payload: dict[str, Any] = {
        "timestamp": timestamp,
        "command": command_line,
        "tool": result.tool,
        "success": result.success,
        "errors": result.errors,
        "data": result.data or {},
        "metadata": result.metadata or {},
    }
    return json.dumps(payload, indent=2, ensure_ascii=False, default=str)


def workspace_tui_dir(workspace_path: str | Path) -> Path:
    """Return the workspace-local folder for TUI transcript artifacts."""
    return Path(workspace_path).expanduser().resolve() / ".dr-magu" / "tui"


def write_text_artifact(workspace_path: str | Path, filename: str, text: str) -> Path:
    """Persist copyable text under the workspace TUI artifact folder."""
    folder = workspace_tui_dir(workspace_path)
    folder.mkdir(parents=True, exist_ok=True)
    output_path = folder / filename
    output_path.write_text(text, encoding="utf-8")
    return output_path


def _run_clipboard_command(command: list[str], text: str) -> bool:
    try:
        subprocess.run(command, input=text, text=True, check=True, capture_output=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError, OSError):
        return False


def copy_text_to_clipboard(text: str) -> ClipboardResult:
    """Copy text to the OS clipboard using optional and native providers.

    This avoids a mandatory dependency. It supports pyperclip when installed,
    Windows clip, macOS pbcopy, and common Linux clipboard tools.
    """
    if not text:
        return ClipboardResult(False, "Nothing to copy.")

    try:  # pragma: no cover - depends on optional user environment
        import pyperclip  # type: ignore

        pyperclip.copy(text)
        return ClipboardResult(True, "Copied to clipboard using pyperclip.")
    except Exception:
        pass

    system = platform.system().lower()
    if system == "windows":
        if _run_clipboard_command(["clip"], text):
            return ClipboardResult(True, "Copied to Windows clipboard.")
        return ClipboardResult(False, "Windows clipboard command 'clip' was not available.")

    if system == "darwin":
        if _run_clipboard_command(["pbcopy"], text):
            return ClipboardResult(True, "Copied to macOS clipboard.")
        return ClipboardResult(False, "macOS clipboard command 'pbcopy' was not available.")

    for candidate in (["wl-copy"], ["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"]):
        if shutil.which(candidate[0]) and _run_clipboard_command(candidate, text):
            return ClipboardResult(True, f"Copied to clipboard using {candidate[0]}.")

    return ClipboardResult(
        False,
        "No clipboard provider found. Use /export-log to write the transcript to a file.",
    )

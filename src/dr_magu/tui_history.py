from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SessionCommandHistory:
    """In-memory command history for a single TUI session.

    The history is intentionally not persisted to disk. It only exists while the
    Terminal UI process is running.
    """

    _commands: list[str] = field(default_factory=list)
    _cursor: int | None = None

    def add(self, command: str) -> None:
        normalized = command.strip()
        if not normalized:
            return

        if self._commands and self._commands[-1] == normalized:
            self._cursor = None
            return

        self._commands.append(normalized)
        self._cursor = None

    def previous(self) -> str | None:
        if not self._commands:
            return None

        if self._cursor is None:
            self._cursor = len(self._commands) - 1
        else:
            self._cursor = max(0, self._cursor - 1)

        return self._commands[self._cursor]

    def next(self) -> str | None:
        if not self._commands or self._cursor is None:
            return None

        if self._cursor >= len(self._commands) - 1:
            self._cursor = None
            return ""

        self._cursor += 1
        return self._commands[self._cursor]

    def reset_navigation(self) -> None:
        self._cursor = None

    @property
    def count(self) -> int:
        return len(self._commands)

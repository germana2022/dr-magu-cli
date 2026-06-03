from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PermissionGuard:
    blocked_shell_patterns: list[str] = field(default_factory=list)

    def validate_shell_command(self, command: str) -> None:
        normalized = command.lower().strip()
        for pattern in self.blocked_shell_patterns:
            if pattern.lower() in normalized:
                raise PermissionError(f"Shell command blocked by policy: {pattern}")

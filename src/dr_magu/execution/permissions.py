from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExecutionPermissions:
    """Execution permission profile."""

    filesystem_read: bool = True
    filesystem_write: bool = True
    filesystem_delete: bool = False
    terminal_execute: bool = True
    git_read: bool = True
    git_commit: bool = True
    git_push: bool = False
    network_outbound: bool = False

    def is_allowed(self, action_type: str) -> bool:
        mapping = {
            "filesystem.read": self.filesystem_read,
            "filesystem.write": self.filesystem_write,
            "filesystem.delete": self.filesystem_delete,
            "terminal.run": self.terminal_execute,
            "git.status": self.git_read,
            "git.diff": self.git_read,
            "git.log": self.git_read,
            "git.branch": self.git_read,
            "git.commit": self.git_commit,
            "git.push": self.git_push,
        }
        return bool(mapping.get(action_type, False))

    def requires_approval(self, action_type: str) -> bool:
        return action_type in {
            "filesystem.write",
            "filesystem.delete",
            "terminal.run",
            "git.commit",
            "git.push",
        }

    def to_dict(self) -> dict:
        return {
            "filesystem": {
                "read": self.filesystem_read,
                "write": self.filesystem_write,
                "delete": self.filesystem_delete,
            },
            "terminal": {"execute": self.terminal_execute},
            "git": {"read": self.git_read, "commit": self.git_commit, "push": self.git_push},
            "network": {"outbound": self.network_outbound},
        }

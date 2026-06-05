from __future__ import annotations

from typing import Any

from dr_magu.contracts.models import PermissionMode, RiskLevel
from dr_magu.runtime.models import PermissionRuntimeInfo


_DEFAULT_POLICIES: dict[str, dict[str, Any]] = {
    "files.list": {"mode": PermissionMode.allowed.value, "risk_level": RiskLevel.low.value, "background_allowed": True},
    "files.read": {"mode": PermissionMode.allowed.value, "risk_level": RiskLevel.low.value, "background_allowed": True},
    "search.code": {"mode": PermissionMode.allowed.value, "risk_level": RiskLevel.low.value, "background_allowed": True},
    "git.status": {"mode": PermissionMode.allowed.value, "risk_level": RiskLevel.low.value, "background_allowed": True},
    "git.diff": {"mode": PermissionMode.allowed.value, "risk_level": RiskLevel.low.value, "background_allowed": True},
    "repo.scan": {"mode": PermissionMode.allowed.value, "risk_level": RiskLevel.low.value, "background_allowed": True},
    "context.generate": {"mode": PermissionMode.allowed.value, "risk_level": RiskLevel.medium.value, "background_allowed": True},
    "workflow.run": {"mode": PermissionMode.allowed.value, "risk_level": RiskLevel.medium.value, "background_allowed": True},
    "agent.run": {"mode": PermissionMode.allowed.value, "risk_level": RiskLevel.medium.value, "background_allowed": True},
    "shell.run": {"mode": PermissionMode.approval_required.value, "risk_level": RiskLevel.high.value, "background_allowed": False},
    "git.push": {"mode": PermissionMode.blocked.value, "risk_level": RiskLevel.critical.value, "background_allowed": False},
    "files.delete": {"mode": PermissionMode.blocked.value, "risk_level": RiskLevel.critical.value, "background_allowed": False},
}


class PermissionContextReader:
    """Builds a permission summary for the Brain and plan validator."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

    def read(self) -> PermissionRuntimeInfo:
        permissions = self.config.get("permissions", {}) or {}
        configured_policies = self.config.get("permission_policies", {}) or {}
        policies = dict(_DEFAULT_POLICIES)
        for name, policy in configured_policies.items():
            if isinstance(policy, dict):
                policies[name] = {**policies.get(name, {}), **policy}

        return PermissionRuntimeInfo(
            file_read=bool(permissions.get("file_read", False)),
            file_write=bool(permissions.get("file_write", False)),
            file_delete=bool(permissions.get("file_delete", False)),
            shell_run=bool(permissions.get("shell_run", False)),
            git_status=bool(permissions.get("git_status", False)),
            git_diff=bool(permissions.get("git_diff", False)),
            git_commit=bool(permissions.get("git_commit", False)),
            git_push=bool(permissions.get("git_push", False)),
            blocked_shell_patterns=list(self.config.get("blocked_shell_patterns", []) or []),
            policies=policies,
            default_policy_mode=PermissionMode.allowed.value,
        )

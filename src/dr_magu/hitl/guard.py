from __future__ import annotations

from typing import Any

from .engine import ApprovalEngine


RISKY_ACTIONS = {
    "file.write",
    "file.delete",
    "git.push",
    "email.send",
    "shell.run",
    "website.generate",
}


def requires_approval(action: str, risk_level: str | None = None) -> bool:
    """Return whether an action should require explicit human approval."""
    normalized = action.strip().lower()
    if normalized in RISKY_ACTIONS:
        return True
    if (risk_level or "").lower() in {"high", "critical"}:
        return True
    return False


def ensure_approval_or_request(
    workspace_path: str,
    action: str,
    title: str,
    description: str,
    risk_level: str = "medium",
) -> dict[str, Any]:
    """Create an approval request when an action requires human approval."""
    if not requires_approval(action, risk_level):
        return {
            "requires_approval": False,
            "approval": None,
        }

    result = ApprovalEngine(workspace_path).request(
        title=title,
        description=description,
        action=action,
        risk_level=risk_level,
    )
    return {
        "requires_approval": True,
        "approval": result.data["approval"] if result.success else None,
    }

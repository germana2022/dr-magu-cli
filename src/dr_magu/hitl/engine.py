from __future__ import annotations

from pathlib import Path

from dr_magu.result import ToolResult

from .models import ApprovalOption, ApprovalRequest
from .store import ApprovalStore


class ApprovalEngine:
    """Create and resolve human-in-the-loop approval requests."""

    def __init__(self, workspace_path: str | Path):
        self.workspace_path = Path(workspace_path).resolve()
        self.store = ApprovalStore(self.workspace_path)

    def request(
        self,
        title: str,
        description: str,
        action: str,
        risk_level: str = "medium",
        options: list[ApprovalOption] | None = None,
    ) -> ToolResult:
        if not title.strip():
            return ToolResult(success=False, tool="approval.request", errors=["Approval title is required."])

        approval = ApprovalRequest.create(
            title=title.strip(),
            description=description.strip(),
            action=action.strip(),
            risk_level=risk_level.strip() or "medium",
            options=options,
        )
        path = self.store.save(approval)
        return ToolResult(
            success=True,
            tool="approval.request",
            data={
                "approval": approval.to_dict(),
                "output_path": str(path),
            },
        )

    def approve(self, request_id: str, selected_option_id: str | None = None) -> ToolResult:
        approval = self.store.get(request_id)
        resolved = approval.approve(selected_option_id=selected_option_id)
        path = self.store.save(resolved)
        return ToolResult(
            success=True,
            tool="approval.approve",
            data={
                "approval": resolved.to_dict(),
                "output_path": str(path),
            },
        )

    def reject(self, request_id: str) -> ToolResult:
        approval = self.store.get(request_id)
        resolved = approval.reject()
        path = self.store.save(resolved)
        return ToolResult(
            success=True,
            tool="approval.reject",
            data={
                "approval": resolved.to_dict(),
                "output_path": str(path),
            },
        )

    def list(self, include_resolved: bool = True) -> ToolResult:
        approvals = self.store.list(include_resolved=include_resolved)
        return ToolResult(
            success=True,
            tool="approval.list",
            data={
                "count": len(approvals),
                "approvals": [approval.to_dict() for approval in approvals],
            },
        )

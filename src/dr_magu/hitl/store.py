from __future__ import annotations

import json
from pathlib import Path

from .models import ApprovalRequest


class ApprovalStore:
    """Persist approval requests inside the workspace .dr-magu directory."""

    def __init__(self, workspace_path: str | Path):
        self.workspace_path = Path(workspace_path).resolve()
        self.approvals_dir = self.workspace_path / ".dr-magu" / "approvals"

    def save(self, request: ApprovalRequest) -> Path:
        self.approvals_dir.mkdir(parents=True, exist_ok=True)
        output_path = self.approvals_dir / f"{request.id}.json"
        output_path.write_text(json.dumps(request.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        return output_path

    def get(self, request_id: str) -> ApprovalRequest:
        path = self.approvals_dir / f"{request_id}.json"
        if not path.exists():
            raise KeyError(f"Unknown approval request: {request_id}")

        payload = json.loads(path.read_text(encoding="utf-8"))
        from .models import ApprovalOption

        return ApprovalRequest(
            id=payload["id"],
            title=payload["title"],
            description=payload["description"],
            action=payload["action"],
            risk_level=payload.get("risk_level", "medium"),
            status=payload.get("status", "pending"),
            options=[
                ApprovalOption(
                    id=option["id"],
                    title=option["title"],
                    description=option.get("description", ""),
                    metadata=option.get("metadata", {}),
                )
                for option in payload.get("options", [])
            ],
            selected_option_id=payload.get("selected_option_id"),
            created_at=payload.get("created_at"),
            resolved_at=payload.get("resolved_at"),
            metadata=payload.get("metadata", {}),
        )

    def list(self, include_resolved: bool = True) -> list[ApprovalRequest]:
        if not self.approvals_dir.exists():
            return []

        requests = [self.get(path.stem) for path in sorted(self.approvals_dir.glob("*.json"))]
        if include_resolved:
            return requests
        return [request for request in requests if request.status == "pending"]

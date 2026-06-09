from pathlib import Path

from dr_magu.commands.context import CommandContext
from dr_magu.commands.processor import CommandProcessor
from dr_magu.commands.registry import registry
from dr_magu.hitl.engine import ApprovalEngine
from dr_magu.hitl.guard import ensure_approval_or_request, requires_approval
from dr_magu.hitl.models import APPROVAL_APPROVED, APPROVAL_REJECTED, ApprovalOption
from dr_magu.plugins.registry import PluginRegistry


def test_approval_engine_creates_and_persists_request(tmp_path: Path):
    result = ApprovalEngine(tmp_path).request(
        title="Approve website architecture",
        description="Select a generated architecture option.",
        action="website.generate",
        risk_level="high",
        options=[ApprovalOption(id="nextjs", title="Next.js Architecture")],
    )

    assert result.success is True
    approval = result.data["approval"]
    assert approval["status"] == "pending"
    assert (tmp_path / ".dr-magu" / "approvals" / f"{approval['id']}.json").exists()


def test_approval_engine_approves_request(tmp_path: Path):
    engine = ApprovalEngine(tmp_path)
    created = engine.request("Approve action", "Description", "manual.review")
    request_id = created.data["approval"]["id"]

    approved = engine.approve(request_id)

    assert approved.success is True
    assert approved.data["approval"]["status"] == APPROVAL_APPROVED


def test_approval_engine_rejects_request(tmp_path: Path):
    engine = ApprovalEngine(tmp_path)
    created = engine.request("Reject action", "Description", "manual.review")
    request_id = created.data["approval"]["id"]

    rejected = engine.reject(request_id)

    assert rejected.success is True
    assert rejected.data["approval"]["status"] == APPROVAL_REJECTED


def test_approval_guard_requires_sensitive_actions():
    assert requires_approval("git.push") is True
    assert requires_approval("repo.scan") is False
    assert requires_approval("anything", "critical") is True


def test_approval_guard_creates_request_for_sensitive_action(tmp_path: Path):
    result = ensure_approval_or_request(
        workspace_path=str(tmp_path),
        action="website.generate",
        title="Approve website generation",
        description="Sensitive generation step",
        risk_level="high",
    )

    assert result["requires_approval"] is True
    assert result["approval"]["action"] == "website.generate"


def test_command_processor_routes_approval_request(tmp_path: Path):
    context = CommandContext(workspace_path=str(tmp_path), output_format="human", config={})
    result = CommandProcessor(registry).execute_line("approval.request TestApproval", context)

    assert result.success is True
    assert result.data["approval"]["title"] == "TestApproval"


def test_approval_plugin_is_discovered():
    plugins = PluginRegistry(".").list()
    assert any(plugin.id == "approval" for plugin in plugins)

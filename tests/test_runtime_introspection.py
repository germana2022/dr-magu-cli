from __future__ import annotations

from dr_magu.commands.context import CommandContext
from dr_magu.commands.processor import CommandProcessor
from dr_magu.commands.registry import registry
from dr_magu.runtime.inspector import RuntimeInspector
from dr_magu.sessions.manager import SessionManager


def test_runtime_inspector_exposes_brain_ready_snapshot(tmp_path):
    SessionManager(tmp_path).start()

    snapshot = RuntimeInspector(str(tmp_path)).inspect()

    assert snapshot.workspace.exists is True
    assert snapshot.workspace.is_directory is True
    assert snapshot.session.id is not None
    assert any(command.name == "runtime.inspect" for command in snapshot.commands)
    assert any(workflow.name == "repository.context" for workflow in snapshot.workflows)
    assert any(tool.name == "files.list" for tool in snapshot.tools)
    assert snapshot.permissions.file_read is True
    assert snapshot.summary["brain_ready"] is True
    assert snapshot.summary["agent_count"] >= 1


def test_runtime_inspect_command_processor_result(tmp_path):
    context = CommandContext(workspace_path=str(tmp_path), output_format="human", config={})
    result = CommandProcessor(registry).execute("runtime.inspect", {}, context)

    assert result.success is True
    assert result.tool == "runtime.inspect"
    assert result.data is not None
    assert result.data["summary"]["brain_ready"] is True
    assert "commands" in result.data
    assert "workflows" in result.data
    assert "tools" in result.data
    assert "agents" in result.data


def test_runtime_inspector_reads_permission_config(tmp_path):
    config = {
        "permissions": {
            "file_read": True,
            "shell_run": True,
            "git_status": True,
        },
        "blocked_shell_patterns": ["rm -rf"],
    }

    snapshot = RuntimeInspector(str(tmp_path), config=config).inspect()

    assert snapshot.permissions.file_read is True
    assert snapshot.permissions.shell_run is True
    assert snapshot.permissions.git_status is True
    assert snapshot.permissions.blocked_shell_patterns == ["rm -rf"]

from pathlib import Path

from dr_magu.commands.context import CommandContext
from dr_magu.commands.processor import CommandProcessor
from dr_magu.commands.registry import registry
from dr_magu.execution.executor import ExecutionExecutor
from dr_magu.execution.filesystem_runtime import FilesystemRuntime
from dr_magu.execution.git_runtime import GitRuntime
from dr_magu.execution.models import PLAN_BLOCKED, PLAN_COMPLETED
from dr_magu.execution.permissions import ExecutionPermissions
from dr_magu.execution.planner import ExecutionPlanner
from dr_magu.execution.terminal_runtime import TerminalRuntime
from dr_magu.plugins.registry import PluginRegistry


def test_execution_permissions_defaults_are_safe():
    permissions = ExecutionPermissions()

    assert permissions.is_allowed("filesystem.read") is True
    assert permissions.is_allowed("filesystem.write") is True
    assert permissions.is_allowed("filesystem.delete") is False
    assert permissions.is_allowed("git.push") is False
    assert permissions.requires_approval("terminal.run") is True


def test_filesystem_runtime_writes_and_reads_inside_workspace(tmp_path: Path):
    runtime = FilesystemRuntime(tmp_path)

    write = runtime.write("docs/demo.md", "hello")
    read = runtime.read("docs/demo.md")

    assert write.success is True
    assert read.success is True
    assert read.data["content"] == "hello"


def test_filesystem_runtime_blocks_workspace_escape(tmp_path: Path):
    result = FilesystemRuntime(tmp_path).write("../outside.md", "blocked")

    assert result.success is False


def test_terminal_runtime_runs_command(tmp_path: Path):
    result = TerminalRuntime(tmp_path).run("echo hello")

    assert result.tool == "terminal.run"
    assert result.success is True
    assert "hello" in result.data["stdout"]


def test_git_runtime_status_returns_tool_result(tmp_path: Path):
    result = GitRuntime(tmp_path).status()

    assert result.tool == "git.status"
    assert result.success in {True, False}


def test_execution_planner_creates_file_plan(tmp_path: Path):
    result = ExecutionPlanner(tmp_path).simple_file_plan("docs/plan.md", "hello")

    assert result.success is True
    plan = result.data["plan"]
    assert plan["actions"][0]["type"] == "filesystem.write"
    assert plan["actions"][0]["requires_approval"] is True
    assert Path(result.data["output_path"]).exists()


def test_execution_executor_requests_approval_when_not_approved(tmp_path: Path):
    created = ExecutionPlanner(tmp_path).simple_file_plan("docs/approved.md", "hello")
    plan_id = created.data["plan"]["plan_id"]

    result = ExecutionExecutor(tmp_path).execute(plan_id, approved=False)

    assert result.success is True
    assert result.data["plan"]["status"] == PLAN_BLOCKED
    assert result.data["plan"]["approval_id"]


def test_execution_executor_executes_approved_plan(tmp_path: Path):
    created = ExecutionPlanner(tmp_path).simple_file_plan("docs/run.md", "hello")
    plan_id = created.data["plan"]["plan_id"]

    result = ExecutionExecutor(tmp_path).execute(plan_id, approved=True)

    assert result.success is True
    assert result.data["plan"]["status"] == PLAN_COMPLETED
    assert (tmp_path / "docs" / "run.md").exists()


def test_execution_inspect_and_list(tmp_path: Path):
    created = ExecutionPlanner(tmp_path).simple_file_plan("docs/list.md", "hello")
    plan_id = created.data["plan"]["plan_id"]
    ExecutionExecutor(tmp_path).execute(plan_id, approved=True)

    inspect = ExecutionExecutor(tmp_path).inspect(plan_id)
    listed = ExecutionExecutor(tmp_path).list_plans()

    assert inspect.success is True
    assert inspect.data["event_count"] > 0
    assert listed.data["count"] == 1


def test_command_processor_routes_execution_plan_create(tmp_path: Path):
    context = CommandContext(workspace_path=str(tmp_path), output_format="human", config={})
    result = CommandProcessor(registry).execute_line("execution.plan.create demo.md --content hello", context)

    assert result.success is True
    assert result.data["plan"]["actions"][0]["type"] == "filesystem.write"


def test_execution_runtime_plugin_is_discovered():
    plugins = PluginRegistry(".").list()
    assert any(plugin.id == "execution-runtime" for plugin in plugins)

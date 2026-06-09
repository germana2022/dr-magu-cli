from pathlib import Path

from dr_magu.commands.context import CommandContext
from dr_magu.commands.processor import CommandProcessor
from dr_magu.commands.registry import registry
from dr_magu.plugins.registry import PluginRegistry
from dr_magu.scheduler.models import SCHEDULE_DELETED, SCHEDULE_DISABLED, estimate_next_run
from dr_magu.scheduler.runtime import SchedulerRuntime


def test_estimate_next_run_supports_shortcuts():
    assert estimate_next_run("@daily")
    assert estimate_next_run("@hourly")


def test_scheduler_runtime_creates_and_lists_schedule(tmp_path: Path):
    runtime = SchedulerRuntime(tmp_path)

    created = runtime.create("daily-research", "research.search LangGraph", "@daily")
    listed = runtime.list()

    assert created.success is True
    assert listed.data["count"] == 1
    assert listed.data["tasks"][0]["name"] == "daily-research"


def test_scheduler_runtime_disable_enable_and_delete(tmp_path: Path):
    runtime = SchedulerRuntime(tmp_path)
    created = runtime.create("daily-report", "report.create DailyReport", "@daily")
    task_id = created.data["task"]["id"]

    disabled = runtime.disable(task_id)
    enabled = runtime.enable(task_id)
    deleted = runtime.delete(task_id)

    assert disabled.data["task"]["status"] == SCHEDULE_DISABLED
    assert enabled.data["task"]["enabled"] is True
    assert deleted.data["task"]["status"] == SCHEDULE_DELETED
    assert runtime.list().data["count"] == 0
    assert runtime.list(include_deleted=True).data["count"] == 1


def test_scheduler_runtime_run_once_executes_command(tmp_path: Path):
    runtime = SchedulerRuntime(tmp_path)
    created = runtime.create("run-research", "research.search LangGraph", "@daily")
    task_id = created.data["task"]["id"]

    result = runtime.run_once(task_id)

    assert result.success is True
    assert result.data["command_result"]["success"] is True
    assert result.data["task"]["last_run_at"]


def test_command_processor_routes_schedule_create_and_list(tmp_path: Path):
    context = CommandContext(workspace_path=str(tmp_path), output_format="human", config={})
    processor = CommandProcessor(registry)

    created = processor.execute_line("schedule.create daily-test --command research.search", context)
    listed = processor.execute_line("schedule.list", context)

    assert created.success is True
    assert listed.success is True
    assert listed.data["count"] == 1


def test_scheduler_plugin_is_discovered():
    plugins = PluginRegistry(".").list()
    assert any(plugin.id == "scheduler" for plugin in plugins)

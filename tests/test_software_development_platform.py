from pathlib import Path

from dr_magu.commands.context import CommandContext
from dr_magu.commands.processor import CommandProcessor
from dr_magu.commands.registry import registry
from dr_magu.filesystem_tools.runner import FilesystemToolRunner
from dr_magu.git_tools.runner import GitToolRunner
from dr_magu.plugins.registry import PluginRegistry
from dr_magu.sdlc.agents import SoftwareAgentRunner
from dr_magu.shell_tools.runner import ShellToolRunner


def test_sdlc_agent_list_contains_expected_agents(tmp_path: Path):
    result = SoftwareAgentRunner(tmp_path).list_agents()
    ids = {agent["id"] for agent in result.data["agents"]}

    assert result.success is True
    assert "repository-analyzer" in ids
    assert "architecture-planner" in ids
    assert "release-notes-generator" in ids


def test_sdlc_agent_run_generates_artifact(tmp_path: Path):
    (tmp_path / "README.md").write_text("# Demo", encoding="utf-8")

    result = SoftwareAgentRunner(tmp_path).run("repository-analyzer")

    assert result.success is True
    assert Path(result.data["artifact"]["path"]).exists()
    assert result.data["artifact"]["agent_id"] == "repository-analyzer"


def test_filesystem_tools_are_workspace_scoped(tmp_path: Path):
    fs = FilesystemToolRunner(tmp_path)

    write_result = fs.write("docs/test.md", "hello")
    read_result = fs.read("docs/test.md")
    list_result = fs.list("docs")

    assert write_result.success is True
    assert read_result.data["content"] == "hello"
    assert "test.md" in list_result.data["items"]


def test_filesystem_tools_reject_workspace_escape(tmp_path: Path):
    result = FilesystemToolRunner(tmp_path).read("../outside.txt")

    assert result.success is False


def test_shell_run_requires_approval(tmp_path: Path):
    result = ShellToolRunner(tmp_path).run("echo hello", approved=False)

    assert result.success is False
    assert result.data["requires_approval"] is True


def test_git_status_returns_tool_result(tmp_path: Path):
    result = GitToolRunner(tmp_path).run("status")

    assert result.tool == "git.status"
    assert result.success in {True, False}


def test_command_processor_routes_sdlc_agent_run(tmp_path: Path):
    context = CommandContext(workspace_path=str(tmp_path), output_format="human", config={})
    result = CommandProcessor(registry).execute_line("sdlc.agent.run repository-analyzer", context)

    assert result.success is True
    assert Path(result.data["artifact"]["path"]).exists()


def test_software_development_plugin_is_discovered():
    plugins = PluginRegistry(".").list()
    assert any(plugin.id == "software-development" for plugin in plugins)

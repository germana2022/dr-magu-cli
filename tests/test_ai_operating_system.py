from typer.testing import CliRunner

from dr_magu.ai_os.capabilities import AI_OS_CAPABILITIES, AI_OS_LAYERS
from dr_magu.ai_os.runtime import AIOperatingSystem
from dr_magu.cli import app
from dr_magu.commands.context import CommandContext
from dr_magu.commands.processor import CommandProcessor
from dr_magu.commands.registry import registry
from dr_magu.plugins.registry import PluginRegistry


def test_ai_os_layers_are_registered():
    assert "conversation" in AI_OS_LAYERS
    assert "self_healing" in AI_OS_LAYERS
    assert "software_factory" in AI_OS_LAYERS
    assert len(AI_OS_CAPABILITIES) >= 10


def test_ai_os_status(tmp_path):
    result = AIOperatingSystem(tmp_path).status()

    assert result.success is True
    assert result.tool == "os.status"
    assert result.data["version"] == "2.0.0"
    assert result.data["health"]["ready"] is True


def test_ai_os_capabilities(tmp_path):
    result = AIOperatingSystem(tmp_path).capabilities()

    assert result.success is True
    assert result.data["count"] >= 10
    assert any(item["id"] == "factory" for item in result.data["capabilities"])


def test_ai_os_dispatch(tmp_path):
    result = AIOperatingSystem(tmp_path).dispatch("files.list")

    assert result.success is True
    assert result.tool == "os.dispatch"
    assert result.data["result"]["tool"] == "files.list"


def test_os_status_command(tmp_path):
    context = CommandContext(workspace_path=str(tmp_path), output_format="human", config={})

    result = CommandProcessor(registry).execute_line("os.status", context)

    assert result.success is True
    assert result.data["version"] == "2.0.0"


def test_os_dispatch_command(tmp_path):
    context = CommandContext(workspace_path=str(tmp_path), output_format="human", config={})

    result = CommandProcessor(registry).execute_line("os.dispatch files.list", context)

    assert result.success is True
    assert result.data["result"]["tool"] == "files.list"


def test_cli_exposes_os_commands():
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "os-status" in result.output
    assert "os-capabilities" in result.output
    assert "os-boot" in result.output


def test_ai_os_plugin_is_discovered():
    plugins = PluginRegistry(".").list()

    assert any(plugin.id == "ai-operating-system" for plugin in plugins)

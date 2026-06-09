from pathlib import Path

from dr_magu.commands.context import CommandContext
from dr_magu.commands.processor import CommandProcessor
from dr_magu.commands.registry import registry
from dr_magu.plugins.registry import PluginRegistry
from dr_magu.website_builder.workflow import WebsiteBuilderWorkflow


def test_website_builder_workflow_generates_artifacts(tmp_path: Path):
    result = WebsiteBuilderWorkflow(tmp_path).generate("AI developer tools landing page", research_limit=3)

    assert result.success is True
    data = result.data["result"]
    assert data["status"] == "waiting_for_approval"
    assert data["approval_id"]
    assert Path(data["proposal_path"]).exists()
    assert Path(data["architecture_options_path"]).exists()
    assert Path(result.data["result_path"]).exists()
    assert len(data["architecture_options"]) == 4


def test_website_builder_creates_custom_user_option(tmp_path: Path):
    result = WebsiteBuilderWorkflow(tmp_path).generate("CRM website", research_limit=2)

    option_ids = {option["id"] for option in result.data["result"]["architecture_options"]}

    assert "custom-user-option" in option_ids


def test_website_builder_command_processor_route(tmp_path: Path):
    context = CommandContext(workspace_path=str(tmp_path), output_format="human", config={})
    result = CommandProcessor(registry).execute_line("website.build CRM", context)

    assert result.success is True
    assert result.data["result"]["topic"] == "CRM"


def test_website_builder_plugin_is_discovered():
    plugins = PluginRegistry(".").list()
    assert any(plugin.id == "website-builder" for plugin in plugins)

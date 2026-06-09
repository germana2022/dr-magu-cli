from pathlib import Path

from dr_magu.commands.context import CommandContext
from dr_magu.commands.processor import CommandProcessor
from dr_magu.commands.registry import registry
from dr_magu.plugins.registry import PluginRegistry
from dr_magu.reports.generator import ReportGenerator
from dr_magu.reports.models import ReportDocument, ReportSection
from dr_magu.reports.renderers import HtmlReportRenderer, MarkdownReportRenderer
from dr_magu.research.runner import WebResearchRunner


def test_markdown_report_renderer_outputs_title():
    document = ReportDocument(
        title="Test Report",
        summary="Test summary",
        sections=[ReportSection(title="Details", body="Body")],
    )

    output = MarkdownReportRenderer().render(document)

    assert "# Test Report" in output
    assert "## Details" in output


def test_html_report_renderer_outputs_html_document():
    document = ReportDocument(title="HTML Report", summary="HTML summary")

    output = HtmlReportRenderer().render(document)

    assert "<!doctype html>" in output
    assert "HTML Report" in output


def test_report_generator_persists_outputs(tmp_path: Path):
    result = ReportGenerator(tmp_path).generate(
        title="Executive Summary",
        summary="Generated summary",
        sections=[ReportSection(title="Findings", body="Finding body")],
    )

    assert result.success is True
    outputs = result.data["outputs"]
    assert Path(outputs["markdown"]).exists()
    assert Path(outputs["html"]).exists()
    assert Path(outputs["json"]).exists()


def test_report_from_latest_research(tmp_path: Path):
    WebResearchRunner(tmp_path).search("LangGraph", limit=2)

    result = ReportGenerator(tmp_path).generate_from_latest_research()

    assert result.success is True
    assert result.data["title"] == "Research Report: LangGraph"


def test_command_processor_routes_report_create(tmp_path: Path):
    context = CommandContext(workspace_path=str(tmp_path), output_format="human", config={})
    result = CommandProcessor(registry).execute_line("report.create TestReport", context)

    assert result.success is True
    assert result.data["title"] == "TestReport"


def test_reporting_plugin_is_discovered():
    plugins = PluginRegistry(".").list()
    assert any(plugin.id == "reporting" for plugin in plugins)

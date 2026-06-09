from __future__ import annotations

import typer
from dr_magu.workflow_engine.runtime import WorkflowRuntime
from dr_magu.workflow_engine.runner import WorkflowRunner
from dr_magu.website_builder.workflow import WebsiteBuilderWorkflow
from dr_magu.filesystem_tools.runner import FilesystemToolRunner
from dr_magu.shell_tools.runner import ShellToolRunner
from dr_magu.git_tools.runner import GitToolRunner
from dr_magu.sdlc.agents import SoftwareAgentRunner
from dr_magu.scheduler.runtime import SchedulerRuntime
from dr_magu.research.runner import WebResearchRunner
from dr_magu.brain.commands import brain_plan, brain_execute, brain_route, render_brain_result
from rich.console import Console
from rich.table import Table

from dr_magu.commands.context import CommandContext
from dr_magu.commands.processor import CommandProcessor
from dr_magu.commands.registry import registry
from dr_magu.config import default_workspace, load_config
from dr_magu.output.renderer import ResultRenderer
from dr_magu.sessions.manager import SessionManager
from dr_magu.scanner.models import RepositoryScan
from dr_magu.scanner.writers import write_latest_scan
from dr_magu.project_context.generator import generate_project_context, get_context_path, show_project_context
from dr_magu.workflows.runner import WorkflowRunner
from dr_magu.runtime.inspector import RuntimeInspector
from dr_magu.agents.runner import AgentRunner
from dr_magu.brain.context_loader import BrainContextLoader
from dr_magu.tools.registry import ToolRegistry
from dr_magu.security.permission_context import PermissionContextReader
from dr_magu.plugins.manager import PluginManager
from dr_magu.control_center.service import ControlCenterService
from dr_magu.plans.models import BrainPlan, PlanStep
from dr_magu.plans.validator import PlanValidator

app = typer.Typer(help="Dr Magu CLI - Tool CLI, TUI, sessions, repository scanner, context generator, workflows, runtime introspection, and Brain foundation")
files_app = typer.Typer(help="File system tools")
search_app = typer.Typer(help="Code search tools")
git_app = typer.Typer(help="Git tools")
shell_app = typer.Typer(help="Shell execution tools")
commands_app = typer.Typer(help="Command registry tools")
session_app = typer.Typer(help="Persistent session management")
context_app = typer.Typer(help="Deterministic project context generation")
workflow_app = typer.Typer(help="Deterministic workflow runtime, and runtime introspection")
runtime_app = typer.Typer(help="Runtime introspection tools")
agent_app = typer.Typer(help="Agent registry tools")
brain_app = typer.Typer(help="Brain context loader tools")
tools_app = typer.Typer(help="Formal tool registry tools")
permissions_app = typer.Typer(help="Permission context tools")
plugin_app = typer.Typer(help="Local plugin registry tools")
control_app = typer.Typer(help="Dr Magu Control Center tools")
contracts_app = typer.Typer(help="Runtime contract inspection tools")
plan_app = typer.Typer(help="Brain plan validation tools")

app.add_typer(files_app, name="files")
app.add_typer(search_app, name="search")
app.add_typer(git_app, name="git")
app.add_typer(shell_app, name="shell")
app.add_typer(commands_app, name="commands")
app.add_typer(session_app, name="session")
app.add_typer(context_app, name="context")
app.add_typer(workflow_app, name="workflow")
app.add_typer(runtime_app, name="runtime")
app.add_typer(agent_app, name="agent")
app.add_typer(brain_app, name="brain")
app.add_typer(tools_app, name="tools")
app.add_typer(permissions_app, name="permissions")
app.add_typer(plugin_app, name="plugin")
app.add_typer(control_app, name="control")
app.add_typer(contracts_app, name="contracts")
app.add_typer(plan_app, name="plan")

console = Console()
renderer = ResultRenderer(console)
processor = CommandProcessor(registry)


def build_context(workspace: str, json_output: bool = False) -> CommandContext:
    return CommandContext(
        workspace_path=workspace,
        output_format="json" if json_output else "human",
        config=load_config(),
    )


def _render_session_metadata(metadata, title: str = "Session") -> None:
    table = Table(title=title)
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("ID", metadata.id)
    table.add_row("Workspace", metadata.workspace_path)
    table.add_row("Status", metadata.status)
    table.add_row("Commands", str(metadata.command_count))
    table.add_row("Events", str(metadata.event_count))
    table.add_row("Created", metadata.created_at)
    table.add_row("Updated", metadata.updated_at)
    console.print(table)


@session_app.command("start")
def session_start(
    workspace: str = typer.Option(default_workspace(), "--workspace", "-w", help="Workspace root."),
) -> None:
    """Create a new persistent session and make it current."""
    metadata = SessionManager(workspace).start()
    _render_session_metadata(metadata, "Started Session")


@session_app.command("current")
def session_current(
    workspace: str = typer.Option(default_workspace(), "--workspace", "-w", help="Workspace root."),
) -> None:
    """Show the current persistent session."""
    metadata = SessionManager(workspace).current()
    if metadata is None:
        console.print("[yellow]No current session found.[/]")
        return
    _render_session_metadata(metadata, "Current Session")


@session_app.command("list")
def session_list(
    workspace: str = typer.Option(default_workspace(), "--workspace", "-w", help="Workspace root."),
) -> None:
    """List persistent sessions for the workspace."""
    sessions = SessionManager(workspace).list()
    table = Table(title="Persistent Sessions")
    table.add_column("ID")
    table.add_column("Status")
    table.add_column("Commands")
    table.add_column("Updated")
    for metadata in sessions:
        table.add_row(metadata.id, metadata.status, str(metadata.command_count), metadata.updated_at)
    console.print(table)


@session_app.command("show")
def session_show(
    session_id: str = typer.Argument(..., help="Session ID to inspect."),
    workspace: str = typer.Option(default_workspace(), "--workspace", "-w", help="Workspace root."),
) -> None:
    """Show one persistent session by ID."""
    metadata = SessionManager(workspace).show(session_id)
    _render_session_metadata(metadata, "Session Details")


@session_app.command("resume")
def session_resume(
    session_id: str = typer.Argument(..., help="Session ID to resume."),
    workspace: str = typer.Option(default_workspace(), "--workspace", "-w", help="Workspace root."),
) -> None:
    """Set an existing session as the current session."""
    metadata = SessionManager(workspace).resume(session_id)
    _render_session_metadata(metadata, "Resumed Session")


@session_app.command("close")
def session_close(
    workspace: str = typer.Option(default_workspace(), "--workspace", "-w", help="Workspace root."),
) -> None:
    """Close the current persistent session."""
    metadata = SessionManager(workspace).close_current()
    if metadata is None:
        console.print("[yellow]No current session found.[/]")
        return
    _render_session_metadata(metadata, "Closed Session")


@session_app.command("delete")
def session_delete(
    session_id: str = typer.Argument(..., help="Session ID to soft-delete."),
    workspace: str = typer.Option(default_workspace(), "--workspace", "-w", help="Workspace root."),
) -> None:
    """Soft-delete a persistent session without physically removing files."""
    metadata = SessionManager(workspace).delete(session_id)
    _render_session_metadata(metadata, "Deleted Session")


@app.command("scan")
def scan_command(
    workspace: str = typer.Option(default_workspace(), "--workspace", "-w", help="Workspace root."),
    max_files: int = typer.Option(5000, help="Maximum number of files to scan."),
    write: bool = typer.Option(True, "--write/--no-write", help="Write .dr-magu/scans/latest-scan.json."),
    json_output: bool = typer.Option(False, "--json", help="Return JSON output."),
) -> None:
    """Scan the workspace and detect repository metadata without using an LLM."""
    context = build_context(workspace, json_output)
    result = processor.execute("repo.scan", {"max_files": max_files}, context)
    if result.success and result.data and write:
        output_path = write_latest_scan(context.workspace_path, RepositoryScan.model_validate(result.data))
        result.data["scan_file"] = str(output_path)
    renderer.render(result, json_output)


@context_app.command("generate")
def context_generate_command(
    workspace: str = typer.Option(default_workspace(), "--workspace", "-w", help="Workspace root."),
    refresh: bool = typer.Option(False, "--refresh", help="Refresh repository scan before generating context."),
    json_output: bool = typer.Option(False, "--json", help="Return JSON output."),
) -> None:
    """Generate deterministic project context files from repository scan metadata."""
    result = generate_project_context(workspace, refresh=refresh)
    renderer.render(result, json_output)


@context_app.command("show")
def context_show_command(
    workspace: str = typer.Option(default_workspace(), "--workspace", "-w", help="Workspace root."),
    json_output: bool = typer.Option(False, "--json", help="Return JSON output."),
) -> None:
    """Show the generated structured project context."""
    result = show_project_context(workspace)
    renderer.render(result, json_output)


@context_app.command("path")
def context_path_command(
    workspace: str = typer.Option(default_workspace(), "--workspace", "-w", help="Workspace root."),
    json_output: bool = typer.Option(False, "--json", help="Return JSON output."),
) -> None:
    """Show the project context directory path."""
    result = get_context_path(workspace)
    renderer.render(result, json_output)


@workflow_app.command("list")
def workflow_list_command(
    workspace: str = typer.Option(default_workspace(), "--workspace", "-w", help="Workspace root."),
    json_output: bool = typer.Option(False, "--json", help="Return JSON output."),
) -> None:
    """List registered deterministic workflows."""
    result = WorkflowRunner(workspace).list_workflows()
    renderer.render(result, json_output)


@workflow_app.command("show")
def workflow_show_command(
    name: str = typer.Argument("repository.context", help="Workflow name."),
    workspace: str = typer.Option(default_workspace(), "--workspace", "-w", help="Workspace root."),
    json_output: bool = typer.Option(False, "--json", help="Return JSON output."),
) -> None:
    """Show workflow metadata."""
    result = WorkflowRunner(workspace).show_workflow(name)
    renderer.render(result, json_output)


@workflow_app.command("run")
def workflow_run_command(
    name: str = typer.Argument("repository.context", help="Workflow name to run."),
    workspace: str = typer.Option(default_workspace(), "--workspace", "-w", help="Workspace root."),
    json_output: bool = typer.Option(False, "--json", help="Return JSON output."),
) -> None:
    """Run a deterministic workflow and persist execution metadata."""
    result = WorkflowRunner(workspace).run(name)
    renderer.render(result, json_output)


@workflow_app.command("runs")
def workflow_runs_command(
    workspace: str = typer.Option(default_workspace(), "--workspace", "-w", help="Workspace root."),
    limit: int = typer.Option(20, "--limit", "-n", help="Maximum number of runs to show."),
    json_output: bool = typer.Option(False, "--json", help="Return JSON output."),
) -> None:
    """List recent persisted workflow runs for the workspace."""
    result = WorkflowRunner(workspace).list_runs(limit=limit)
    renderer.render(result, json_output)


@workflow_app.command("last")
def workflow_last_command(
    workspace: str = typer.Option(default_workspace(), "--workspace", "-w", help="Workspace root."),
    json_output: bool = typer.Option(False, "--json", help="Return JSON output."),
) -> None:
    """Show the latest persisted workflow run and state."""
    result = WorkflowRunner(workspace).show_last_run()
    renderer.render(result, json_output)


@workflow_app.command("run-show")
def workflow_run_show_command(
    run_id: str = typer.Argument(..., help="Workflow run id."),
    workspace: str = typer.Option(default_workspace(), "--workspace", "-w", help="Workspace root."),
    json_output: bool = typer.Option(False, "--json", help="Return JSON output."),
) -> None:
    """Show one persisted workflow run and state."""
    result = WorkflowRunner(workspace).show_run(run_id)
    renderer.render(result, json_output)


@runtime_app.command("inspect")
def runtime_inspect_command(
    workspace: str = typer.Option(default_workspace(), "--workspace", "-w", help="Workspace root."),
    json_output: bool = typer.Option(False, "--json", help="Return JSON output."),
) -> None:
    """Inspect the current Dr Magu runtime context for the future Orchestrator Brain."""
    result = RuntimeInspector(workspace).inspect_result()
    renderer.render(result, json_output)


@agent_app.command("list")
def agent_list_command(
    workspace: str = typer.Option(default_workspace(), "--workspace", "-w", help="Workspace root."),
    include_deleted: bool = typer.Option(False, "--include-deleted", help="Include soft-deleted agents."),
    json_output: bool = typer.Option(False, "--json", help="Return JSON output."),
) -> None:
    """List configured agents with resolved model configuration."""
    result = AgentRunner(workspace).list_agents(include_deleted=include_deleted)
    renderer.render(result, json_output)


@agent_app.command("show")
def agent_show_command(
    agent_id: str = typer.Argument(..., help="Agent ID or alias."),
    workspace: str = typer.Option(default_workspace(), "--workspace", "-w", help="Workspace root."),
    json_output: bool = typer.Option(False, "--json", help="Return JSON output."),
) -> None:
    """Show one configured agent and its resolved model configuration."""
    result = AgentRunner(workspace).show_agent(agent_id)
    renderer.render(result, json_output)


@agent_app.command("run")
def agent_run_command(
    agent_id: str = typer.Argument("repository-analyzer", help="Agent ID or alias."),
    workspace: str = typer.Option(default_workspace(), "--workspace", "-w", help="Workspace root."),
    json_output: bool = typer.Option(False, "--json", help="Return JSON output."),
) -> None:
    """Run a configured agent by delegating to its bound workflow."""
    result = AgentRunner(workspace).run_agent(agent_id)
    renderer.render(result, json_output)


@agent_app.command("validate")
def agent_validate_command(
    agent_id: str = typer.Argument(..., help="Agent ID or alias."),
    workspace: str = typer.Option(default_workspace(), "--workspace", "-w", help="Workspace root."),
    json_output: bool = typer.Option(False, "--json", help="Return JSON output."),
) -> None:
    """Validate an agent definition and its workflow binding."""
    result = AgentRunner(workspace).validate_agent(agent_id)
    renderer.render(result, json_output)


@agent_app.command("enable")
def agent_enable_command(
    agent_id: str = typer.Argument(..., help="Agent ID or alias."),
    workspace: str = typer.Option(default_workspace(), "--workspace", "-w", help="Workspace root."),
    json_output: bool = typer.Option(False, "--json", help="Return JSON output."),
) -> None:
    """Enable an agent using a workspace-level override."""
    result = AgentRunner(workspace).enable_agent(agent_id)
    renderer.render(result, json_output)


@agent_app.command("disable")
def agent_disable_command(
    agent_id: str = typer.Argument(..., help="Agent ID or alias."),
    workspace: str = typer.Option(default_workspace(), "--workspace", "-w", help="Workspace root."),
    json_output: bool = typer.Option(False, "--json", help="Return JSON output."),
) -> None:
    """Disable an agent using a workspace-level override."""
    result = AgentRunner(workspace).disable_agent(agent_id)
    renderer.render(result, json_output)


@agent_app.command("delete")
def agent_delete_command(
    agent_id: str = typer.Argument(..., help="Agent ID or alias."),
    workspace: str = typer.Option(default_workspace(), "--workspace", "-w", help="Workspace root."),
    json_output: bool = typer.Option(False, "--json", help="Return JSON output."),
) -> None:
    """Soft-delete an agent using a workspace-level override."""
    result = AgentRunner(workspace).delete_agent(agent_id)
    renderer.render(result, json_output)


@agent_app.command("add")
def agent_add_command(
    file_path: str = typer.Option(..., "--file", "-f", help="YAML file containing one agent definition."),
    workspace: str = typer.Option(default_workspace(), "--workspace", "-w", help="Workspace root."),
    json_output: bool = typer.Option(False, "--json", help="Return JSON output."),
) -> None:
    """Add a workspace-managed agent from a YAML definition."""
    result = AgentRunner(workspace).add_agent_from_file(file_path)
    renderer.render(result, json_output)


@agent_app.command("update")
def agent_update_command(
    agent_id: str = typer.Argument(..., help="Agent ID to update."),
    file_path: str = typer.Option(..., "--file", "-f", help="YAML file containing the updated agent definition."),
    workspace: str = typer.Option(default_workspace(), "--workspace", "-w", help="Workspace root."),
    json_output: bool = typer.Option(False, "--json", help="Return JSON output."),
) -> None:
    """Update or override an agent from a YAML definition."""
    result = AgentRunner(workspace).update_agent_from_file(agent_id, file_path)
    renderer.render(result, json_output)


@brain_app.command("context")
def brain_context_command(
    workspace: str = typer.Option(default_workspace(), "--workspace", "-w", help="Workspace root."),
    json_output: bool = typer.Option(False, "--json", help="Return JSON output."),
) -> None:
    """Load Brain context for the future Orchestrator Brain."""
    result = BrainContextLoader(workspace).load_result()
    renderer.render(result, json_output)


@tools_app.command("list")
def tools_list_command(
    json_output: bool = typer.Option(False, "--json", help="Return JSON output."),
) -> None:
    """List formal tool registry entries exposed to the Brain."""
    from dr_magu.result import ToolResult

    result = ToolResult(success=True, tool="tools.list", data=ToolRegistry().as_result_data())
    renderer.render(result, json_output)


@permissions_app.command("show")
def permissions_show_command(
    workspace: str = typer.Option(default_workspace(), "--workspace", "-w", help="Workspace root."),
    json_output: bool = typer.Option(False, "--json", help="Return JSON output."),
) -> None:
    """Show the effective permission context used by the Brain and validator."""
    from dr_magu.result import ToolResult

    context = build_context(workspace, json_output)
    result = ToolResult(success=True, tool="permissions.show", data=PermissionContextReader(context.config).read().model_dump())
    renderer.render(result, json_output)


@plugin_app.command("list")
def plugin_list_command(
    workspace: str = typer.Option(default_workspace(), "--workspace", "-w", help="Workspace root."),
    json_output: bool = typer.Option(False, "--json", help="Return JSON output."),
) -> None:
    """List discovered local plugins and provided resources."""
    result = PluginManager(workspace).list_plugins()
    renderer.render(result, json_output)


@plugin_app.command("show")
def plugin_show_command(
    plugin_id: str = typer.Argument(..., help="Plugin ID."),
    workspace: str = typer.Option(default_workspace(), "--workspace", "-w", help="Workspace root."),
    json_output: bool = typer.Option(False, "--json", help="Return JSON output."),
) -> None:
    """Show one discovered local plugin manifest."""
    result = PluginManager(workspace).show_plugin(plugin_id)
    renderer.render(result, json_output)


@plugin_app.command("validate")
def plugin_validate_command(
    plugin_id: str | None = typer.Argument(None, help="Optional plugin ID. When omitted, all plugins are validated."),
    workspace: str = typer.Option(default_workspace(), "--workspace", "-w", help="Workspace root."),
    json_output: bool = typer.Option(False, "--json", help="Return JSON output."),
) -> None:
    """Validate one plugin or all discovered local plugins."""
    result = PluginManager(workspace).validate_plugin(plugin_id)
    renderer.render(result, json_output)




@contracts_app.command("tools")
def contracts_tools_command(
    json_output: bool = typer.Option(False, "--json", help="Return JSON output."),
) -> None:
    """Show formal tool contracts used by the Brain plan validator."""
    from dr_magu.result import ToolResult

    result = ToolResult(success=True, tool="contracts.tools", data=ToolRegistry().as_result_data())
    renderer.render(result, json_output)


@plan_app.command("validate")
def plan_validate_command(
    step: list[str] = typer.Option(None, "--step", help="Tool or command step to validate. Can be passed multiple times."),
    intent: str = typer.Option("manual_validation", "--intent", help="Plan intent label."),
    json_output: bool = typer.Option(False, "--json", help="Return JSON output."),
) -> None:
    """Validate a structured Brain plan without executing it."""
    from dr_magu.result import ToolResult

    plan = BrainPlan(
        intent=intent,
        language="en",
        confidence=1.0,
        steps=[PlanStep(name=item) for item in (step or [])],
        explanation="CLI-created validation plan.",
    )
    validation = PlanValidator().validate(plan)
    result = ToolResult(success=validation.valid, tool="plan.validate", data=validation.model_dump())
    renderer.render(result, json_output)


@control_app.command("center")
def control_center_command(
    workspace: str = typer.Option(default_workspace(), "--workspace", "-w", help="Workspace root."),
    json_output: bool = typer.Option(False, "--json", help="Return JSON output."),
) -> None:
    """Show the Dr Magu Control Center dashboard."""
    result = ControlCenterService(workspace).dashboard_result()
    renderer.render(result, json_output)


@control_app.command("plugin")
def control_plugin_command(
    plugin_id: str = typer.Argument(..., help="Plugin ID to inspect."),
    workspace: str = typer.Option(default_workspace(), "--workspace", "-w", help="Workspace root."),
    json_output: bool = typer.Option(False, "--json", help="Return JSON output."),
) -> None:
    """Show one plugin impact summary in the Control Center."""
    result = ControlCenterService(workspace).plugin_impact_result(plugin_id)
    renderer.render(result, json_output)


@app.command("run")
def run_command(
    command_line: str = typer.Argument(..., help="Internal command line, for example: 'files.read README.md'."),
    workspace: str = typer.Option(default_workspace(), "--workspace", "-w", help="Workspace root."),
    json_output: bool = typer.Option(False, "--json", help="Return JSON output."),
) -> None:
    """Process one internal command through the Command Processor."""
    context = build_context(workspace, json_output)
    result = processor.execute_line(command_line, context)
    renderer.render(result, json_output)


@commands_app.command("list")
def list_registered_commands(
    json_output: bool = typer.Option(False, "--json", help="Return JSON output."),
) -> None:
    """List commands registered in the Command Registry."""
    commands = registry.list_commands()
    if json_output:
        import json
        console.print_json(json.dumps([command.model_dump(exclude={"handler"}) for command in commands]))
        return

    table = Table(title="Registered Commands")
    table.add_column("Name")
    table.add_column("Category")
    table.add_column("Description")
    table.add_column("Aliases")
    for command in commands:
        table.add_row(command.name, command.category, command.description, ", ".join(command.aliases))
    console.print(table)


@files_app.command("list")
def files_list(
    path: str = typer.Argument(".", help="Path to list inside the workspace."),
    workspace: str = typer.Option(default_workspace(), "--workspace", "-w", help="Workspace root."),
    max_files: int = typer.Option(500, help="Maximum number of files to return."),
    json_output: bool = typer.Option(False, "--json", help="Return JSON output."),
) -> None:
    context = build_context(workspace, json_output)
    result = processor.execute("files.list", {"path": path, "max_files": max_files}, context)
    renderer.render(result, json_output)


@files_app.command("read")
def files_read(
    path: str = typer.Argument(..., help="File path inside the workspace."),
    workspace: str = typer.Option(default_workspace(), "--workspace", "-w", help="Workspace root."),
    max_chars: int = typer.Option(20000, help="Maximum characters to read."),
    json_output: bool = typer.Option(False, "--json", help="Return JSON output."),
) -> None:
    context = build_context(workspace, json_output)
    result = processor.execute("files.read", {"path": path, "max_chars": max_chars}, context)
    renderer.render(result, json_output)


@search_app.command("code")
def search_code_command(
    query: str = typer.Argument(..., help="Text to search."),
    path: str = typer.Argument(".", help="Path to search inside the workspace."),
    workspace: str = typer.Option(default_workspace(), "--workspace", "-w", help="Workspace root."),
    max_results: int = typer.Option(100, help="Maximum number of results."),
    json_output: bool = typer.Option(False, "--json", help="Return JSON output."),
) -> None:
    context = build_context(workspace, json_output)
    result = processor.execute(
        "search.code",
        {"query": query, "path": path, "max_results": max_results},
        context,
    )
    renderer.render(result, json_output)


@git_app.command("status")
def git_status_command(
    workspace: str = typer.Option(default_workspace(), "--workspace", "-w", help="Workspace root."),
    json_output: bool = typer.Option(False, "--json", help="Return JSON output."),
) -> None:
    context = build_context(workspace, json_output)
    result = processor.execute("git.status", {}, context)
    renderer.render(result, json_output)


@git_app.command("diff")
def git_diff_command(
    workspace: str = typer.Option(default_workspace(), "--workspace", "-w", help="Workspace root."),
    json_output: bool = typer.Option(False, "--json", help="Return JSON output."),
) -> None:
    context = build_context(workspace, json_output)
    result = processor.execute("git.diff", {}, context)
    renderer.render(result, json_output)


@shell_app.command("run")
def shell_run_command(
    command: str = typer.Argument(..., help="Shell command to run inside the workspace."),
    workspace: str = typer.Option(default_workspace(), "--workspace", "-w", help="Workspace root."),
    timeout_seconds: int = typer.Option(120, help="Command timeout in seconds."),
    json_output: bool = typer.Option(False, "--json", help="Return JSON output."),
) -> None:
    context = build_context(workspace, json_output)
    result = processor.execute(
        "shell.run",
        {"command": command, "timeout_seconds": timeout_seconds},
        context,
    )
    renderer.render(result, json_output)


@app.command("tui")
def tui_command(
    workspace: str = typer.Option(default_workspace(), "--workspace", "-w", help="Workspace root."),
) -> None:
    """Start the Dr Magu Terminal UI."""
    from dr_magu.tui_app import run_tui

    try:
        run_tui(workspace)
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(code=1)


@app.command("version")
def version() -> None:
    console.print("dr-magu-cli v0.9.4")


if __name__ == "__main__":
    app()



@app.command("ask")
def ask(prompt: str, workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path.")) -> None:
    """Ask Dr Magu Brain to plan and execute a safe workspace action."""
    typer.echo(render_brain_result(brain_execute(prompt, workspace)))


@app.command("brain-plan")
def brain_plan_command(prompt: str, workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path.")) -> None:
    """Create a Brain plan without executing it."""
    typer.echo(render_brain_result(brain_plan(prompt, workspace)))


@app.command("brain-execute")
def brain_execute_command(prompt: str, workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path.")) -> None:
    """Create, validate and execute a Brain plan."""
    typer.echo(render_brain_result(brain_execute(prompt, workspace)))



@app.command("brain-route")
def brain_route_command(prompt: str) -> None:
    """Classify a prompt through the Dr Magu Intent Router."""
    typer.echo(render_brain_result(brain_route(prompt)))



@app.command("research")
def research(topic: str, limit: int = typer.Option(5, "--limit", "-n", help="Number of sources to return."), workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path.")) -> None:
    """Search for structured research sources about a topic."""
    result = WebResearchRunner(workspace).search(topic, limit=limit)
    typer.echo(result.data if result.success else result.errors)



@app.command("schedule-create")
def schedule_create(
    name: str,
    command: str = typer.Option(..., "--command", "-c", help="Dr Magu command to execute."),
    cron: str = typer.Option("@daily", "--cron", help="Cron expression or shortcut."),
    timezone_name: str = typer.Option("UTC", "--timezone", help="Schedule timezone."),
    description: str = typer.Option("", "--description", "-d", help="Schedule description."),
    workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path."),
) -> None:
    """Create a persisted scheduled command."""
    result = SchedulerRuntime(workspace).create(name, command, cron, timezone_name, description)
    typer.echo(result.data if result.success else result.errors)


@app.command("schedule-list")
def schedule_list(
    include_deleted: bool = typer.Option(False, "--include-deleted", help="Include soft-deleted tasks."),
    workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path."),
) -> None:
    """List persisted scheduled commands."""
    result = SchedulerRuntime(workspace).list(include_deleted=include_deleted)
    typer.echo(result.data if result.success else result.errors)


@app.command("schedule-enable")
def schedule_enable(task_id: str, workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path.")) -> None:
    """Enable a scheduled command."""
    result = SchedulerRuntime(workspace).enable(task_id)
    typer.echo(result.data if result.success else result.errors)


@app.command("schedule-disable")
def schedule_disable(task_id: str, workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path.")) -> None:
    """Disable a scheduled command."""
    result = SchedulerRuntime(workspace).disable(task_id)
    typer.echo(result.data if result.success else result.errors)


@app.command("schedule-delete")
def schedule_delete(task_id: str, workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path.")) -> None:
    """Soft-delete a scheduled command."""
    result = SchedulerRuntime(workspace).delete(task_id)
    typer.echo(result.data if result.success else result.errors)


@app.command("schedule-run")
def schedule_run(task_id: str, workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path.")) -> None:
    """Execute a scheduled command once."""
    result = SchedulerRuntime(workspace).run_once(task_id)
    typer.echo(result.data if result.success else result.errors)



@app.command("dev-agents")
def dev_agents(workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path.")) -> None:
    """List software development agents."""
    result = SoftwareAgentRunner(workspace).list_agents()
    typer.echo(result.data if result.success else result.errors)


@app.command("dev-run")
def dev_run(agent_id: str, workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path.")) -> None:
    """Run a deterministic software development agent."""
    result = SoftwareAgentRunner(workspace).run(agent_id)
    typer.echo(result.data if result.success else result.errors)


@app.command("git-status")
def git_status(workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path.")) -> None:
    """Read git status."""
    result = GitToolRunner(workspace).run("status")
    typer.echo(result.data if result.success else result.errors)


@app.command("fs-list")
def fs_list(path: str = ".", workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path.")) -> None:
    """List workspace files."""
    result = FilesystemToolRunner(workspace).list(path)
    typer.echo(result.data if result.success else result.errors)


@app.command("fs-read")
def fs_read(path: str, workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path.")) -> None:
    """Read a workspace file."""
    result = FilesystemToolRunner(workspace).read(path)
    typer.echo(result.data if result.success else result.errors)


@app.command("fs-write")
def fs_write(path: str, content: str, workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path.")) -> None:
    """Write a workspace file."""
    result = FilesystemToolRunner(workspace).write(path, content)
    typer.echo(result.data if result.success else result.errors)


@app.command("shell-run")
def shell_run(command: str, approved: bool = typer.Option(False, "--approved", help="Confirm shell execution approval."), workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path.")) -> None:
    """Run a shell command after approval."""
    result = ShellToolRunner(workspace).run(command, approved=approved)
    typer.echo(result.data if result.success else result.errors)



@app.command("website-build")
def website_build(
    topic: str,
    limit: int = typer.Option(5, "--limit", "-n", help="Number of research sources."),
    workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path."),
) -> None:
    """Generate website proposal, architecture options, approval request and report."""
    result = WebsiteBuilderWorkflow(workspace).generate(topic=topic, research_limit=limit)
    typer.echo(result.data if result.success else result.errors)



@app.command("workflow-engine-run")
def workflow_engine_run(
    workflow_id: str = typer.Argument("website-builder"),
    topic: str = typer.Option("", "--topic", "-t", help="Workflow topic/input."),
    workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path."),
) -> None:
    """Run a stateful workflow through the Workflow Engine."""
    result = WorkflowRunner(workspace).run(workflow_id, topic=topic)
    typer.echo(result.data if result.success else result.errors)


@app.command("workflow-engine-status")
def workflow_engine_status(
    run_id: str,
    workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path."),
) -> None:
    """Inspect workflow state and context."""
    result = WorkflowRunner(workspace).status(run_id)
    typer.echo(result.data if result.success else result.errors)


@app.command("workflow-engine-history")
def workflow_engine_history(
    run_id: str,
    workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path."),
) -> None:
    """Inspect workflow history."""
    result = WorkflowRunner(workspace).history(run_id)
    typer.echo(result.data if result.success else result.errors)


@app.command("workflow-engine-runs")
def workflow_engine_runs(
    workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path."),
) -> None:
    """List workflow engine runs."""
    result = WorkflowRunner(workspace).list_runs()
    typer.echo(result.data if result.success else result.errors)



@app.command("workflow-runtime-inspect")
def workflow_runtime_inspect(
    run_id: str,
    workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path."),
) -> None:
    """Inspect workflow state, context and latest event."""
    result = WorkflowRuntime(workspace).inspect(run_id)
    typer.echo(result.data if result.success else result.errors)


@app.command("workflow-runtime-cancel")
def workflow_runtime_cancel(
    run_id: str,
    reason: str = typer.Option("", "--reason", "-r", help="Cancellation reason."),
    workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path."),
) -> None:
    """Cancel a workflow run."""
    result = WorkflowRuntime(workspace).cancel(run_id, reason=reason)
    typer.echo(result.data if result.success else result.errors)


@app.command("workflow-runtime-retry")
def workflow_runtime_retry(
    run_id: str,
    workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path."),
) -> None:
    """Retry a failed workflow run."""
    result = WorkflowRuntime(workspace).retry(run_id)
    typer.echo(result.data if result.success else result.errors)


@app.command("workflow-runtime-resume")
def workflow_runtime_resume(
    run_id: str,
    workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path."),
) -> None:
    """Resume a workflow run."""
    result = WorkflowRuntime(workspace).resume(run_id)
    typer.echo(result.data if result.success else result.errors)


@app.command("workflow-runtime-export")
def workflow_runtime_export(
    run_id: str,
    output_format: str = typer.Option("json", "--format", "-f", help="Export format: json or md."),
    workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path."),
) -> None:
    """Export workflow history as JSON or Markdown."""
    result = WorkflowRuntime(workspace).export_history(run_id, output_format=output_format)
    typer.echo(result.data if result.success else result.errors)

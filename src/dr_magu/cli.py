from __future__ import annotations

import typer
from dr_magu.ai_os.runtime import AIOperatingSystem
from dr_magu.self_healing.runtime import SelfHealingRuntime
from dr_magu.software_factory.runtime import SoftwareFactoryRuntime
from dr_magu.multi_agent.runtime import MultiAgentOrchestrator
from dr_magu.conversational_router.router import route_prompt
from dr_magu.mcp_integrations.runtime import MCPIntegrationRuntime
from dr_magu.chat_ux.renderer import render_user_facing_result
from dr_magu.mcp_runtime.registry import MCPServerRegistry
from dr_magu.mcp_runtime.manager import MCPRuntimeManager
from dr_magu.llm_runtime.runtime import LLMRuntime
from dr_magu.execution.executor import ExecutionExecutor
from dr_magu.execution.planner import ExecutionPlanner
from dr_magu.stabilization.commands import run_stabilization_checks
from dr_magu.workflow_engine.runtime import WorkflowRuntime
from dr_magu.workflow_engine.runner import WorkflowRunner as WorkflowEngineRunner
from dr_magu.website_builder.workflow import WebsiteBuilderWorkflow
from dr_magu.filesystem_tools.runner import FilesystemToolRunner
from dr_magu.shell_tools.runner import ShellToolRunner
from dr_magu.git_tools.runner import GitToolRunner
from dr_magu.sdlc.agents import SoftwareAgentRunner
from dr_magu.scheduler.runtime import SchedulerRuntime
from dr_magu.research.runner import WebResearchRunner
from dr_magu.brain.commands import brain_ask, brain_chat, brain_plan, brain_execute, brain_route, render_brain_result
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
from dr_magu.multi_agent.team import TeamRuntime
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
team_app = typer.Typer(help="Multi-agent team orchestration tools")
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
app.add_typer(team_app, name="team")
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


@agent_app.command("create")
def agent_create_command(
    agent_id: str = typer.Argument(..., help="Agent ID to create."),
    name: str = typer.Option("", "--name", help="Human-readable agent name."),
    role: str = typer.Option("general", "--role", help="Agent role, for example researcher, architect or reviewer."),
    workflow: str = typer.Option("research-brief", "--workflow", help="Bound workflow id."),
    description: str = typer.Option("", "--description", help="Agent description."),
    capabilities: str = typer.Option("", "--capabilities", help="Comma-separated capabilities."),
    aliases: str = typer.Option("", "--aliases", help="Comma-separated aliases."),
    requires_llm: bool = typer.Option(False, "--requires-llm", help="Mark this agent as requiring LLM access."),
    workspace: str = typer.Option(default_workspace(), "--workspace", "-w", help="Workspace root."),
    json_output: bool = typer.Option(False, "--json", help="Return JSON output."),
) -> None:
    """Create a workspace-managed runtime agent without requiring YAML."""
    result = AgentRunner(workspace).create_agent(
        agent_id,
        name=name or None,
        role=role,
        workflow=workflow,
        description=description,
        capabilities=[item.strip() for item in capabilities.split(",") if item.strip()] or None,
        aliases=[item.strip() for item in aliases.split(",") if item.strip()] or None,
        requires_llm=requires_llm,
    )
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
    prompt: str = typer.Argument("", help="Optional agent task prompt or topic."),
    dry_run: bool = typer.Option(False, "--dry-run", "--dry", help="Plan the bound workflow without executing it."),
    workspace: str = typer.Option(default_workspace(), "--workspace", "-w", help="Workspace root."),
    json_output: bool = typer.Option(False, "--json", help="Return JSON output."),
) -> None:
    """Run a configured agent through the Agent Runtime."""
    result = AgentRunner(workspace).run_agent(agent_id, prompt=prompt, dry_run=dry_run)
    renderer.render(result, json_output)


@agent_app.command("status")
def agent_status_command(
    agent_id: str = typer.Argument(..., help="Agent ID or alias."),
    workspace: str = typer.Option(default_workspace(), "--workspace", "-w", help="Workspace root."),
    json_output: bool = typer.Option(False, "--json", help="Return JSON output."),
) -> None:
    """Show Agent Runtime status and latest execution state."""
    result = AgentRunner(workspace).status_agent(agent_id)
    renderer.render(result, json_output)


@agent_app.command("stop")
def agent_stop_command(
    agent_id: str = typer.Argument(..., help="Agent ID or alias."),
    reason: str = typer.Option("Manual stop requested.", "--reason", help="Stop reason."),
    workspace: str = typer.Option(default_workspace(), "--workspace", "-w", help="Workspace root."),
    json_output: bool = typer.Option(False, "--json", help="Return JSON output."),
) -> None:
    """Request an agent stop and persist stopped runtime state."""
    result = AgentRunner(workspace).stop_agent(agent_id, reason=reason)
    renderer.render(result, json_output)


@agent_app.command("history")
def agent_history_command(
    agent_id: str = typer.Argument("", help="Optional agent ID or alias."),
    limit: int = typer.Option(20, "--limit", help="Maximum run records."),
    workspace: str = typer.Option(default_workspace(), "--workspace", "-w", help="Workspace root."),
    json_output: bool = typer.Option(False, "--json", help="Return JSON output."),
) -> None:
    """List Agent Runtime execution history."""
    result = AgentRunner(workspace).history(agent_id=agent_id or None, limit=limit)
    renderer.render(result, json_output)


@agent_app.command("context")
def agent_context_command(
    agent_id: str = typer.Argument(..., help="Agent ID or alias."),
    workspace: str = typer.Option(default_workspace(), "--workspace", "-w", help="Workspace root."),
    json_output: bool = typer.Option(False, "--json", help="Return JSON output."),
) -> None:
    """Show Agent Runtime context, permissions, MCP access and workflow access."""
    result = AgentRunner(workspace).context(agent_id)
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


@team_app.command("create")
def team_create_command(
    team_id: str = typer.Argument(..., help="Team ID to create."),
    name: str = typer.Option("", "--name", help="Human-readable team name."),
    mode: str = typer.Option("sequential", "--mode", help="Team execution mode."),
    description: str = typer.Option("", "--description", help="Team description."),
    workspace: str = typer.Option(default_workspace(), "--workspace", "-w", help="Workspace root."),
    json_output: bool = typer.Option(False, "--json", help="Return JSON output."),
) -> None:
    """Create a workspace-managed multi-agent team."""
    result = TeamRuntime(workspace).create(team_id, name=name or None, mode=mode, description=description)
    renderer.render(result, json_output)


@team_app.command("add")
def team_add_command(
    team_id: str = typer.Argument(..., help="Team ID."),
    agent_id: str = typer.Argument(..., help="Agent ID to add."),
    workspace: str = typer.Option(default_workspace(), "--workspace", "-w", help="Workspace root."),
    json_output: bool = typer.Option(False, "--json", help="Return JSON output."),
) -> None:
    """Add an agent to a multi-agent team."""
    result = TeamRuntime(workspace).add(team_id, agent_id)
    renderer.render(result, json_output)


@team_app.command("remove")
def team_remove_command(
    team_id: str = typer.Argument(..., help="Team ID."),
    agent_id: str = typer.Argument(..., help="Agent ID to remove."),
    workspace: str = typer.Option(default_workspace(), "--workspace", "-w", help="Workspace root."),
    json_output: bool = typer.Option(False, "--json", help="Return JSON output."),
) -> None:
    """Remove an agent from a multi-agent team."""
    result = TeamRuntime(workspace).remove(team_id, agent_id)
    renderer.render(result, json_output)


@team_app.command("list")
def team_list_command(
    workspace: str = typer.Option(default_workspace(), "--workspace", "-w", help="Workspace root."),
    include_deleted: bool = typer.Option(False, "--include-deleted", help="Include soft-deleted teams."),
    json_output: bool = typer.Option(False, "--json", help="Return JSON output."),
) -> None:
    """List configured multi-agent teams."""
    result = TeamRuntime(workspace).list(include_deleted=include_deleted)
    renderer.render(result, json_output)


@team_app.command("show")
def team_show_command(
    team_id: str = typer.Argument(..., help="Team ID."),
    workspace: str = typer.Option(default_workspace(), "--workspace", "-w", help="Workspace root."),
    json_output: bool = typer.Option(False, "--json", help="Return JSON output."),
) -> None:
    """Show a multi-agent team, members and runtime state."""
    result = TeamRuntime(workspace).show(team_id)
    renderer.render(result, json_output)


@team_app.command("run")
def team_run_command(
    team_id: str = typer.Argument(..., help="Team ID."),
    prompt: str = typer.Argument("", help="Shared team objective."),
    mode: str = typer.Option("", "--mode", help="Override team execution mode."),
    continue_on_error: bool = typer.Option(False, "--continue-on-error", help="Continue after failed agents."),
    dry_run: bool = typer.Option(False, "--dry-run", "--dry", help="Run agents in dry-run mode."),
    workspace: str = typer.Option(default_workspace(), "--workspace", "-w", help="Workspace root."),
    json_output: bool = typer.Option(False, "--json", help="Return JSON output."),
) -> None:
    """Run a multi-agent team against a shared objective."""
    result = TeamRuntime(workspace).run(team_id, prompt=prompt, mode=mode or None, continue_on_error=continue_on_error, dry_run=dry_run)
    renderer.render(result, json_output)


@team_app.command("status")
def team_status_command(
    team_id: str = typer.Argument(..., help="Team ID."),
    workspace: str = typer.Option(default_workspace(), "--workspace", "-w", help="Workspace root."),
    json_output: bool = typer.Option(False, "--json", help="Return JSON output."),
) -> None:
    """Show multi-agent team runtime status and recent runs."""
    result = TeamRuntime(workspace).status(team_id)
    renderer.render(result, json_output)


@team_app.command("history")
def team_history_command(
    team_id: str = typer.Argument("", help="Optional team ID."),
    limit: int = typer.Option(20, "--limit", help="Maximum run records."),
    workspace: str = typer.Option(default_workspace(), "--workspace", "-w", help="Workspace root."),
    json_output: bool = typer.Option(False, "--json", help="Return JSON output."),
) -> None:
    """List multi-agent team run history."""
    result = TeamRuntime(workspace).history(team_id=team_id or None, limit=limit)
    renderer.render(result, json_output)


@team_app.command("stop")
def team_stop_command(
    team_id: str = typer.Argument(..., help="Team ID."),
    reason: str = typer.Option("Manual team stop requested.", "--reason", help="Stop reason."),
    workspace: str = typer.Option(default_workspace(), "--workspace", "-w", help="Workspace root."),
    json_output: bool = typer.Option(False, "--json", help="Return JSON output."),
) -> None:
    """Stop a multi-agent team run and persist stopped state."""
    result = TeamRuntime(workspace).stop(team_id, reason=reason)
    renderer.render(result, json_output)


@team_app.command("delete")
def team_delete_command(
    team_id: str = typer.Argument(..., help="Team ID."),
    workspace: str = typer.Option(default_workspace(), "--workspace", "-w", help="Workspace root."),
    json_output: bool = typer.Option(False, "--json", help="Return JSON output."),
) -> None:
    """Soft-delete a multi-agent team."""
    result = TeamRuntime(workspace).delete(team_id)
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
    console.print("dr-magu-cli v2.7.0")



@app.command("brain-ask")
def brain_ask_command(
    prompt: str,
    workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path."),
    debug: bool = typer.Option(False, "--debug", help="Show internal routing and model metadata."),
) -> None:
    """Route a natural-language prompt through the Conversational Brain."""
    from dr_magu.brain.conversation import ConversationalBrain

    result = ConversationalBrain(workspace).ask(prompt)
    typer.echo(render_user_facing_result(result, debug=debug))

@app.command("brain-chat")
def brain_chat_command(
    prompt: str,
    workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path."),
    debug: bool = typer.Option(False, "--debug", help="Show internal routing and model metadata."),
) -> None:
    """Alias for Conversational Brain prompts."""
    from dr_magu.brain.conversation import ConversationalBrain

    result = ConversationalBrain(workspace).ask(prompt)
    typer.echo(render_user_facing_result(result, debug=debug))

@app.command("llm-chat")
def llm_chat_command(
    prompt: str,
    timeout_seconds: int = typer.Option(60, "--timeout", help="LLM request timeout in seconds."),
    workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path."),
    debug: bool = typer.Option(False, "--debug", help="Show sanitized debug metadata."),
) -> None:
    """Send a prompt to the configured default LLM model."""
    result = LLMRuntime(workspace).chat(prompt, timeout_seconds=timeout_seconds)
    if result.success:
        response = result.data.get("response", {})
        if debug:
            typer.echo(result.data)
        else:
            typer.echo(response.get("content", ""))
    else:
        typer.echo(result.errors)



@app.command("mcp-servers")
def mcp_servers_command(workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path.")) -> None:
    """List configured MCP servers."""
    typer.echo(MCPServerRegistry(workspace).to_dict())


@app.command("mcp-list")
def mcp_list_command(workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path.")) -> None:
    """List operational MCP servers with lifecycle status."""
    result = MCPRuntimeManager(workspace).list()
    typer.echo(result.data if result.success else result.errors)


@app.command("mcp-discover")
def mcp_discover_command(workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path.")) -> None:
    """Discover default MCP servers and persist workspace configuration."""
    result = MCPRuntimeManager(workspace).discover()
    typer.echo(result.data if result.success else result.errors)


@app.command("mcp-status")
def mcp_status_command(server_id: str, workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path.")) -> None:
    """Show operational status for one MCP server."""
    result = MCPRuntimeManager(workspace).status(server_id)
    typer.echo(result.data if result.success else result.errors)


@app.command("mcp-health")
def mcp_health_command(server_id: str, workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path.")) -> None:
    """Run an MCP health check."""
    result = MCPRuntimeManager(workspace).health(server_id)
    typer.echo(result.data if result.success else result.errors)


@app.command("mcp-debug")
def mcp_debug_command(server_id: str, workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path.")) -> None:
    """Show expanded MCP diagnostics for one server."""
    result = MCPRuntimeManager(workspace).debug(server_id)
    typer.echo(result.data if result.success else result.errors)


@app.command("mcp-start")
def mcp_start_command(server_id: str, workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path.")) -> None:
    """Start one configured MCP server process."""
    result = MCPRuntimeManager(workspace).start(server_id)
    typer.echo(result.data if result.success else result.errors)


@app.command("mcp-stop")
def mcp_stop_command(server_id: str, workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path.")) -> None:
    """Stop one managed MCP server process."""
    result = MCPRuntimeManager(workspace).stop(server_id)
    typer.echo(result.data if result.success else result.errors)


@app.command("mcp-restart")
def mcp_restart_command(server_id: str, workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path.")) -> None:
    """Restart one managed MCP server process."""
    result = MCPRuntimeManager(workspace).restart(server_id)
    typer.echo(result.data if result.success else result.errors)


@app.command("mcp-enable")
def mcp_enable_command(server_id: str, workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path.")) -> None:
    """Enable one MCP server in workspace configuration."""
    result = MCPRuntimeManager(workspace).enable(server_id)
    typer.echo(result.data if result.success else result.errors)


@app.command("mcp-disable")
def mcp_disable_command(server_id: str, workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path.")) -> None:
    """Disable one MCP server and stop it if it is running."""
    result = MCPRuntimeManager(workspace).disable(server_id)
    typer.echo(result.data if result.success else result.errors)


@app.command("mcp-boot")
def mcp_boot_command(workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path.")) -> None:
    """Start all enabled MCP servers that have auto_start=true."""
    result = MCPRuntimeManager(workspace).boot()
    typer.echo(result.data if result.success else result.errors)


@app.command("mcp-handshake")
def mcp_handshake_command(server_id: str, workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path.")) -> None:
    """Open a direct MCP stdio session and run initialize()."""
    from dr_magu.mcp_runtime.client import MCPClient

    server = MCPServerRegistry(workspace).find_by_id(server_id, include_disabled=True)
    if not server:
        typer.echo([f"Unknown MCP server: {server_id}"])
        return
    result = MCPClient(workspace, simulation_enabled=False).handshake(server)
    typer.echo(result.to_dict())


@app.command("mcp-tools")
def mcp_tools_command(server_id: str, workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path.")) -> None:
    """Open a direct MCP session and list available tools."""
    from dr_magu.mcp_runtime.client import MCPClient

    server = MCPServerRegistry(workspace).find_by_id(server_id, include_disabled=True)
    if not server:
        typer.echo([f"Unknown MCP server: {server_id}"])
        return
    result = MCPClient(workspace, simulation_enabled=False).list_mcp_tools(server)
    typer.echo(result.to_dict())


@app.command("mcp-test")
def mcp_test_command(
    server_id: str,
    target: str = typer.Argument("https://www.google.com"),
    workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path."),
) -> None:
    """Run a direct provider-specific MCP smoke test."""
    from dr_magu.mcp_runtime.client import MCPClient

    server = MCPServerRegistry(workspace).find_by_id(server_id, include_disabled=True)
    if not server:
        typer.echo([f"Unknown MCP server: {server_id}"])
        return
    result = MCPClient(workspace, simulation_enabled=False).test_server(server, target=target)
    typer.echo(result.to_dict())


@app.command("mcp-diagnose")
def mcp_diagnose_command(
    server_id: str,
    target: str = typer.Argument("https://www.google.com"),
    workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path."),
) -> None:
    """Run runtime, handshake, tools, and provider smoke-test diagnostics."""
    from dr_magu.mcp_runtime.client import MCPClient

    server = MCPServerRegistry(workspace).find_by_id(server_id, include_disabled=True)
    if not server:
        typer.echo([f"Unknown MCP server: {server_id}"])
        return
    runtime_status = MCPRuntimeManager(workspace).status(server_id)
    client = MCPClient(workspace, simulation_enabled=False)
    handshake = client.handshake(server)
    tools = client.list_mcp_tools(server) if handshake.success else None
    smoke = client.test_server(server, target=target) if handshake.success else None
    success = bool(runtime_status.success and handshake.success and (tools is None or tools.success) and (smoke is None or smoke.success))
    typer.echo({
        "server_id": server_id,
        "runtime_status": runtime_status.data if runtime_status.success else {"errors": runtime_status.errors},
        "handshake": handshake.to_dict(),
        "tools": tools.to_dict() if tools else None,
        "test": smoke.to_dict() if smoke else None,
        "overall": "SUCCESS" if success else "FAILED",
    })



@app.command("website-analyze")
def website_analyze_command(
    url: str,
    workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path."),
) -> None:
    """Analyze a website through Playwright MCP."""
    result = MCPIntegrationRuntime(workspace).website_analyze(url)
    typer.echo(result.data if result.success else result.errors)


@app.command("repository-read")
def repository_read_command(
    repository: str,
    workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path."),
) -> None:
    """Read repository metadata through GitHub MCP."""
    result = MCPIntegrationRuntime(workspace).repository_read(repository)
    typer.echo(result.data if result.success else result.errors)



@app.command("route")
def route_command(prompt: str) -> None:
    """Route a natural-language prompt to the command Dr Magu would execute."""
    typer.echo(route_prompt(prompt).to_dict())


@app.command("route-execute")
def route_execute_command(
    prompt: str,
    workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path."),
) -> None:
    """Route and execute a natural-language prompt."""
    from dr_magu.brain.conversation import ConversationalBrain
    from dr_magu.chat_ux.renderer import render_user_facing_result

    result = ConversationalBrain(workspace).ask(prompt)
    typer.echo(render_user_facing_result(result))




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
def research(
    topic: str,
    limit: int = typer.Option(5, "--limit", "-n", help="Number of sources to return."),
    provider: str = typer.Option("auto", "--provider", "-p", help="Research provider: auto, brave-search, playwright, github, filesystem, deterministic."),
    simulate: bool = typer.Option(False, "--simulate", help="Use deterministic MCP simulation instead of real provider adapters."),
    debug: bool = typer.Option(False, "--debug", help="Include Research -> MCP diagnostic events and persist latest-debug.json."),
    workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path."),
) -> None:
    """Search for structured research sources using selectable MCP providers and fallbacks."""
    result = WebResearchRunner(workspace, provider_name=provider, simulation_enabled=simulate, debug_enabled=debug).search(topic, limit=limit, debug=debug)
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




@app.command("workflow-engine-list")
def workflow_engine_list(
    workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path."),
) -> None:
    """List Workflow Engine definitions."""
    result = WorkflowEngineRunner(workspace).list_definitions()
    typer.echo(result.data if result.success else result.errors)


@app.command("workflow-engine-show")
def workflow_engine_show(
    workflow_id: str = typer.Argument("website-builder"),
    topic: str = typer.Option("", "--topic", "-t", help="Workflow topic/input."),
    workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path."),
) -> None:
    """Show a Workflow Engine definition."""
    variables = {"topic": topic} if topic else {}
    result = WorkflowEngineRunner(workspace).show_definition(workflow_id, variables=variables)
    typer.echo(result.data if result.success else result.errors)


@app.command("workflow-engine-plan")
def workflow_engine_plan(
    workflow_id: str = typer.Argument("website-builder"),
    topic: str = typer.Option("", "--topic", "-t", help="Workflow topic/input."),
    workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path."),
) -> None:
    """Render a Workflow Engine plan without executing it."""
    variables = {"topic": topic} if topic else {}
    result = WorkflowEngineRunner(workspace).plan(workflow_id, variables=variables)
    typer.echo(result.data if result.success else result.errors)


@app.command("workflow-engine-run")
def workflow_engine_run(
    workflow_id: str = typer.Argument("website-builder"),
    topic: str = typer.Option("", "--topic", "-t", help="Workflow topic/input."),
    workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path."),
) -> None:
    """Run a stateful workflow through the Workflow Engine."""
    result = WorkflowEngineRunner(workspace).run(workflow_id, topic=topic)
    typer.echo(result.data if result.success else result.errors)


@app.command("workflow-engine-status")
def workflow_engine_status(
    run_id: str,
    workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path."),
) -> None:
    """Inspect workflow state and context."""
    result = WorkflowEngineRunner(workspace).status(run_id)
    typer.echo(result.data if result.success else result.errors)


@app.command("workflow-engine-history")
def workflow_engine_history(
    run_id: str,
    workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path."),
) -> None:
    """Inspect workflow history."""
    result = WorkflowEngineRunner(workspace).history(run_id)
    typer.echo(result.data if result.success else result.errors)


@app.command("workflow-engine-runs")
def workflow_engine_runs(
    workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path."),
) -> None:
    """List workflow engine runs."""
    result = WorkflowEngineRunner(workspace).list_runs()
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



@app.command("stabilize")
def stabilize(
    output_format: str = typer.Option("text", "--format", "-f", help="Output format: text or json."),
    workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace/project root path."),
) -> None:
    """Run platform readiness checks before v1.0.0."""
    result = run_stabilization_checks(workspace, output_format=output_format)
    typer.echo(result.data if result.success else result.errors)



@app.command("execution-plan-file")
def execution_plan_file(
    target: str,
    content: str,
    workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path."),
) -> None:
    """Create a filesystem write execution plan."""
    result = ExecutionPlanner(workspace).simple_file_plan(target, content)
    typer.echo(result.data if result.success else result.errors)


@app.command("execution-plan-terminal")
def execution_plan_terminal(
    command: str,
    workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path."),
) -> None:
    """Create a terminal execution plan."""
    result = ExecutionPlanner(workspace).simple_terminal_plan(command)
    typer.echo(result.data if result.success else result.errors)


@app.command("execution-plan-git-commit")
def execution_plan_git_commit(
    message: str,
    workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path."),
) -> None:
    """Create a git commit execution plan."""
    result = ExecutionPlanner(workspace).simple_git_commit_plan(message)
    typer.echo(result.data if result.success else result.errors)


@app.command("execution-run")
def execution_run(
    plan_id: str,
    approved: bool = typer.Option(False, "--approved", help="Execute actions that require approval."),
    workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path."),
) -> None:
    """Execute an execution plan."""
    result = ExecutionExecutor(workspace).execute(plan_id, approved=approved)
    typer.echo(result.data if result.success else result.errors)


@app.command("execution-inspect")
def execution_inspect(
    plan_id: str,
    workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path."),
) -> None:
    """Inspect an execution plan."""
    result = ExecutionExecutor(workspace).inspect(plan_id)
    typer.echo(result.data if result.success else result.errors)


@app.command("execution-list")
def execution_list(
    workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path."),
) -> None:
    """List execution plans."""
    result = ExecutionExecutor(workspace).list_plans()
    typer.echo(result.data if result.success else result.errors)


@app.command("multiagent-plan")
def multiagent_plan_command(
    name: str = typer.Argument("sdlc.pipeline"),
    mode: str = typer.Option("sequential", "--mode", help="Orchestration mode."),
    workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path."),
) -> None:
    """Create a multi-agent orchestration plan."""
    result = MultiAgentOrchestrator(workspace).plan(name=name, mode=mode)
    typer.echo(result.data if result.success else result.errors)


@app.command("multiagent-run")
def multiagent_run_command(
    name: str = typer.Argument("sdlc.pipeline"),
    mode: str = typer.Option("sequential", "--mode", help="Orchestration mode."),
    continue_on_error: bool = typer.Option(False, "--continue-on-error", help="Continue after failed tasks."),
    workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path."),
) -> None:
    """Run a multi-agent orchestration plan."""
    result = MultiAgentOrchestrator(workspace).run(name=name, mode=mode, continue_on_error=continue_on_error)
    typer.echo(result.data if result.success else result.errors)


@app.command("factory-plan")
def factory_plan_command(
    idea: str,
    workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path."),
) -> None:
    """Create an Autonomous Software Factory plan."""
    result = SoftwareFactoryRuntime(workspace).plan(idea=idea)
    typer.echo(result.data if result.success else result.errors)


@app.command("factory-run")
def factory_run_command(
    idea: str,
    continue_on_error: bool = typer.Option(False, "--continue-on-error", help="Continue after failed stages."),
    workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path."),
) -> None:
    """Run the Autonomous Software Factory pipeline."""
    result = SoftwareFactoryRuntime(workspace).run(idea=idea, continue_on_error=continue_on_error)
    typer.echo(result.data if result.success else result.errors)


@app.command("healing-plan")
def healing_plan_command(
    command: str,
    fallback_command: str | None = typer.Option(None, "--fallback-command", help="Fallback command."),
    max_retries: int | None = typer.Option(None, "--max-retries", help="Maximum retry count."),
    workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path."),
) -> None:
    """Create a self-healing policy for a command."""
    result = SelfHealingRuntime(workspace).plan(command=command, fallback_command=fallback_command, max_retries=max_retries)
    typer.echo(result.data if result.success else result.errors)


@app.command("healing-run")
def healing_run_command(
    command: str,
    fallback_command: str | None = typer.Option(None, "--fallback-command", help="Fallback command."),
    max_retries: int | None = typer.Option(None, "--max-retries", help="Maximum retry count."),
    escalate_on_failure: bool = typer.Option(True, "--escalate/--no-escalate", help="Escalate after unrecovered failure."),
    workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path."),
) -> None:
    """Run a command with retry, fallback and escalation."""
    result = SelfHealingRuntime(workspace).run(
        command=command,
        fallback_command=fallback_command,
        max_retries=max_retries,
        escalate_on_failure=escalate_on_failure,
    )
    typer.echo(result.data if result.success else result.errors)


@app.command("os-status")
def os_status_command(
    workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path."),
) -> None:
    """Show AI Operating System status."""
    result = AIOperatingSystem(workspace).status()
    typer.echo(result.data if result.success else result.errors)


@app.command("os-capabilities")
def os_capabilities_command(
    workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path."),
) -> None:
    """List AI Operating System capabilities."""
    result = AIOperatingSystem(workspace).capabilities()
    typer.echo(result.data if result.success else result.errors)


@app.command("os-dispatch")
def os_dispatch_command(
    command: str,
    workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path."),
) -> None:
    """Dispatch a command through the AI Operating System control layer."""
    result = AIOperatingSystem(workspace).dispatch(command)
    typer.echo(result.data if result.success else result.errors)


@app.command("os-boot")
def os_boot_command(
    workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path."),
) -> None:
    """Boot and summarize the AI Operating System."""
    result = AIOperatingSystem(workspace).boot()
    typer.echo(result.data if result.success else result.errors)

if __name__ == "__main__":
    app()

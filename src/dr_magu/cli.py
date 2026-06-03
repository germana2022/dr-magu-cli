from __future__ import annotations

import typer
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

app = typer.Typer(help="Dr Magu CLI - Tool CLI, command processor, Terminal UI, repository scanner, and context generator")
files_app = typer.Typer(help="File system tools")
search_app = typer.Typer(help="Code search tools")
git_app = typer.Typer(help="Git tools")
shell_app = typer.Typer(help="Shell execution tools")
commands_app = typer.Typer(help="Command registry tools")
session_app = typer.Typer(help="Persistent session management")
context_app = typer.Typer(help="Deterministic project context generation")

app.add_typer(files_app, name="files")
app.add_typer(search_app, name="search")
app.add_typer(git_app, name="git")
app.add_typer(shell_app, name="shell")
app.add_typer(commands_app, name="commands")
app.add_typer(session_app, name="session")
app.add_typer(context_app, name="context")

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
    console.print("dr-magu-cli v0.7.0")


if __name__ == "__main__":
    app()

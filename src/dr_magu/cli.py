from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from dr_magu.commands.context import CommandContext
from dr_magu.commands.processor import CommandProcessor
from dr_magu.commands.registry import registry
from dr_magu.config import default_workspace, load_config
from dr_magu.output.renderer import ResultRenderer

app = typer.Typer(help="Dr Magu CLI - Tool CLI, command processor, and Terminal UI")
files_app = typer.Typer(help="File system tools")
search_app = typer.Typer(help="Code search tools")
git_app = typer.Typer(help="Git tools")
shell_app = typer.Typer(help="Shell execution tools")
commands_app = typer.Typer(help="Command registry tools")

app.add_typer(files_app, name="files")
app.add_typer(search_app, name="search")
app.add_typer(git_app, name="git")
app.add_typer(shell_app, name="shell")
app.add_typer(commands_app, name="commands")

console = Console()
renderer = ResultRenderer(console)
processor = CommandProcessor(registry)


def build_context(workspace: str, json_output: bool = False) -> CommandContext:
    return CommandContext(
        workspace_path=workspace,
        output_format="json" if json_output else "human",
        config=load_config(),
    )


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
    console.print("dr-magu-cli v0.3.1")


if __name__ == "__main__":
    app()

from __future__ import annotations

import json
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table

from dr_magu.result import ToolResult


def _format_duration(duration_ms: object) -> str:
    if duration_ms is None:
        return ""
    try:
        value = int(duration_ms)
    except (TypeError, ValueError):
        return str(duration_ms)
    if value < 1000:
        return f"{value} ms"
    return f"{value / 1000:.2f} s"


class ResultRenderer:
    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()

    def render(self, result: ToolResult, as_json: bool = False) -> None:
        if as_json:
            self.console.print_json(json.dumps(result.model_dump()))
            return

        if not result.success:
            self.console.print(f"[bold red]Error:[/bold red] {'; '.join(result.errors)}")
            return

        if result.tool == "files.list":
            table = Table(title="Files")
            table.add_column("Path")
            for file_path in result.data.get("files", []):
                table.add_row(str(file_path))
            self.console.print(table)
            return

        if result.tool == "files.read":
            content = result.data.get("content", "")
            path = result.data.get("path", "")
            self.console.print(f"[bold]File:[/bold] {path}")
            self.console.print(Syntax(content, "text", line_numbers=True))
            return

        if result.tool == "search.code":
            table = Table(title="Search Results")
            table.add_column("File")
            table.add_column("Line")
            table.add_column("Text")
            for item in result.data.get("results", []):
                table.add_row(str(item["path"]), str(item["line"]), str(item["text"]))
            self.console.print(table)
            return


        if result.tool == "repo.scan":
            data = result.data or {}
            table = Table(title="Repository Scan Summary")
            table.add_column("Field")
            table.add_column("Value")
            table.add_row("Workspace", str(data.get("workspace_path", "")))
            table.add_row("Project", str(data.get("project_name", "")))
            table.add_row("Type", str(data.get("project_type", "")))
            table.add_row("Primary language", str(data.get("primary_language", "unknown")))
            table.add_row("Languages", ", ".join(data.get("languages", [])))
            table.add_row("Frameworks", ", ".join(data.get("frameworks", [])))
            table.add_row("Package managers", ", ".join(data.get("package_managers", [])))
            table.add_row("Build tools", ", ".join(data.get("build_tools", [])))
            table.add_row("Test frameworks", ", ".join(data.get("test_frameworks", [])))
            table.add_row("Files", str(data.get("file_count", 0)))
            if data.get("scan_file"):
                table.add_row("Scan file", str(data.get("scan_file")))
            self.console.print(table)

            important_files = data.get("important_files", []) or []
            if important_files:
                files_table = Table(title="Important Files")
                files_table.add_column("Path")
                files_table.add_column("Reason")
                for item in important_files[:20]:
                    files_table.add_row(str(item.get("path", "")), str(item.get("reason", "")))
                self.console.print(files_table)
            return

        if result.tool in {"context.generate", "context.show"}:
            data = result.data or {}
            table = Table(title="Project Context")
            table.add_column("Field")
            table.add_column("Value")
            table.add_row("Workspace", str(data.get("workspace_path", "")))
            table.add_row("Project", str(data.get("project_name", "")))
            table.add_row("Type", str(data.get("project_type", "")))
            table.add_row("Primary language", str(data.get("primary_language", "unknown")))
            table.add_row("Languages", ", ".join(data.get("languages", [])))
            table.add_row("Frameworks", ", ".join(data.get("frameworks", [])))
            if data.get("context_dir"):
                table.add_row("Context directory", str(data.get("context_dir")))
            self.console.print(table)

            generated_files = data.get("generated_files", []) or []
            if generated_files:
                files_table = Table(title="Generated Context Files")
                files_table.add_column("Name")
                files_table.add_column("Path")
                files_table.add_column("Description")
                for item in generated_files:
                    files_table.add_row(str(item.get("name", "")), str(item.get("path", "")), str(item.get("description", "")))
                self.console.print(files_table)
            return

        if result.tool == "context.path":
            data = result.data or {}
            table = Table(title="Project Context Path")
            table.add_column("Field")
            table.add_column("Value")
            table.add_row("Workspace", str(data.get("workspace_path", "")))
            table.add_row("Context directory", str(data.get("context_dir", "")))
            table.add_row("Exists", str(data.get("exists", False)))
            self.console.print(table)
            return


        if result.tool == "workflow.list":
            table = Table(title="Registered Workflows")
            table.add_column("Name")
            table.add_column("Type")
            table.add_column("Requires LLM")
            table.add_column("Aliases")
            table.add_column("Description")
            for workflow in (result.data or {}).get("workflows", []):
                table.add_row(
                    str(workflow.get("name", "")),
                    str(workflow.get("workflow_type", "")),
                    str(workflow.get("requires_llm", False)),
                    ", ".join(workflow.get("aliases", []) or []),
                    str(workflow.get("description", "")),
                )
            self.console.print(table)
            return

        if result.tool == "workflow.show":
            data = result.data or {}
            table = Table(title="Workflow")
            table.add_column("Field")
            table.add_column("Value")
            table.add_row("Name", str(data.get("name", "")))
            table.add_row("Type", str(data.get("workflow_type", "")))
            table.add_row("Requires LLM", str(data.get("requires_llm", False)))
            table.add_row("Aliases", ", ".join(data.get("aliases", []) or []))
            table.add_row("Description", str(data.get("description", "")))
            self.console.print(table)
            return

        if result.tool == "workflow.run":
            data = result.data or {}
            table = Table(title="Workflow Run")
            table.add_column("Field")
            table.add_column("Value")
            for key in ("run_id", "workflow", "workspace_path", "session_id", "duration_ms", "scan_path", "context_path", "run_file", "state_file", "events_file"):
                if data.get(key):
                    value = _format_duration(data.get(key)) if key == "duration_ms" else str(data.get(key))
                    table.add_row(key.replace("_", " ").title(), value)
            self.console.print(table)
            generated_files = data.get("generated_files", []) or []
            if generated_files:
                files_table = Table(title="Generated Files")
                files_table.add_column("Path")
                for path in generated_files:
                    files_table.add_row(str(path))
                self.console.print(files_table)
            return

        if result.tool == "workflow.runs":
            table = Table(title="Recent Workflow Runs")
            table.add_column("ID")
            table.add_column("Workflow")
            table.add_column("Status")
            table.add_column("Duration")
            table.add_column("Started")
            table.add_column("Completed")
            for run in (result.data or {}).get("runs", []):
                table.add_row(
                    str(run.get("id", "")),
                    str(run.get("workflow", "")),
                    str(run.get("status", "")),
                    _format_duration(run.get("duration_ms")),
                    str(run.get("started_at", "")),
                    str(run.get("completed_at", "")),
                )
            self.console.print(table)
            return

        if result.tool in {"workflow.run.show", "workflow.last"}:
            data = result.data or {}
            run = data.get("run", {}) or {}
            state = data.get("state", {}) or {}
            table = Table(title="Workflow Run Details")
            table.add_column("Field")
            table.add_column("Value")
            for key in ("id", "workflow", "status", "duration_ms", "workspace_path", "session_id", "started_at", "completed_at", "error"):
                if run.get(key):
                    value = _format_duration(run.get(key)) if key == "duration_ms" else str(run.get(key))
                    table.add_row(key.replace("_", " ").title(), value)
            if state.get("context_path"):
                table.add_row("Context Path", str(state.get("context_path")))
            self.console.print(table)
            generated_files = state.get("generated_files", []) or []
            if generated_files:
                files_table = Table(title="Generated Files")
                files_table.add_column("Path")
                for path in generated_files:
                    files_table.add_row(str(path))
                self.console.print(files_table)
            events = (data.get("events", []) or [])[-10:]
            if events:
                events_table = Table(title="Recent Workflow Events")
                events_table.add_column("Type")
                events_table.add_column("Node")
                events_table.add_column("Duration")
                events_table.add_column("Message")
                for event in events:
                    events_table.add_row(
                        str(event.get("type", "")),
                        str(event.get("node", "")),
                        _format_duration(event.get("duration_ms")),
                        str(event.get("message", "") or ""),
                    )
                self.console.print(events_table)
            return


        if result.tool in {"git.status", "git.diff", "shell.run"}:
            stdout = result.data.get("stdout", "")
            stderr = result.data.get("stderr", "")
            if stdout:
                self.console.print(stdout)
            if stderr:
                self.console.print(f"[yellow]{stderr}[/yellow]")
            return

        self.console.print(result.model_dump())

from __future__ import annotations

import json
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table

from dr_magu.result import ToolResult


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

        if result.tool in {"git.status", "git.diff", "shell.run"}:
            stdout = result.data.get("stdout", "")
            stderr = result.data.get("stderr", "")
            if stdout:
                self.console.print(stdout)
            if stderr:
                self.console.print(f"[yellow]{stderr}[/yellow]")
            return

        self.console.print(result.model_dump())

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

        if result.tool in {"git.status", "git.diff", "shell.run"}:
            stdout = result.data.get("stdout", "")
            stderr = result.data.get("stderr", "")
            if stdout:
                self.console.print(stdout)
            if stderr:
                self.console.print(f"[yellow]{stderr}[/yellow]")
            return

        self.console.print(result.model_dump())

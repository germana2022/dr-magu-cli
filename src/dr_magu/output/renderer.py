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


        if result.tool == "agent.list":
            table = Table(title="Configured Agents")
            table.add_column("ID")
            table.add_column("Enabled")
            table.add_column("Deleted")
            table.add_column("Source")
            table.add_column("Plugin")
            table.add_column("Workflow")
            table.add_column("Model")
            table.add_column("Description")
            for agent in (result.data or {}).get("agents", []):
                model = agent.get("model", {}) or {}
                table.add_row(
                    str(agent.get("id", "")),
                    str(agent.get("enabled", False)),
                    str(agent.get("deleted", False)),
                    str(agent.get("source", "")),
                    str(agent.get("plugin_id", "") or ""),
                    str(agent.get("workflow", "")),
                    f"{model.get('provider', '')}/{model.get('model', '')}",
                    str(agent.get("description", "")),
                )
            self.console.print(table)
            return

        if result.tool == "agent.show":
            data = result.data or {}
            model = data.get("model", {}) or {}
            table = Table(title="Agent")
            table.add_column("Field")
            table.add_column("Value")
            for key in ("id", "name", "role", "workflow", "enabled", "deleted", "requires_llm", "source", "plugin_id", "description"):
                table.add_row(key.replace("_", " ").title(), str(data.get(key, "")))
            table.add_row("Model Provider", str(model.get("provider", "")))
            table.add_row("Model", str(model.get("model", "")))
            table.add_row("Temperature", str(model.get("temperature", "")))
            table.add_row("API Key Configured", str(model.get("api_key_configured", False)))
            table.add_row("Model Source", str(model.get("source", "")))
            self.console.print(table)
            return

        if result.tool == "agent.run":
            data = result.data or {}
            agent = data.get("agent", {}) or {}
            workflow_result = data.get("workflow_result", {}) or {}
            table = Table(title="Agent Run")
            table.add_column("Field")
            table.add_column("Value")
            table.add_row("Agent", str(agent.get("id", "")))
            table.add_row("Workflow", str(agent.get("workflow", "")))
            table.add_row("Workflow Success", str(data.get("workflow_success", False)))
            for key in ("run_id", "duration_ms", "context_path"):
                if workflow_result.get(key):
                    value = _format_duration(workflow_result.get(key)) if key == "duration_ms" else str(workflow_result.get(key))
                    table.add_row(key.replace("_", " ").title(), value)
            self.console.print(table)
            return


        if result.tool in {"agent.add", "agent.update", "agent.enable", "agent.disable", "agent.delete"}:
            data = result.data or {}
            agent = data.get("agent", {}) or {}
            table = Table(title=result.tool.replace(".", " ").title())
            table.add_column("Field")
            table.add_column("Value")
            for key in ("id", "name", "enabled", "deleted", "source", "plugin_id", "workflow"):
                table.add_row(key.replace("_", " ").title(), str(agent.get(key, "")))
            if data.get("store_path"):
                table.add_row("Store Path", str(data.get("store_path")))
            self.console.print(table)
            return

        if result.tool == "agent.validate":
            data = result.data or {}
            agent = data.get("agent", {}) or {}
            table = Table(title="Agent Validation")
            table.add_column("Field")
            table.add_column("Value")
            table.add_row("Agent", str(agent.get("id", "")))
            table.add_row("Valid", str(data.get("valid", False)))
            table.add_row("Workflow", str(agent.get("workflow", "")))
            table.add_row("Source", str(agent.get("source", "")))
            self.console.print(table)
            errors = data.get("errors", []) or []
            if errors:
                error_table = Table(title="Validation Errors")
                error_table.add_column("Error")
                for error in errors:
                    error_table.add_row(str(error))
                self.console.print(error_table)
            return

        if result.tool == "brain.context":
            data = result.data or {}
            summary = data.get("summary", {}) or {}
            default_model = data.get("default_model", {}) or {}
            table = Table(title="Brain Context")
            table.add_column("Field")
            table.add_column("Value")
            table.add_row("Commands", str(summary.get("command_count", 0)))
            table.add_row("Workflows", str(summary.get("workflow_count", 0)))
            table.add_row("Tools", str(summary.get("tool_count", 0)))
            table.add_row("Agents", str(summary.get("agent_count", 0)))
            table.add_row("Default Provider", str(default_model.get("provider", "")))
            table.add_row("Default Model", str(default_model.get("model", "")))
            table.add_row("Temperature", str(default_model.get("temperature", "")))
            table.add_row("API Key Configured", str(default_model.get("api_key_configured", False)))
            table.add_row("LLM Calls Enabled", str(summary.get("llm_calls_enabled", False)))
            self.console.print(table)
            return

        if result.tool == "tools.list":
            table = Table(title="Formal Tool Registry")
            table.add_column("Name")
            table.add_column("Category")
            table.add_column("Read Only")
            table.add_column("Approval")
            table.add_column("Description")
            for tool in (result.data or {}).get("tools", []):
                table.add_row(
                    str(tool.get("name", "")),
                    str(tool.get("category", "")),
                    str(tool.get("read_only", True)),
                    str(tool.get("requires_approval", False)),
                    str(tool.get("description", "")),
                )
            self.console.print(table)
            return

        if result.tool == "permissions.show":
            data = result.data or {}
            table = Table(title="Permission Context")
            table.add_column("Permission")
            table.add_column("Value")
            for key, value in data.items():
                table.add_row(key.replace("_", " ").title(), str(value))
            self.console.print(table)
            return

        if result.tool == "runtime.inspect":
            data = result.data or {}
            workspace = data.get("workspace", {}) or {}
            session = data.get("session", {}) or {}
            summary = data.get("summary", {}) or {}
            table = Table(title="Runtime Introspection")
            table.add_column("Section")
            table.add_column("Value")
            table.add_row("Workspace", str(workspace.get("path", "")))
            table.add_row("Workspace Exists", str(workspace.get("exists", False)))
            table.add_row("Git Repository", str(workspace.get("is_git_repository", False)))
            table.add_row("Current Session", str(session.get("id") or "none"))
            table.add_row("Commands", str(summary.get("command_count", len(data.get("commands", []) or []))))
            table.add_row("Workflows", str(summary.get("workflow_count", len(data.get("workflows", []) or []))))
            table.add_row("Tools", str(summary.get("tool_count", len(data.get("tools", []) or []))))
            table.add_row("Agents", str(summary.get("agent_count", len(data.get("agents", []) or []))))
            table.add_row("Brain Ready", str(summary.get("brain_ready", False)))
            self.console.print(table)

            commands = data.get("commands", []) or []
            if commands:
                commands_table = Table(title="Registered Commands")
                commands_table.add_column("Name")
                commands_table.add_column("Category")
                commands_table.add_column("Aliases")
                for command in commands:
                    commands_table.add_row(
                        str(command.get("name", "")),
                        str(command.get("category", "")),
                        ", ".join(command.get("aliases", []) or []),
                    )
                self.console.print(commands_table)

            workflows = data.get("workflows", []) or []
            if workflows:
                workflows_table = Table(title="Registered Workflows")
                workflows_table.add_column("Name")
                workflows_table.add_column("Type")
                workflows_table.add_column("Requires LLM")
                for workflow in workflows:
                    workflows_table.add_row(
                        str(workflow.get("name", "")),
                        str(workflow.get("workflow_type", "")),
                        str(workflow.get("requires_llm", False)),
                    )
                self.console.print(workflows_table)
            return

        if result.tool == "control.center":
            data = result.data or {}
            table = Table(title="Dr Magu Control Center")
            table.add_column("Area")
            table.add_column("Count")
            table.add_column("Enabled")
            table.add_column("Status")
            table.add_column("Description")
            for section in data.get("sections", []) or []:
                enabled = section.get("enabled_count")
                table.add_row(
                    str(section.get("name", "")),
                    str(section.get("count", 0)),
                    "" if enabled is None else str(enabled),
                    str(section.get("status", "")),
                    str(section.get("description", "")),
                )
            self.console.print(table)

            plugins = data.get("plugins", []) or []
            if plugins:
                plugins_table = Table(title="Plugin Impact")
                plugins_table.add_column("Plugin")
                plugins_table.add_column("Enabled")
                plugins_table.add_column("Domain")
                plugins_table.add_column("Health")
                plugins_table.add_column("Agents")
                plugins_table.add_column("Workflows")
                plugins_table.add_column("Tools")
                for plugin in plugins:
                    plugins_table.add_row(
                        str(plugin.get("plugin_id", "")),
                        str(plugin.get("enabled", False)),
                        str(plugin.get("domain", "")),
                        str(plugin.get("status", "")),
                        str(len(plugin.get("agents", []) or [])),
                        str(len(plugin.get("workflows", []) or [])),
                        str(len(plugin.get("tools", []) or [])),
                    )
                self.console.print(plugins_table)

            brain = data.get("brain", {}) or {}
            summary = brain.get("summary", {}) or {}
            model = brain.get("default_model", {}) or {}
            brain_table = Table(title="Brain Readiness")
            brain_table.add_column("Field")
            brain_table.add_column("Value")
            for key in ("brain_ready", "llm_configured", "default_provider", "default_model", "llm_calls_enabled"):
                brain_table.add_row(key.replace("_", " ").title(), str(summary.get(key, model.get(key, ""))))
            self.console.print(brain_table)
            return

        if result.tool == "control.plugin":
            data = result.data or {}
            table = Table(title="Plugin Control Center Detail")
            table.add_column("Field")
            table.add_column("Value")
            for key in ("plugin_id", "name", "enabled", "domain", "status"):
                table.add_row(key.replace("_", " ").title(), str(data.get(key, "")))
            self.console.print(table)
            for key in ("agents", "workflows", "tools", "commands", "schedules"):
                values = data.get(key, []) or []
                values_table = Table(title=key.title())
                values_table.add_column("Name")
                for value in values:
                    values_table.add_row(str(value))
                self.console.print(values_table)
            warnings = data.get("warnings", []) or []
            errors = data.get("errors", []) or []
            if warnings or errors:
                health_table = Table(title="Health Details")
                health_table.add_column("Type")
                health_table.add_column("Message")
                for warning in warnings:
                    health_table.add_row("warning", str(warning))
                for error in errors:
                    health_table.add_row("error", str(error))
                self.console.print(health_table)
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

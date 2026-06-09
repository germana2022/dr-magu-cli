from __future__ import annotations

from dr_magu.commands.definitions import CommandDefinition
from dr_magu.commands.context import CommandContext
from dr_magu.result import ToolResult
from dr_magu.tools.file_tools import list_files, read_file
from dr_magu.tools.git_tools import git_diff, git_status
from dr_magu.tools.search_tools import search_code
from dr_magu.tools.shell_tools import run_shell
from dr_magu.scanner.repository_scanner import scan_repository
from dr_magu.project_context.generator import generate_project_context, get_context_path, show_project_context
from dr_magu.workflows.runner import WorkflowRunner


def _get_str(args: dict[str, object], key: str, default: str) -> str:
    value = args.get(key, default)
    return str(value)




def _get_bool(args: dict[str, object], key: str, default: bool = False) -> bool:
    value = args.get(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)

def _get_int(args: dict[str, object], key: str, default: int) -> int:
    value = args.get(key, default)
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def handle_files_list(args: dict[str, object], context: CommandContext) -> ToolResult:
    return list_files(
        context.workspace_path,
        target_path=_get_str(args, "path", "."),
        max_files=_get_int(args, "max_files", 500),
    )


def handle_files_read(args: dict[str, object], context: CommandContext) -> ToolResult:
    return read_file(
        context.workspace_path,
        file_path=_get_str(args, "path", ""),
        max_chars=_get_int(args, "max_chars", 20000),
    )


def handle_search_code(args: dict[str, object], context: CommandContext) -> ToolResult:
    return search_code(
        context.workspace_path,
        query=_get_str(args, "query", ""),
        target_path=_get_str(args, "path", "."),
        max_results=_get_int(args, "max_results", 100),
    )


def handle_git_status(args: dict[str, object], context: CommandContext) -> ToolResult:
    return git_status(context.workspace_path)


def handle_git_diff(args: dict[str, object], context: CommandContext) -> ToolResult:
    return git_diff(context.workspace_path)


def handle_shell_run(args: dict[str, object], context: CommandContext) -> ToolResult:
    blocked_patterns = context.config.get("blocked_shell_patterns", [])
    return run_shell(
        context.workspace_path,
        command=_get_str(args, "command", ""),
        blocked_patterns=list(blocked_patterns),
        timeout_seconds=_get_int(args, "timeout_seconds", 120),
    )


def handle_repo_scan(args: dict[str, object], context: CommandContext) -> ToolResult:
    return scan_repository(
        context.workspace_path,
        max_files=_get_int(args, "max_files", 5000),
    )


def handle_context_generate(args: dict[str, object], context: CommandContext) -> ToolResult:
    return generate_project_context(
        context.workspace_path,
        refresh=_get_bool(args, "refresh", False),
    )


def handle_context_show(args: dict[str, object], context: CommandContext) -> ToolResult:
    return show_project_context(context.workspace_path)


def handle_context_path(args: dict[str, object], context: CommandContext) -> ToolResult:
    return get_context_path(context.workspace_path)


def handle_workflow_list(args: dict[str, object], context: CommandContext) -> ToolResult:
    return WorkflowRunner(context.workspace_path).list_workflows()


def handle_workflow_show(args: dict[str, object], context: CommandContext) -> ToolResult:
    return WorkflowRunner(context.workspace_path).show_workflow(_get_str(args, "name", "repository.context"))


def handle_workflow_run(args: dict[str, object], context: CommandContext) -> ToolResult:
    return WorkflowRunner(context.workspace_path).run(_get_str(args, "name", "repository.context"))


def handle_workflow_runs(args: dict[str, object], context: CommandContext) -> ToolResult:
    limit = _get_int(args, "limit", 20)
    return WorkflowRunner(context.workspace_path).list_runs(limit=limit)


def handle_workflow_last(args: dict[str, object], context: CommandContext) -> ToolResult:
    return WorkflowRunner(context.workspace_path).show_last_run()


def handle_workflow_run_show(args: dict[str, object], context: CommandContext) -> ToolResult:
    return WorkflowRunner(context.workspace_path).show_run(_get_str(args, "run_id", ""))


def handle_runtime_inspect(args: dict[str, object], context: CommandContext) -> ToolResult:
    from dr_magu.runtime.inspector import RuntimeInspector

    return RuntimeInspector(context.workspace_path, config=context.config).inspect_result()



def handle_agent_list(args: dict[str, object], context: CommandContext) -> ToolResult:
    from dr_magu.agents.runner import AgentRunner

    return AgentRunner(context.workspace_path).list_agents(
        include_disabled=_get_bool(args, "include_disabled", True),
        include_deleted=_get_bool(args, "include_deleted", False),
    )


def handle_agent_show(args: dict[str, object], context: CommandContext) -> ToolResult:
    from dr_magu.agents.runner import AgentRunner

    return AgentRunner(context.workspace_path).show_agent(_get_str(args, "id", _get_str(args, "value", "")))


def handle_agent_validate(args: dict[str, object], context: CommandContext) -> ToolResult:
    from dr_magu.agents.runner import AgentRunner

    return AgentRunner(context.workspace_path).validate_agent(_get_str(args, "id", _get_str(args, "value", "")))


def handle_agent_enable(args: dict[str, object], context: CommandContext) -> ToolResult:
    from dr_magu.agents.runner import AgentRunner

    return AgentRunner(context.workspace_path).enable_agent(_get_str(args, "id", _get_str(args, "value", "")))


def handle_agent_disable(args: dict[str, object], context: CommandContext) -> ToolResult:
    from dr_magu.agents.runner import AgentRunner

    return AgentRunner(context.workspace_path).disable_agent(_get_str(args, "id", _get_str(args, "value", "")))


def handle_agent_delete(args: dict[str, object], context: CommandContext) -> ToolResult:
    from dr_magu.agents.runner import AgentRunner

    return AgentRunner(context.workspace_path).delete_agent(_get_str(args, "id", _get_str(args, "value", "")))


def handle_agent_run(args: dict[str, object], context: CommandContext) -> ToolResult:
    from dr_magu.agents.runner import AgentRunner

    return AgentRunner(context.workspace_path).run_agent(_get_str(args, "id", _get_str(args, "value", "repository-analyzer")))


def handle_agent_add(args: dict[str, object], context: CommandContext) -> ToolResult:
    from dr_magu.agents.runner import AgentRunner

    return AgentRunner(context.workspace_path).add_agent_from_file(_get_str(args, "file", _get_str(args, "value", "")))


def handle_agent_update(args: dict[str, object], context: CommandContext) -> ToolResult:
    from dr_magu.agents.runner import AgentRunner

    agent_id = _get_str(args, "id", "") or _get_str(args, "agent_id", "")
    return AgentRunner(context.workspace_path).update_agent_from_file(agent_id, _get_str(args, "file", ""))


def handle_brain_context(args: dict[str, object], context: CommandContext) -> ToolResult:
    from dr_magu.brain.context_loader import BrainContextLoader

    return BrainContextLoader(context.workspace_path, config=context.config).load_result()



def handle_brain_route(args: dict[str, object], context: CommandContext) -> ToolResult:
    from dr_magu.brain.commands import brain_route

    prompt = _get_str(args, "prompt", _get_str(args, "value", ""))
    return ToolResult(success=True, tool="brain.route", data=brain_route(prompt))


def handle_research_search(args: dict[str, object], context: CommandContext) -> ToolResult:
    from dr_magu.research.runner import WebResearchRunner

    topic = _get_str(args, "topic", _get_str(args, "value", ""))
    limit = int(args.get("limit", 5) or 5)
    return WebResearchRunner(context.workspace_path).search(topic, limit=limit)

def handle_tools_list(args: dict[str, object], context: CommandContext) -> ToolResult:
    from dr_magu.tools.registry import ToolRegistry

    return ToolResult(success=True, tool="tools.list", data=ToolRegistry().as_result_data())


def handle_permissions_show(args: dict[str, object], context: CommandContext) -> ToolResult:
    from dr_magu.security.permission_context import PermissionContextReader

    return ToolResult(success=True, tool="permissions.show", data=PermissionContextReader(context.config).read().model_dump())


def handle_plugin_list(args: dict[str, object], context: CommandContext) -> ToolResult:
    from dr_magu.plugins.manager import PluginManager

    return PluginManager(context.workspace_path).list_plugins()


def handle_plugin_show(args: dict[str, object], context: CommandContext) -> ToolResult:
    from dr_magu.plugins.manager import PluginManager

    return PluginManager(context.workspace_path).show_plugin(_get_str(args, "id", _get_str(args, "value", "")))


def handle_plugin_validate(args: dict[str, object], context: CommandContext) -> ToolResult:
    from dr_magu.plugins.manager import PluginManager

    plugin_id = _get_str(args, "id", _get_str(args, "value", "")).strip() or None
    return PluginManager(context.workspace_path).validate_plugin(plugin_id)


def handle_control_center(args: dict[str, object], context: CommandContext) -> ToolResult:
    from dr_magu.control_center.service import ControlCenterService

    return ControlCenterService(context.workspace_path, config=context.config).dashboard_result()


def handle_control_plugin(args: dict[str, object], context: CommandContext) -> ToolResult:
    from dr_magu.control_center.service import ControlCenterService

    plugin_id = _get_str(args, "id", _get_str(args, "value", "")).strip()
    return ControlCenterService(context.workspace_path, config=context.config).plugin_impact_result(plugin_id)


def handle_contracts_tools(args: dict[str, object], context: CommandContext) -> ToolResult:
    from dr_magu.tools.registry import ToolRegistry

    return ToolResult(success=True, tool="contracts.tools", data=ToolRegistry().as_result_data())


def handle_plan_validate(args: dict[str, object], context: CommandContext) -> ToolResult:
    from dr_magu.plans.models import BrainPlan
    from dr_magu.plans.validator import PlanValidator

    raw_plan = args.get("plan")
    if isinstance(raw_plan, dict):
        plan = BrainPlan.model_validate(raw_plan)
    else:
        # Safe sample plan used for CLI/TUI smoke checks before v0.10.0 starts
        # producing real LLM plans.
        plan = BrainPlan(
            intent=str(args.get("intent", "runtime_contract_validation")),
            language=str(args.get("language", "en")),
            confidence=1.0,
            steps=[],
            explanation="No executable steps were provided.",
        )
    validation = PlanValidator().validate(plan)
    return ToolResult(success=validation.valid, tool="plan.validate", data=validation.model_dump())

class CommandRegistry:
    """In-memory registry used by both direct CLI commands and the run processor."""

    def __init__(self) -> None:
        self._commands: dict[str, CommandDefinition] = {}
        self._aliases: dict[str, str] = {}

    def register(self, command: CommandDefinition) -> None:
        self._commands[command.name] = command
        for alias in command.aliases:
            self._aliases[alias] = command.name

    def get(self, name: str) -> CommandDefinition:
        resolved_name = self._aliases.get(name, name)
        if resolved_name not in self._commands:
            available = ", ".join(sorted(self._commands))
            raise KeyError(f"Unknown command '{name}'. Available commands: {available}")
        return self._commands[resolved_name]

    def list_commands(self) -> list[CommandDefinition]:
        return sorted(self._commands.values(), key=lambda item: item.name)


registry = CommandRegistry()

registry.register(CommandDefinition(
    name="files.list",
    aliases=["fl"],
    description="List files inside the workspace.",
    category="files",
    handler=handle_files_list,
))
registry.register(CommandDefinition(
    name="files.read",
    aliases=["fr"],
    description="Read a text file from the workspace.",
    category="files",
    handler=handle_files_read,
))
registry.register(CommandDefinition(
    name="search.code",
    aliases=["sc"],
    description="Search text across source files.",
    category="search",
    handler=handle_search_code,
))
registry.register(CommandDefinition(
    name="git.status",
    aliases=["gs"],
    description="Show git status for the workspace.",
    category="git",
    handler=handle_git_status,
))
registry.register(CommandDefinition(
    name="git.diff",
    aliases=["gd"],
    description="Show git diff for the workspace.",
    category="git",
    handler=handle_git_diff,
))
registry.register(CommandDefinition(
    name="shell.run",
    aliases=["sh"],
    description="Run a shell command inside the workspace.",
    category="shell",
    handler=handle_shell_run,
))

registry.register(CommandDefinition(
    name="repo.scan",
    aliases=["scan", "rs"],
    description="Scan the workspace and detect repository metadata.",
    category="repository",
    handler=handle_repo_scan,
))

registry.register(CommandDefinition(
    name="context.generate",
    aliases=["context", "cg"],
    description="Generate deterministic project context files from repository scan metadata.",
    category="context",
    handler=handle_context_generate,
))
registry.register(CommandDefinition(
    name="context.show",
    aliases=["cs"],
    description="Show the generated structured project context.",
    category="context",
    handler=handle_context_show,
))
registry.register(CommandDefinition(
    name="context.path",
    aliases=["cp"],
    description="Show the project context directory path.",
    category="context",
    handler=handle_context_path,
))

registry.register(CommandDefinition(
    name="workflow.list",
    aliases=["wl"],
    description="List registered deterministic workflows.",
    category="workflow",
    handler=handle_workflow_list,
))
registry.register(CommandDefinition(
    name="workflow.show",
    aliases=["ws"],
    description="Show workflow metadata.",
    category="workflow",
    handler=handle_workflow_show,
))
registry.register(CommandDefinition(
    name="workflow.run",
    aliases=["wr", "wf"],
    description="Run a registered workflow.",
    category="workflow",
    handler=handle_workflow_run,
))
registry.register(CommandDefinition(
    name="workflow.runs",
    aliases=["wrs"],
    description="List persisted workflow runs for the workspace.",
    category="workflow",
    handler=handle_workflow_runs,
))
registry.register(CommandDefinition(
    name="workflow.last",
    aliases=["wlast"],
    description="Show the latest persisted workflow run and state.",
    category="workflow",
    handler=handle_workflow_last,
))
registry.register(CommandDefinition(
    name="workflow.run.show",
    aliases=["wshow"],
    description="Show a persisted workflow run and state.",
    category="workflow",
    handler=handle_workflow_run_show,
))

registry.register(CommandDefinition(
    name="runtime.inspect",
    aliases=["runtime", "ri"],
    description="Inspect commands, workflows, tools, permissions, session, workspace, and agent placeholders.",
    category="runtime",
    handler=handle_runtime_inspect,
))


registry.register(CommandDefinition(
    name="agent.list",
    aliases=["agents", "al"],
    description="List configured agents with resolved model configuration.",
    category="agent",
    handler=handle_agent_list,
))
registry.register(CommandDefinition(
    name="agent.show",
    aliases=["as"],
    description="Show one configured agent and its resolved model configuration.",
    category="agent",
    handler=handle_agent_show,
))


registry.register(CommandDefinition(
    name="agent.add",
    aliases=["aa"],
    description="Add a workspace-managed agent from a YAML file.",
    category="agent",
    handler=handle_agent_add,
))
registry.register(CommandDefinition(
    name="agent.update",
    aliases=["au"],
    description="Update a workspace-managed agent from a YAML file.",
    category="agent",
    handler=handle_agent_update,
))

registry.register(CommandDefinition(
    name="agent.validate",
    aliases=["av"],
    description="Validate one configured agent and its workflow binding.",
    category="agent",
    handler=handle_agent_validate,
))
registry.register(CommandDefinition(
    name="agent.enable",
    aliases=["ae"],
    description="Enable an agent through a workspace override.",
    category="agent",
    handler=handle_agent_enable,
))
registry.register(CommandDefinition(
    name="agent.disable",
    aliases=["ad"],
    description="Disable an agent through a workspace override.",
    category="agent",
    handler=handle_agent_disable,
))
registry.register(CommandDefinition(
    name="agent.delete",
    aliases=["ax"],
    description="Soft-delete an agent through a workspace override.",
    category="agent",
    handler=handle_agent_delete,
))

registry.register(CommandDefinition(
    name="agent.run",
    aliases=["ar", "agent"],
    description="Run a configured agent by delegating to its bound workflow.",
    category="agent",
    handler=handle_agent_run,
))

registry.register(CommandDefinition(
    name="brain.route",
    aliases=["route", "intent"],
    description="Classify a natural-language prompt with the Intent Router.",
    category="brain",
    handler=handle_brain_route,
))


registry.register(CommandDefinition(
    name="research.search",
    aliases=["research", "web.search", "rs"],
    description="Search for structured research sources about a topic.",
    category="research",
    handler=handle_research_search,
))

registry.register(CommandDefinition(
    name="brain.context",
    aliases=["brain", "bc"],
    description="Load Brain context including commands, workflows, agents, tools, permissions, session, workspace, and model defaults.",
    category="brain",
    handler=handle_brain_context,
))
registry.register(CommandDefinition(
    name="tools.list",
    aliases=["tools", "tl"],
    description="List formal tool registry entries exposed to the Brain.",
    category="tools",
    handler=handle_tools_list,
))
registry.register(CommandDefinition(
    name="permissions.show",
    aliases=["permissions", "ps"],
    description="Show the effective permission context used by the Brain and validator.",
    category="permissions",
    handler=handle_permissions_show,
))

registry.register(CommandDefinition(
    name="plugin.list",
    aliases=["plugins", "pl"],
    description="List discovered local plugins and the resources they provide.",
    category="plugin",
    handler=handle_plugin_list,
))
registry.register(CommandDefinition(
    name="plugin.show",
    aliases=["pshow"],
    description="Show one discovered local plugin manifest.",
    category="plugin",
    handler=handle_plugin_show,
))
registry.register(CommandDefinition(
    name="plugin.validate",
    aliases=["pv"],
    description="Validate one plugin or all discovered local plugins.",
    category="plugin",
    handler=handle_plugin_validate,
))

registry.register(CommandDefinition(
    name="control.center",
    aliases=["control", "cc", "dashboard"],
    description="Show the Dr Magu Control Center dashboard across plugins, agents, workflows, tools, permissions, schedules, and Brain readiness.",
    category="control",
    handler=handle_control_center,
))
registry.register(CommandDefinition(
    name="control.plugin",
    aliases=["cplugin"],
    description="Show one plugin impact summary from the Control Center.",
    category="control",
    handler=handle_control_plugin,
))

registry.register(CommandDefinition(
    name="contracts.tools",
    aliases=["contracts", "ct"],
    description="List formal runtime tool contracts exposed to the Brain plan validator.",
    category="contracts",
    handler=handle_contracts_tools,
))
registry.register(CommandDefinition(
    name="plan.validate",
    aliases=["pvld"],
    description="Validate a structured Brain plan without executing it.",
    category="plan",
    handler=handle_plan_validate,
))

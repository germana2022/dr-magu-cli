from __future__ import annotations

from pathlib import Path

from dr_magu.agents.registry import AgentRegistry
from dr_magu.brain.context_loader import BrainContextLoader
from dr_magu.commands.registry import registry as command_registry
from dr_magu.control_center.models import ControlCenterDashboard, ControlCenterSection, PluginImpact
from dr_magu.plugins.registry import PluginRegistry
from dr_magu.result import ToolResult
from dr_magu.runtime.inspector import RuntimeInspector
from dr_magu.security.permission_context import PermissionContextReader
from dr_magu.tools.registry import ToolRegistry
from dr_magu.config import load_config


class ControlCenterService:
    """Builds the Control Center dashboard from all Dr Magu registries.

    The Control Center is intentionally read-only in v0.9.3. It gives users one
    place to inspect plugins, agents, workflows, tools, permissions, schedules,
    and Brain readiness before the AI Orchestrator Brain starts executing plans.
    """

    def __init__(self, workspace_path: str | Path, config: dict | None = None) -> None:
        self.workspace_path = Path(workspace_path).resolve()
        self.config = config if config is not None else load_config()

    def dashboard(self) -> ControlCenterDashboard:
        runtime = RuntimeInspector(str(self.workspace_path), config=self.config).inspect()
        brain_snapshot = BrainContextLoader(str(self.workspace_path), config=self.config).load()
        plugins = PluginRegistry(self.workspace_path).list()
        agents = AgentRegistry(self.workspace_path).list(include_deleted=True)
        tools = ToolRegistry().list_tools()
        commands = command_registry.list_commands()
        permissions = PermissionContextReader(self.config).read()

        plugin_impacts: list[PluginImpact] = []
        for plugin in plugins:
            validation_errors = plugin.validation_errors or []
            warnings: list[str] = []
            if not plugin.enabled:
                warnings.append("Plugin is disabled.")
            if not plugin.provides.agents and not plugin.provides.workflows and not plugin.provides.tools:
                warnings.append("Plugin does not declare agents, workflows, or tools.")
            status = "error" if validation_errors else "warning" if warnings else "healthy"
            plugin_impacts.append(
                PluginImpact(
                    plugin_id=plugin.id,
                    name=plugin.name,
                    enabled=plugin.enabled,
                    domain=plugin.domain,
                    status=status,
                    agents=plugin.provides.agents,
                    workflows=plugin.provides.workflows,
                    tools=plugin.provides.tools,
                    commands=plugin.provides.commands,
                    schedules=plugin.provides.schedules,
                    warnings=warnings,
                    errors=validation_errors,
                )
            )

        enabled_plugins = [plugin for plugin in plugins if plugin.enabled]
        enabled_agents = [agent for agent in agents if agent.enabled and not agent.deleted]
        enabled_tools = tools

        sections = [
            ControlCenterSection(
                name="Plugins",
                count=len(plugins),
                enabled_count=len(enabled_plugins),
                status="available",
                description="Local plugin registry and plugin-provided resources.",
            ),
            ControlCenterSection(
                name="Agents",
                count=len(agents),
                enabled_count=len(enabled_agents),
                status="available",
                description="Configured plugin and workspace agents.",
            ),
            ControlCenterSection(
                name="Workflows",
                count=len(runtime.workflows),
                enabled_count=len(runtime.workflows),
                status="available",
                description="Registered deterministic workflows.",
            ),
            ControlCenterSection(
                name="Tools",
                count=len(tools),
                enabled_count=len(enabled_tools),
                status="available",
                description="Formal tool registry entries exposed to the Brain.",
            ),
            ControlCenterSection(
                name="Permissions",
                count=len(permissions.model_dump()),
                enabled_count=None,
                status="available",
                description="Effective local permission policy summary.",
            ),
            ControlCenterSection(
                name="Schedules",
                count=0,
                enabled_count=0,
                status="reserved",
                description="Reserved area for future cron/background task management.",
            ),
            ControlCenterSection(
                name="Brain",
                count=1,
                enabled_count=1 if brain_snapshot.summary.get("brain_ready") else 0,
                status="ready" if brain_snapshot.summary.get("brain_ready") else "not-ready",
                description="Brain context and default model readiness.",
            ),
        ]

        return ControlCenterDashboard(
            workspace_path=str(self.workspace_path),
            sections=sections,
            plugins=plugin_impacts,
            brain={
                "summary": brain_snapshot.summary,
                "default_model": brain_snapshot.default_model,
            },
            permissions=permissions.model_dump(),
            schedules={
                "status": "reserved",
                "message": "Scheduler Runtime is planned for a future version.",
            },
        )

    def dashboard_result(self) -> ToolResult:
        return ToolResult(success=True, tool="control.center", data=self.dashboard().model_dump())

    def plugin_impact_result(self, plugin_id: str) -> ToolResult:
        dashboard = self.dashboard()
        for plugin in dashboard.plugins:
            if plugin.plugin_id == plugin_id:
                return ToolResult(success=True, tool="control.plugin", data=plugin.model_dump())
        available = ", ".join(sorted(plugin.plugin_id for plugin in dashboard.plugins)) or "none"
        return ToolResult(success=False, tool="control.plugin", errors=[f"Unknown plugin '{plugin_id}'. Available plugins: {available}"])

from __future__ import annotations

from dr_magu.commands.registry import registry
from dr_magu.contracts.models import PermissionMode, RiskLevel, SchemaField, ToolContract

_TOOL_CATEGORIES = {
    "files",
    "git",
    "search",
    "shell",
    "repository",
    "context",
    "workflow",
    "runtime",
    "agent",
    "brain",
    "tools",
    "permissions",
    "plugin",
    "control",
    "contracts",
    "plan",
}

_TOOL_CONTRACT_OVERRIDES: dict[str, dict[str, object]] = {
    "files.list": {
        "input_schema": [SchemaField(name="path", default=".", description="Workspace-relative path to list."), SchemaField(name="max_files", type="integer", default=500)],
        "output_schema": [SchemaField(name="files", type="array"), SchemaField(name="count", type="integer")],
        "read_only": True,
        "risk_level": RiskLevel.low,
        "background_allowed": True,
    },
    "files.read": {
        "input_schema": [SchemaField(name="path", required=True, description="Workspace-relative file path."), SchemaField(name="max_chars", type="integer", default=20000)],
        "output_schema": [SchemaField(name="content"), SchemaField(name="truncated", type="boolean")],
        "read_only": True,
        "risk_level": RiskLevel.low,
        "background_allowed": True,
    },
    "search.code": {
        "input_schema": [SchemaField(name="query", required=True), SchemaField(name="path", default="."), SchemaField(name="max_results", type="integer", default=100)],
        "output_schema": [SchemaField(name="results", type="array")],
        "read_only": True,
        "risk_level": RiskLevel.low,
        "background_allowed": True,
    },
    "git.status": {"read_only": True, "risk_level": RiskLevel.low, "background_allowed": True},
    "git.diff": {"read_only": True, "risk_level": RiskLevel.low, "background_allowed": True},
    "shell.run": {
        "input_schema": [SchemaField(name="command", required=True), SchemaField(name="timeout_seconds", type="integer", default=120)],
        "output_schema": [SchemaField(name="stdout"), SchemaField(name="stderr"), SchemaField(name="return_code", type="integer")],
        "read_only": False,
        "risk_level": RiskLevel.high,
        "permission_mode": PermissionMode.approval_required,
        "requires_approval": True,
        "background_allowed": False,
        "interactive_only": True,
    },
    "repo.scan": {"read_only": True, "risk_level": RiskLevel.low, "background_allowed": True},
    "context.generate": {
        "input_schema": [SchemaField(name="refresh", type="boolean", default=False)],
        "read_only": False,
        "risk_level": RiskLevel.medium,
        "permission_mode": PermissionMode.allowed,
        "background_allowed": True,
    },
    "workflow.run": {
        "input_schema": [SchemaField(name="name", default="repository.context")],
        "read_only": False,
        "risk_level": RiskLevel.medium,
        "permission_mode": PermissionMode.allowed,
        "background_allowed": True,
    },
    "agent.run": {
        "input_schema": [SchemaField(name="id", default="repository-analyzer")],
        "read_only": False,
        "risk_level": RiskLevel.medium,
        "permission_mode": PermissionMode.allowed,
        "background_allowed": True,
    },
    "agent.add": {"read_only": False, "risk_level": RiskLevel.medium, "permission_mode": PermissionMode.approval_required, "requires_approval": True, "background_allowed": False},
    "agent.update": {"read_only": False, "risk_level": RiskLevel.medium, "permission_mode": PermissionMode.approval_required, "requires_approval": True, "background_allowed": False},
    "agent.delete": {"read_only": False, "risk_level": RiskLevel.high, "permission_mode": PermissionMode.approval_required, "requires_approval": True, "background_allowed": False},
    "contracts.tools": {"read_only": True, "risk_level": RiskLevel.low, "background_allowed": True},
    "plan.validate": {"read_only": True, "risk_level": RiskLevel.low, "background_allowed": True},
}


class ToolRegistry:
    """Formal registry that exposes tool contracts to the Brain.

    v0.9.4 still keeps command compatibility, but the public Brain-facing API is
    now ToolContract instead of raw command strings.
    """

    def list_tools(self) -> list[ToolContract]:
        tools: list[ToolContract] = []
        for command in registry.list_commands():
            if command.category not in _TOOL_CATEGORIES:
                continue
            overrides = dict(_TOOL_CONTRACT_OVERRIDES.get(command.name, {}))
            tools.append(ToolContract(
                name=command.name,
                category=command.category,
                description=command.description,
                command=command.name,
                aliases=list(command.aliases),
                read_only=bool(overrides.pop("read_only", True)),
                requires_approval=bool(overrides.pop("requires_approval", command.requires_approval)),
                risk_level=overrides.pop("risk_level", RiskLevel.low),
                permission_mode=overrides.pop("permission_mode", PermissionMode.allowed),
                background_allowed=bool(overrides.pop("background_allowed", True)),
                interactive_only=bool(overrides.pop("interactive_only", False)),
                input_schema=overrides.pop("input_schema", []),
                output_schema=overrides.pop("output_schema", []),
            ))
        return tools

    def get(self, name: str) -> ToolContract | None:
        for tool in self.list_tools():
            if tool.name == name or name in tool.aliases:
                return tool
        return None

    def as_result_data(self) -> dict[str, object]:
        tools = [tool.model_dump(mode="json") for tool in self.list_tools()]
        return {
            "tools": tools,
            "count": len(tools),
            "contract_version": "0.9.4",
            "source": "formal_tool_contracts",
        }

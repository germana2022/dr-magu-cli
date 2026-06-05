from __future__ import annotations

from pathlib import Path

from dr_magu.plugins.models import PluginDefinition, PluginValidationResult


class PluginValidator:
    """Validates local plugin manifests and optional resource files."""

    REQUIRED_MANIFEST_FIELDS = {"id", "name", "version"}

    def validate(self, plugin: PluginDefinition) -> PluginValidationResult:
        errors = list(plugin.validation_errors)
        warnings: list[str] = []

        plugin_path = Path(plugin.path)
        manifest = plugin_path / "plugin.yaml"
        if not manifest.exists():
            errors.append("Missing plugin.yaml manifest.")

        if not plugin.id.strip():
            errors.append("Plugin id is required.")
        if not plugin.name.strip():
            errors.append("Plugin name is required.")

        optional_files = {
            "agents.yaml": plugin.provides.agents,
            "workflows.yaml": plugin.provides.workflows,
            "tools.yaml": plugin.provides.tools,
        }
        for file_name, declared_resources in optional_files.items():
            if declared_resources and not (plugin_path / file_name).exists():
                warnings.append(f"{file_name} is not present even though resources are declared in plugin.yaml.")

        return PluginValidationResult(
            plugin_id=plugin.id,
            valid=not errors,
            errors=errors,
            warnings=warnings,
        )

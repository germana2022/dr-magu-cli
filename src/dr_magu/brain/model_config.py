from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from dr_magu.brain.models import ResolvedModelConfig


_ENV_MAP = {
    "${LLM_PROVIDER}": "LLM_PROVIDER",
    "${LLM_BASE_URL}": "LLM_BASE_URL",
    "${LLM_MODEL}": "LLM_MODEL",
    "${LLM_TEMPERATURE}": "LLM_TEMPERATURE",
}


def _resolve_env_value(value: Any) -> Any:
    """Resolve simple ${VAR} placeholders used in YAML configuration."""
    if not isinstance(value, str):
        return value
    if value in _ENV_MAP:
        return os.getenv(_ENV_MAP[value])
    if value.startswith("${") and value.endswith("}"):
        return os.getenv(value[2:-1])
    return value


def _to_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


class ModelConfigLoader:
    """Loads default LLM configuration without creating an LLM client."""

    def __init__(self, workspace_path: str | Path, config_path: str | Path | None = None) -> None:
        self.workspace_path = Path(workspace_path).resolve()
        self.config_path = Path(config_path) if config_path else None

    def load_raw(self) -> dict[str, Any]:
        """Load model configuration from workspace or project config files."""
        candidates: list[Path] = []
        if self.config_path:
            candidates.append(self.config_path)
        candidates.extend([
            self.workspace_path / ".dr-magu" / "config" / "models.yaml",
            Path("config/models.yaml"),
        ])

        for candidate in candidates:
            if candidate.exists():
                with candidate.open("r", encoding="utf-8") as file:
                    return yaml.safe_load(file) or {}
        return {}

    def default_model(self) -> ResolvedModelConfig:
        raw = self.load_raw().get("default_model", {}) or {}

        provider = _resolve_env_value(raw.get("provider")) or os.getenv("LLM_PROVIDER") or "opencode"
        base_url = _resolve_env_value(raw.get("base_url")) or os.getenv("LLM_BASE_URL") or "https://opencode.ai/zen/go/v1"
        model = _resolve_env_value(raw.get("model")) or os.getenv("LLM_MODEL") or "deepseek-v4-flash"
        temperature = _to_float(_resolve_env_value(raw.get("temperature")) or os.getenv("LLM_TEMPERATURE"), 0.1)
        api_key_env = str(raw.get("api_key_env") or "LLM_API_KEY")

        return ResolvedModelConfig(
            provider=str(provider),
            base_url=str(base_url) if base_url else None,
            model=str(model),
            temperature=temperature,
            api_key_env=api_key_env,
            api_key_configured=bool(os.getenv(api_key_env)),
            source="config/models.yaml or environment",
        )


class ModelResolver:
    """Resolves agent model overrides with fallback to the Brain default model."""

    def __init__(self, default_model: ResolvedModelConfig) -> None:
        self.default_model = default_model

    def resolve(self, agent_model: dict[str, Any] | None = None) -> ResolvedModelConfig:
        agent_model = agent_model or {}
        provider = agent_model.get("provider") or self.default_model.provider
        base_url = agent_model.get("base_url") or self.default_model.base_url
        model = agent_model.get("model") or self.default_model.model
        temperature = _to_float(agent_model.get("temperature"), self.default_model.temperature)
        api_key_env = str(agent_model.get("api_key_env") or self.default_model.api_key_env)

        has_override = any(agent_model.get(key) is not None for key in ("provider", "base_url", "model", "temperature", "api_key_env"))
        return ResolvedModelConfig(
            provider=str(provider),
            base_url=str(base_url) if base_url else None,
            model=str(model),
            temperature=temperature,
            api_key_env=api_key_env,
            api_key_configured=bool(os.getenv(api_key_env)),
            source="agent override" if has_override else "brain default",
        )

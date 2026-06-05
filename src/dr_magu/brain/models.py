from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class ResolvedModelConfig(BaseModel):
    """Resolved model configuration used by the Brain or an agent.

    The API key value is never exposed in snapshots. Dr Magu only exposes whether
    a key is configured and the environment variable name used to resolve it.
    """

    provider: str = "opencode"
    base_url: str | None = None
    model: str = "deepseek-v4-flash"
    temperature: float = 0.1
    api_key_env: str = "LLM_API_KEY"
    api_key_configured: bool = False
    source: str = "defaults"


class BrainContextSnapshot(BaseModel):
    """Unified context snapshot consumed by the future Orchestrator Brain."""

    workspace: dict[str, Any]
    session: dict[str, Any]
    commands: list[dict[str, Any]] = Field(default_factory=list)
    workflows: list[dict[str, Any]] = Field(default_factory=list)
    tools: list[dict[str, Any]] = Field(default_factory=list)
    permissions: dict[str, Any] = Field(default_factory=dict)
    agents: list[dict[str, Any]] = Field(default_factory=list)
    plugins: list[dict[str, Any]] = Field(default_factory=list)
    default_model: dict[str, Any] = Field(default_factory=dict)
    summary: dict[str, Any] = Field(default_factory=dict)
    contracts: dict[str, Any] = Field(default_factory=dict)

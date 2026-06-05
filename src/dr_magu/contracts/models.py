from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    """Normalized risk levels consumed by the Brain plan validator."""

    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class PermissionMode(str, Enum):
    """Permission modes used by tools, plans, and future background jobs."""

    allowed = "allowed"
    approval_required = "approval_required"
    blocked = "blocked"
    interactive_only = "interactive_only"


class SchemaField(BaseModel):
    """Small schema description for tool inputs and outputs.

    This intentionally avoids full JSON Schema complexity for v0.9.4 while still
    giving the Orchestrator Brain enough structure to build safe plans.
    """

    name: str
    type: str = "string"
    required: bool = False
    description: str = ""
    default: Any | None = None


class ToolContract(BaseModel):
    """Formal tool contract exposed to the Orchestrator Brain."""

    name: str
    category: str
    description: str
    command: str
    aliases: list[str] = Field(default_factory=list)
    input_schema: list[SchemaField] = Field(default_factory=list)
    output_schema: list[SchemaField] = Field(default_factory=list)
    read_only: bool = True
    risk_level: RiskLevel = RiskLevel.low
    permission_mode: PermissionMode = PermissionMode.allowed
    requires_approval: bool = False
    background_allowed: bool = True
    interactive_only: bool = False


class WorkflowContract(BaseModel):
    """Workflow contract exposed to plugins, agents, and the Brain."""

    name: str
    description: str
    workflow_type: str = "deterministic"
    requires_llm: bool = False
    risk_level: RiskLevel = RiskLevel.low
    permission_mode: PermissionMode = PermissionMode.allowed
    background_allowed: bool = True


class ResourceContract(BaseModel):
    """Unified resource contract used by plugin and brain introspection."""

    resource_type: Literal["tool", "workflow", "agent", "command", "prompt", "schedule", "template"]
    name: str
    provider: str = "core"
    enabled: bool = True
    risk_level: RiskLevel = RiskLevel.low
    permission_mode: PermissionMode = PermissionMode.allowed

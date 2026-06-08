from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any




@dataclass(frozen=True)
class ResolvedModelConfig:
    """Resolved model configuration used by the Brain and agents."""

    provider: str | None = None
    base_url: str | None = None
    model: str | None = None
    temperature: float | None = None
    api_key_env: str | None = None
    api_key_configured: bool = False
    source: str = "unknown"

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "base_url": self.base_url,
            "model": self.model,
            "temperature": self.temperature,
            "api_key_env": self.api_key_env,
            "api_key_configured": self.api_key_configured,
            "source": self.source,
        }

    def model_dump(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        """Pydantic-compatible dump helper used by existing code."""
        return self.to_dict()



@dataclass(frozen=True)
class BrainPlanStep:
    """Single executable step proposed by the AI Orchestrator Brain."""

    type: str
    name: str
    args: dict[str, Any] = field(default_factory=dict)
    description: str = ""


@dataclass(frozen=True)
class BrainPlan:
    """Structured plan produced by the Brain before execution."""

    intent: str
    language: str
    confidence: float
    steps: list[BrainPlanStep]
    requires_approval: bool = False
    explanation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "language": self.language,
            "confidence": self.confidence,
            "requires_approval": self.requires_approval,
            "explanation": self.explanation,
            "steps": [
                {
                    "type": step.type,
                    "name": step.name,
                    "args": step.args,
                    "description": step.description,
                }
                for step in self.steps
            ],
        }


@dataclass(frozen=True)
class BrainResponse:
    """Brain response that can either be an execution plan or a general answer."""

    mode: str
    message: str
    plan: BrainPlan | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "message": self.message,
            "plan": self.plan.to_dict() if self.plan else None,
        }

from __future__ import annotations

from .models import BrainPlan, BrainPlanStep, BrainResponse
from .intent_router import classify_prompt


def _detect_language(text: str) -> str:
    lowered = text.lower()
    spanish_markers = ["analiza", "genera", "repositorio", "contexto", "muéstrame", "muestrame", "ejecuta"]
    return "es" if any(marker in lowered for marker in spanish_markers) else "en"


def plan_prompt(user_prompt: str) -> BrainResponse:
    """Create a deterministic Brain response for v0.10.0."""
    text = user_prompt.strip()
    lowered = text.lower()
    language = _detect_language(text)

    repository_words = ["repo", "repository", "repositorio", "project", "proyecto", "codebase", "codigo", "código"]
    context_words = ["context", "contexto", "documentation", "documentacion", "documentación", "technical", "tecnico", "técnico"]
    scan_words = ["scan", "analyze", "analiza", "analizar", "inspect", "revisa", "review"]

    wants_repository = any(word in lowered for word in repository_words)
    wants_context = any(word in lowered for word in context_words)
    wants_scan = any(word in lowered for word in scan_words)

    if wants_repository and wants_context:
        plan = BrainPlan(
            intent="generate_repository_context",
            language=language,
            confidence=0.92,
            explanation="The prompt asks to analyze the repository and generate technical context.",
            steps=[
                BrainPlanStep(type="command", name="repo.scan", args={}, description="Scan the current workspace repository."),
                BrainPlanStep(type="command", name="context.generate", args={"refresh": True}, description="Generate project context files."),
            ],
        )
        return BrainResponse(mode="workspace_action", message="Repository context generation plan created.", plan=plan)

    if wants_repository and wants_scan:
        plan = BrainPlan(
            intent="scan_repository",
            language=language,
            confidence=0.88,
            explanation="The prompt asks to inspect or analyze the repository.",
            steps=[BrainPlanStep(type="command", name="repo.scan", args={}, description="Scan the current workspace repository.")],
        )
        return BrainResponse(mode="workspace_action", message="Repository scan plan created.", plan=plan)

    if "workflow" in lowered or "flujo" in lowered:
        plan = BrainPlan(
            intent="run_repository_context_workflow",
            language=language,
            confidence=0.85,
            explanation="The prompt refers to running the repository context workflow.",
            steps=[BrainPlanStep(type="workflow", name="repository.context", args={}, description="Run repository context workflow.")],
        )
        return BrainResponse(mode="workspace_action", message="Workflow execution plan created.", plan=plan)

    classification = classify_prompt(user_prompt)
    return BrainResponse(
        mode=classification.intent,
        message=f"Intent Router selected {classification.intent}. Full LLM response/execution for this domain is reserved for a later version.",
        plan=None,
    )

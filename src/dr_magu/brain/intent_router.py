from __future__ import annotations

import re
from .intent_models import (
    INTENT_DOCUMENT_ACTION,
    INTENT_GENERAL_CHAT,
    INTENT_RESEARCH_ACTION,
    INTENT_SCHEDULE_ACTION,
    INTENT_SOFTWARE_ACTION,
    INTENT_WORKSPACE_ACTION,
    IntentClassification,
)


SPANISH_MARKERS = [
    "analiza",
    "genera",
    "repositorio",
    "contexto",
    "documento",
    "busca",
    "investiga",
    "programa",
    "agenda",
    "reporte",
]

KEYWORDS = {
    INTENT_RESEARCH_ACTION: [
        "search",

        "best",
        "top",
        "compare",
        "comparison",
        "recommend",
        "recommendation",
        "systems",
        "platforms",
        "tools",
        "solutions",
        "crm",
        "business",
        "small business",
        "small businesses",
        "mejores",
        "comparar",
        "recomienda",
        "sistemas",
        "plataformas",
        "herramientas",
        "research",
        "find",
        "web",
        "buscar",
        "busca",
        "investiga",
        "investigar",
        "sitios",
        "web",
        "fuentes",
    ],
    INTENT_DOCUMENT_ACTION: [
        "document",
        "report",
        "pdf",
        "markdown",
        "md",
        "summary",
        "summarize",
        "documento",
        "reporte",
        "resumen",
        "pdf",
        "correo",
        "email",
    ],
    INTENT_SCHEDULE_ACTION: [
        "schedule",
        "cron",
        "daily",
        "weekly",
        "background",
        "remind",
        "agenda",
        "programa",
        "diario",
        "semanal",
        "recordatorio",
        "background",
    ],
    INTENT_SOFTWARE_ACTION: [
        "code",
        "website",
        "app",
        "api",
        "test",
        "refactor",
        "architecture",
        "software",
        "sitio",
        "aplicacion",
        "aplicación",
        "codigo",
        "código",
        "arquitectura",
        "pruebas",
    ],
    INTENT_WORKSPACE_ACTION: [
        "repo",
        "repository",
        "workspace",
        "context",
        "scan",
        "workflow",
        "agent",
        "plugin",
        "repositorio",
        "contexto",
        "escanea",
        "analiza",
        "agente",
        "plugin",
    ],
}


def detect_language(prompt: str) -> str:
    """Detect the prompt language using a lightweight deterministic heuristic."""
    lowered = prompt.lower()
    if any(marker in lowered for marker in SPANISH_MARKERS):
        return "es"
    return "en"


def _match_keywords(prompt: str, keywords: list[str]) -> list[str]:
    lowered = prompt.lower()
    matches: list[str] = []
    for keyword in keywords:
        if " " in keyword:
            if keyword in lowered:
                matches.append(keyword)
        elif keyword.isascii() and keyword.replace("_", "").isalnum():
            if re.search(rf"\b{re.escape(keyword)}\b", lowered):
                matches.append(keyword)
        elif keyword in lowered:
            matches.append(keyword)
    return matches


class IntentRouter:
    """Route natural-language prompts to the correct Dr Magu capability domain."""

    def classify(self, prompt: str) -> IntentClassification:
        text = prompt.strip()
        language = detect_language(text)

        ranked: list[tuple[str, list[str]]] = []
        for intent, keywords in KEYWORDS.items():
            matches = _match_keywords(text, keywords)
            if matches:
                ranked.append((intent, matches))

        if not ranked:
            return IntentClassification(
                intent=INTENT_GENERAL_CHAT,
                language=language,
                confidence=0.65,
                reason="No platform action keywords were detected, so the prompt is treated as general chat.",
                suggested_route="general_chat",
                matched_keywords=[],
            )

        # Explicit precedence rules for common mixed prompts.
        ranked_map = {intent: matches for intent, matches in ranked}
        document_matches = ranked_map.get(INTENT_DOCUMENT_ACTION, [])
        software_matches = ranked_map.get(INTENT_SOFTWARE_ACTION, [])

        schedule_matches = ranked_map.get(INTENT_SCHEDULE_ACTION, [])
        if schedule_matches:
            return IntentClassification(
                intent=INTENT_SCHEDULE_ACTION,
                language=language,
                confidence=min(0.95, 0.75 + (0.05 * len(schedule_matches))),
                reason="Scheduling/background execution keywords take precedence.",
                suggested_route=INTENT_SCHEDULE_ACTION,
                matched_keywords=schedule_matches,
                metadata={"candidate_count": len(ranked)},
            )

        if document_matches and any(keyword in document_matches for keyword in ["report", "pdf", "document", "markdown", "md", "reporte", "documento"]):
            return IntentClassification(
                intent=INTENT_DOCUMENT_ACTION,
                language=language,
                confidence=min(0.95, 0.75 + (0.05 * len(document_matches))),
                reason="Document/report generation keywords take precedence over source references.",
                suggested_route=INTENT_DOCUMENT_ACTION,
                matched_keywords=document_matches,
                metadata={"candidate_count": len(ranked)},
            )

        if software_matches and any(keyword in software_matches for keyword in ["code", "architecture", "website", "app", "api", "codigo", "código", "arquitectura", "sitio"]):
            return IntentClassification(
                intent=INTENT_SOFTWARE_ACTION,
                language=language,
                confidence=min(0.95, 0.75 + (0.05 * len(software_matches))),
                reason="Software creation or architecture keywords take precedence.",
                suggested_route=INTENT_SOFTWARE_ACTION,
                matched_keywords=software_matches,
                metadata={"candidate_count": len(ranked)},
            )

        # Prefer more specific platform domains over generic workspace actions.
        priority = [
            INTENT_SCHEDULE_ACTION,
            INTENT_RESEARCH_ACTION,
            INTENT_DOCUMENT_ACTION,
            INTENT_SOFTWARE_ACTION,
            INTENT_WORKSPACE_ACTION,
        ]

        ranked_by_priority = sorted(
            ranked,
            key=lambda item: (priority.index(item[0]), -len(item[1])) if item[0] in priority else (99, -len(item[1])),
        )
        intent, matches = ranked_by_priority[0]

        confidence = min(0.95, 0.70 + (0.05 * len(matches)))
        return IntentClassification(
            intent=intent,
            language=language,
            confidence=confidence,
            reason=f"Matched {len(matches)} keyword(s) for {intent}.",
            suggested_route=intent,
            matched_keywords=matches,
            metadata={"candidate_count": len(ranked)},
        )


def classify_prompt(prompt: str) -> IntentClassification:
    """Convenience function used by CLI, TUI and tests."""
    return IntentRouter().classify(prompt)

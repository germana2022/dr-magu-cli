from __future__ import annotations

import re

from .models import RoutedCommand


_URL_RE = re.compile(r"(https?://[^\s]+|(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(?:/[^\s]*)?)")
_GITHUB_RE = re.compile(r"(?:https?://github\.com/)?([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)")
_QUOTED_RE = re.compile(r'"([^"]+)"|\'([^\']+)\'')


def _quote(value: str) -> str:
    return '"' + value.replace('"', '\\"') + '"'


def _first_quoted(prompt: str) -> str | None:
    match = _QUOTED_RE.search(prompt)
    if not match:
        return None
    return match.group(1) or match.group(2)


def _extract_url(prompt: str) -> str | None:
    match = _URL_RE.search(prompt)
    if not match:
        return None
    value = match.group(1).rstrip(".,)")
    if not value.startswith("http") and "." in value:
        return "https://" + value
    return value


def _extract_repository(prompt: str) -> str | None:
    match = _GITHUB_RE.search(prompt)
    if not match:
        return None
    return match.group(1).rstrip(".,)")


def _clean_query(prompt: str) -> str:
    quoted = _first_quoted(prompt)
    if quoted:
        return quoted.strip()
    cleaned = prompt.strip()
    for prefix in [
        "research", "search", "find", "compare", "look up", "busca", "buscar",
        "investiga", "investigar", "compara", "analiza", "analyze",
    ]:
        if cleaned.lower().startswith(prefix + " "):
            return cleaned[len(prefix):].strip()
    return cleaned


class ConversationalCommandRouter:
    """Route natural-language prompts to explicit Dr Magu commands."""

    def route(self, prompt: str) -> RoutedCommand:
        text = prompt.strip()
        lowered = text.lower()

        if not text:
            return RoutedCommand("empty", None, 0.0, "Prompt is empty.")

        # Website analysis has priority over generic research when a URL/domain is present.
        if any(word in lowered for word in ["website", "site", "webpage", "landing page", "analyze", "analiza", "extract", "screenshot"]):
            url = _extract_url(text)
            if url and "github.com" not in url:
                return RoutedCommand(
                    intent="website_analysis",
                    command=f"website.analyze {_quote(url)}",
                    confidence=0.95,
                    reason="Detected website analysis request with URL/domain.",
                    extracted={"url": url},
                )

        # Repository analysis/read.
        if any(word in lowered for word in ["repository", "repo", "github", "pull request", "issue", "repositorio"]):
            repository = _extract_repository(text)
            if repository:
                return RoutedCommand(
                    intent="repository_analysis",
                    command=f"repository.read {_quote(repository)}",
                    confidence=0.95,
                    reason="Detected repository request with GitHub repository identifier.",
                    extracted={"repository": repository},
                )
            return RoutedCommand(
                intent="workspace_analysis",
                command="repo.scan",
                confidence=0.75,
                reason="Detected repository/workspace request without remote repository identifier.",
                extracted={},
            )

        # Filesystem/workspace file search.
        if any(word in lowered for word in ["find files", "search files", "file search", "filesystem", "archivos", "buscar archivos"]):
            query = _clean_query(text)
            return RoutedCommand(
                intent="filesystem_search",
                command=f"filesystem.search {_quote(query or '.')}",
                confidence=0.9,
                reason="Detected filesystem search request.",
                extracted={"path": query or "."},
            )

        # Software development agents.
        if any(word in lowered for word in ["ticket", "tickets", "user story", "stories"]):
            return RoutedCommand("ticket_generation", "sdlc.agent.run ticket-generator", 0.9, "Detected ticket generation request.")
        if any(word in lowered for word in ["code review", "review code", "review pr", "pr review"]):
            return RoutedCommand("code_review", "sdlc.agent.run code-reviewer", 0.9, "Detected code review request.")
        if any(word in lowered for word in ["test", "tests", "unit test", "generate tests"]):
            return RoutedCommand("test_generation", "sdlc.agent.run test-generator", 0.86, "Detected test generation request.")
        if any(word in lowered for word in ["architecture", "arquitectura", "design options", "technical design"]):
            return RoutedCommand("architecture_planning", "sdlc.agent.run architecture-planner", 0.84, "Detected architecture planning request.")

        # Web/research intent.
        if any(word in lowered for word in [
            "research", "search", "find", "top", "best", "compare", "comparison", "platforms",
            "systems", "tools", "solutions", "crm", "market", "competitors", "busca", "investiga",
            "mejores", "comparar"
        ]):
            query = _clean_query(text)
            command_name = "research.search"
            return RoutedCommand(
                intent="research",
                command=f"{command_name} {_quote(query)}",
                confidence=0.9,
                reason="Detected web/research request.",
                extracted={"query": query},
            )

        # Website build remains a software workflow, not website analysis.
        if any(word in lowered for word in ["build website", "generate website", "create website", "crear sitio", "generar sitio"]):
            return RoutedCommand(
                intent="website_build",
                command=f"website.build {_quote(text)}",
                confidence=0.88,
                reason="Detected website generation request.",
                extracted={"prompt": text},
            )

        return RoutedCommand(
            intent="general_chat",
            command=None,
            confidence=0.55,
            reason="No actionable command intent detected; use LLM chat.",
            extracted={},
        )


def route_prompt(prompt: str) -> RoutedCommand:
    return ConversationalCommandRouter().route(prompt)

from __future__ import annotations

from .models import HealingPolicy


def default_policy_for(command: str) -> HealingPolicy:
    """Return a conservative healing policy for a command."""
    if command.startswith("web.search") or command.startswith("research.search"):
        return HealingPolicy(max_retries=1, fallback_command="research.search", escalate_on_failure=True)
    if command.startswith("website.analyze"):
        return HealingPolicy(max_retries=1, fallback_command="research.search", escalate_on_failure=True)
    if command.startswith("repository.read"):
        return HealingPolicy(max_retries=1, fallback_command="repo.scan", escalate_on_failure=True)
    if command.startswith("factory.run"):
        return HealingPolicy(max_retries=1, fallback_command="factory.plan", escalate_on_failure=True)
    return HealingPolicy(max_retries=1, fallback_command=None, escalate_on_failure=True)

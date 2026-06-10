from __future__ import annotations

from pathlib import Path

from dr_magu.commands.context import CommandContext
from dr_magu.commands.processor import CommandProcessor
from dr_magu.commands.registry import registry
from dr_magu.config import load_config
from dr_magu.result import ToolResult

from .models import HealingAttempt, HealingPolicy, HealingReport
from .policies import default_policy_for
from .store import HealingStore


class SelfHealingRuntime:
    """Retry, fallback and escalation boundary for commands/workflows."""

    def __init__(self, workspace_path: str | Path):
        self.workspace_path = str(Path(workspace_path).resolve())
        self.processor = CommandProcessor(registry)
        self.store = HealingStore(self.workspace_path)

    def plan(self, command: str, fallback_command: str | None = None, max_retries: int | None = None) -> ToolResult:
        policy = default_policy_for(command)
        if fallback_command is not None:
            policy = HealingPolicy(
                max_retries=policy.max_retries if max_retries is None else max_retries,
                fallback_command=fallback_command,
                escalate_on_failure=policy.escalate_on_failure,
                approval_required=policy.approval_required,
            )
        elif max_retries is not None:
            policy = HealingPolicy(
                max_retries=max_retries,
                fallback_command=policy.fallback_command,
                escalate_on_failure=policy.escalate_on_failure,
                approval_required=policy.approval_required,
            )
        return ToolResult(success=True, tool="healing.plan", data={"command": command, "policy": policy.to_dict()})

    def run(
        self,
        command: str,
        fallback_command: str | None = None,
        max_retries: int | None = None,
        escalate_on_failure: bool | None = None,
    ) -> ToolResult:
        policy = default_policy_for(command)
        policy = HealingPolicy(
            max_retries=policy.max_retries if max_retries is None else max_retries,
            fallback_command=policy.fallback_command if fallback_command is None else fallback_command,
            escalate_on_failure=policy.escalate_on_failure if escalate_on_failure is None else escalate_on_failure,
            approval_required=policy.approval_required,
        )

        context = CommandContext(workspace_path=self.workspace_path, output_format="human", config=load_config())
        attempts: list[HealingAttempt] = []
        fallback_used = False

        # Initial attempt plus retries.
        total_primary_attempts = max(1, policy.max_retries + 1)
        last_result: ToolResult | None = None
        for index in range(1, total_primary_attempts + 1):
            result = self.processor.execute_line(command, context)
            last_result = result
            attempts.append(HealingAttempt(
                index=index,
                command=command,
                status="completed" if result.success else "failed",
                tool=result.tool,
                errors=result.errors,
            ))
            if result.success:
                report = HealingReport(command=command, success=True, status="completed", attempts=attempts, policy=policy)
                artifact = self.store.write_report(report.to_dict())
                return ToolResult(success=True, tool="healing.run", data={"report": report.to_dict(), "artifact": artifact})

        # Fallback once if configured.
        if policy.fallback_command:
            fallback_used = True
            fallback = self._build_fallback_command(policy.fallback_command, command)
            result = self.processor.execute_line(fallback, context)
            last_result = result
            attempts.append(HealingAttempt(
                index=len(attempts) + 1,
                command=fallback,
                status="completed" if result.success else "failed",
                tool=result.tool,
                errors=result.errors,
            ))
            if result.success:
                report = HealingReport(
                    command=command,
                    success=True,
                    status="recovered",
                    attempts=attempts,
                    policy=policy,
                    fallback_used=True,
                )
                artifact = self.store.write_report(report.to_dict())
                return ToolResult(success=True, tool="healing.run", data={"report": report.to_dict(), "artifact": artifact})

        escalated = bool(policy.escalate_on_failure)
        status = "escalated" if escalated else "failed"
        report = HealingReport(
            command=command,
            success=False,
            status=status,
            attempts=attempts,
            policy=policy,
            escalated=escalated,
            fallback_used=fallback_used,
        )
        artifact = self.store.write_report(report.to_dict())
        errors = list(last_result.errors if last_result else ["Command failed."])
        if escalated:
            errors.append("Escalated for human review.")
        return ToolResult(success=False, tool="healing.run", data={"report": report.to_dict(), "artifact": artifact}, errors=errors)

    def _build_fallback_command(self, fallback_command: str, original_command: str) -> str:
        """Build a fallback command while preserving useful context."""
        if fallback_command in {"research.search", "web.search"}:
            return f'{fallback_command} "Fallback for: {original_command}"'
        if fallback_command in {"factory.plan"}:
            return f'{fallback_command} "Fallback for: {original_command}"'
        return fallback_command

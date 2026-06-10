# Dr Magu CLI v1.8.0

## Self-Healing Workflows

v1.8.0 adds retry, fallback and escalation around command execution.

### Added

- SelfHealingRuntime
- HealingPolicy
- HealingReport
- `healing.plan`
- `healing.run`
- `dr-magu healing-plan`
- `dr-magu healing-run`
- Healing report artifacts

### Flow

Detect failure → Retry → Fallback → Escalate → Store report\n
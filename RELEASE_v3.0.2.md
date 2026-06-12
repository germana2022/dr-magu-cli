# dr-magu-cli v3.0.2 — Agent Collaboration & Artifact Pipeline

## Summary

This patch turns multi-agent team execution into a collaborative artifact pipeline.
Each team agent now produces a persisted Markdown and JSON artifact, and each
subsequent agent receives prior artifact summaries and paths in its prompt.

## Changes

- Added shared team artifact store under `.dr-magu/teams/artifacts/<team-run-id>/`.
- Added run context artifact for every team run.
- Added per-agent Markdown and JSON artifacts.
- Added artifact manifest persisted with the team run record.
- Added prior artifact context to downstream agent prompts.
- Added role-specific directives for researcher, architect, reviewer and reporter.
- Added `team.artifacts <run_id>` command.
- Updated team run summaries to include artifact counts and artifact directories.

## Expected Pipeline

```text
Researcher -> repository-findings.md/json
Architect  -> architecture.md/json
Reviewer   -> review.md/json
Reporter   -> final-report.md/json
```

## Acceptance Criteria

- `team.run repo-analysis "Analyze this repository"` creates an artifact directory.
- Every executed agent writes a Markdown and JSON artifact.
- The team run record includes `artifact_manifest`.
- Downstream agent prompts include prior artifact summaries.
- `team.artifacts <team-run-id>` lists persisted artifacts.

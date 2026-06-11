# dr-magu-cli v2.5.0 — Workflow Orchestration Engine

## Summary

v2.5.0 promotes workflow execution into an operational orchestration layer. The Workflow Engine now supports workflow definition discovery, planning, stateful execution, persisted context, observable history, resume/retry/cancel operations, and workspace-defined YAML/JSON workflows.

## Highlights

- Added workflow definition catalog with built-in and workspace workflows.
- Added workspace workflow loading from `.dr-magu/workflows/*.json|*.yaml|*.yml`.
- Added plan rendering before execution.
- Added richer step metadata: enabled, requires_approval, continue_on_error, timeout_seconds, output_key.
- Added persisted workflow definitions per run.
- Added improved resume support against the existing run state.
- Added command aliases for `workflow.engine.list`, `workflow.engine.show`, `workflow.engine.plan`, and `workflow.engine.run`.
- Fixed CLI import shadowing so root `workflow-engine-*` commands use the Workflow Engine runner.

## Operational Commands

```bash
dr-magu workflow-engine-list
dr-magu workflow-engine-show research-brief --topic "AI news"
dr-magu workflow-engine-plan research-brief --topic "AI news"
dr-magu workflow-engine-run research-brief --topic "AI news"
dr-magu workflow-engine-status <run_id>
dr-magu workflow-engine-history <run_id>
dr-magu workflow-runtime-resume <run_id>
dr-magu workflow-runtime-cancel <run_id>
dr-magu workflow-runtime-export <run_id> --format md
```

Command registry equivalents:

```text
workflow.engine.list
workflow.engine.show <workflow_id>
workflow.engine.plan <workflow_id>
workflow.engine.run <workflow_id> --topic "..."
workflow.engine.status <run_id>
workflow.engine.history <run_id>
workflow.runtime.resume <run_id>
workflow.runtime.cancel <run_id>
workflow.runtime.export_history <run_id>
```

## Built-in Workflow Definitions

- `website-builder`
- `research-brief`
- `repository-context`

## Validation

- CLI version returns `dr-magu-cli v2.5.0`.
- Test suite validates workflow planning, execution, persistence, history, and command routing.

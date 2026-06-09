# Dr Magu CLI v1.1.0

## Execution Runtime Layer

This release moves Dr Magu from an orchestration platform toward an execution-capable AI Agent Operating System.

### Added

- Execution Planner
- Execution Executor
- Execution Permissions
- Filesystem Runtime
- Terminal Runtime
- Git Runtime
- Execution logs and persisted execution history
- HITL approval flow for sensitive actions

### Intent

v1.1.0 enables this loop:

```text
Observe
  -> Plan
  -> Ask Permission
  -> Execute
  -> Validate
  -> Persist Result
```

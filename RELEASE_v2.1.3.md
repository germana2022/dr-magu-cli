# dr-magu-cli v2.1.3 — MCP Runtime Process Persistence Fix

## Goal

Make MCP lifecycle management operational after a successful `mcp.start` by keeping stdio MCP processes alive during the active runtime session and persisting process diagnostics.

## Changes

- Added in-session MCP process tracking for started stdio servers.
- Persisted process metadata in `.dr-magu/mcp_runtime/processes.json`.
- Added per-server stdout/stderr runtime logs.
- Improved `mcp.status` with runtime state and failure diagnostics.
- Added startup verification to avoid reporting `started` when the process exits immediately.
- Improved `mcp.stop` cleanup for tracked and persisted processes.

## Expected Behavior

```text
mcp.start playwright
→ status: started
→ pid: <process id>

mcp.status playwright
→ running: True
→ healthy: True when enabled, configured, command is available, and no required env is missing
```

## Notes

For stdio-based MCP servers, the process must remain attached to the active Dr. Magu runtime session. This release keeps the process handle alive in memory and persists metadata/log paths for observability.

# dr-magu-cli v2.1.1 — Operational Command Routing Fix

## Summary

v2.1.1 fixes the operational command routing gap discovered in v2.1.0. Operational commands are now resolved before any LLM fallback, so enable/disable/start/stop/status/health commands are executed by the runtime instead of being treated as general chat.

## Key Changes

- Added command-first normalization for operational domains.
- Added support for both dot syntax and space syntax:
  - `mcp.enable playwright`
  - `mcp enable playwright`
  - `agent.enable repository-analyzer`
  - `agent enable repository-analyzer`
  - `schedule.enable task-id`
  - `schedule enable task-id`
- Registered MCP runtime commands in the internal command registry:
  - `mcp.enable`
  - `mcp.disable`
  - `mcp.start`
  - `mcp.stop`
  - `mcp.restart`
  - `mcp.health`
  - `mcp.status`
  - `mcp.discover`
  - `mcp.boot`
- MCP enable/disable now reaches `MCPRuntimeManager` from the TUI command processor.
- MCP state changes initialize and persist `.dr-magu/config/mcp_servers.json` through the registry save path.
- Added tests to prevent operational commands from falling back to `brain.ask`.

## Validation

- CLI version returns `dr-magu-cli v2.1.1`.
- MCP command routing validates dot syntax and space syntax.
- Agent and schedule enable/disable routing remains operational.
- MCP enable persists a configuration file under the workspace.

# Release v2.1.0 - Operational MCP Runtime

## Summary

v2.1.0 turns the MCP layer into an operational runtime. The release adds server lifecycle management, health checks, auto-discovery, enable/disable support, provider selection for research, and fallback provider chains.

## Goals

- Start MCP servers from the CLI.
- Check MCP runtime health.
- Discover and persist MCP server configuration.
- Enable or disable MCP servers per workspace.
- Manage MCP lifecycle: start, stop, restart and boot.
- Support real Brave Search, Playwright-style page extraction, GitHub repository metadata and Filesystem access.
- Select research providers explicitly.
- Fall back to compatible providers when the requested provider fails.

## New CLI Commands

```bash
dr-magu mcp-list
dr-magu mcp-discover
dr-magu mcp-status brave-search
dr-magu mcp-health brave-search
dr-magu mcp-enable brave-search
dr-magu mcp-disable brave-search
dr-magu mcp-start brave-search
dr-magu mcp-stop brave-search
dr-magu mcp-restart brave-search
dr-magu mcp-boot
```

## Research Provider Selection

```bash
dr-magu research "LangGraph MCP examples" --provider auto
dr-magu research "LangGraph MCP examples" --provider brave-search
dr-magu research "https://example.com" --provider playwright
dr-magu research "owner/repository" --provider github
dr-magu research "." --provider filesystem
dr-magu research "offline topic" --provider deterministic
```

## Runtime Configuration

Workspace configuration is stored at:

```text
.dr-magu/config/mcp_servers.json
```

Runtime process state is stored at:

```text
.dr-magu/mcp_runtime/processes.json
```

## Environment Variables

```bash
BRAVE_API_KEY=
GITHUB_TOKEN=
RESEARCH_PROVIDER=auto
```

Each MCP server can also be configured with `MCP_<SERVER>_ENABLED`, `MCP_<SERVER>_AUTO_START`, `MCP_<SERVER>_COMMAND` and `MCP_<SERVER>_ARGS` variables.

## Acceptance Criteria

- `dr-magu version` returns `v2.1.0`.
- `dr-magu mcp-discover` creates workspace MCP configuration.
- `dr-magu mcp-list` shows configured servers with lifecycle status.
- `dr-magu mcp-enable <server>` and `dr-magu mcp-disable <server>` persist configuration changes.
- `dr-magu mcp-health <server>` reports enabled, configured, running and missing environment variables.
- `dr-magu mcp-start <server>` starts a configured stdio MCP process when requirements are satisfied.
- `dr-magu research --provider <provider>` records provider, provider chain and fallback usage.
- Fallbacks are applied when the requested provider is unavailable or fails.

## Notes

Real MCP process lifecycle is now available. Tool-call integration is exposed through operational adapters for Brave Search, GitHub, Filesystem and page extraction while preserving the MCP client boundary for future stdio protocol expansion.

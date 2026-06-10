# dr-magu-cli v2.1.2 — Windows MCP Command Resolution Fix

## Summary

v2.1.2 fixes MCP server startup on Windows when MCP server commands are configured with portable executable names such as `npx`. The MCP Runtime now resolves commands through the active process PATH before spawning MCP servers and automatically checks common Windows command shims such as `.cmd`, `.exe`, and `.bat`.

## Why this release exists

In v2.1.1, operational command routing was fixed and commands such as `mcp.enable playwright`, `mcp.status playwright`, and `mcp.start playwright` correctly reached the MCP Runtime. However, on Windows the runtime could fail to start Playwright MCP with:

```text
Command not found: npx
```

This happened even when `npx` or `npx.cmd` worked from the user shell, because the runtime passed the portable command directly to `subprocess.Popen` without resolving the concrete executable path first.

## Changes

- Added cross-platform MCP command resolution before process startup.
- Resolves configured commands with `shutil.which()`.
- On Windows, portable commands such as `npx` are also resolved as:
  - `npx.cmd`
  - `npx.exe`
  - `npx.bat`
- `mcp.start` now launches the resolved executable path instead of the raw command string.
- `mcp.status` and `mcp.health` now expose:
  - `resolved_command`
  - `command_available`
- Startup state now records both:
  - the resolved command used to launch the process
  - the original configured command
- Missing commands now return a clearer error:

```text
Command not found in PATH: <command>
```

## Expected Windows behavior

With Playwright configured as:

```json
{
  "id": "playwright",
  "command": "npx",
  "args": ["-y", "@playwright/mcp"]
}
```

The runtime should resolve it to something like:

```text
C:\\Program Files\\nodejs\\npx.cmd
```

Then:

```bash
mcp.start playwright
```

should use the resolved `.cmd` shim instead of failing on the portable `npx` command.

## Validation

- Full test suite: `256 passed`
- CLI version: `dr-magu-cli v2.1.2`
- Added regression coverage for Windows `.cmd` shim resolution.
- Added regression coverage for clear missing-command startup errors.

## Upgrade notes

No manual configuration change is required. Existing MCP configs can continue using portable commands such as:

```json
"command": "npx"
```

The runtime handles Windows-specific executable resolution automatically.

# Dr Magu CLI v1.2.0

## MCP Research Runtime

v1.2.0 adds the MCP runtime boundary and uses it as the default research provider.

### Added

- MCPServerRegistry
- MCPClient boundary
- MCPToolCall / MCPToolResult
- MCPResearchProvider
- `mcp.servers`
- `mcp.call`
- `dr-magu mcp-servers`

### Notes

The version includes deterministic simulation mode for offline development and tests. Real MCP transport can be added later behind the same runtime boundary.

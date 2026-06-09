# Dr Magu CLI v1.3.0

## Real MCP Integrations

v1.3.0 adds integration contracts for the first real MCP servers:

- Playwright MCP
- Brave Search MCP
- GitHub MCP
- Filesystem MCP

### Added

- MCPIntegrationRuntime
- `website.analyze`
- `repository.read`
- `filesystem.search`
- `web.search`
- `dr-magu website-analyze`
- `dr-magu repository-read`
- MCP server configuration template

### Notes

The runtime still supports deterministic simulation for offline development. Real MCP server processes can be configured through `.dr-magu/config/mcp_servers.json` or environment variables.

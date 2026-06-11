# dr-magu-cli v2.2.0 — Real MCP Provider Integration

## Summary

This release completes the transition from simulated MCP-backed research to real provider execution. The MCP Runtime introduced and stabilized in v2.1.x is now connected to the research and integration layer through real adapters for Playwright, Brave Search, GitHub, and Filesystem.

## Main Changes

- Research now uses real provider adapters by default.
- `mcp-simulated` is no longer used unless simulation is explicitly requested.
- `research ... --provider playwright` performs real web discovery for search queries and real page extraction for HTTP(S) URLs.
- `research ... --provider brave-search` uses Brave Search API and requires `BRAVE_API_KEY`.
- `research ... --provider github` retrieves repository metadata through the GitHub REST API and supports optional `GITHUB_TOKEN`.
- `research ... --provider filesystem` performs workspace-safe local file scans.
- Explicit provider selection is strict and does not silently fall back to a different provider.
- `--provider auto` remains the recommended mode when fallback behavior is desired.
- `--simulate` remains available for deterministic offline demos and test fixtures.

## Expected Behavior

```bash
research AI news --provider playwright
```

Expected output characteristics:

```text
provider: playwright
fallback_used: False
source_count: <real extracted count>
```

The output should no longer show:

```text
provider: mcp-simulated
```

unless `--simulate` is explicitly used.

## Validation

```text
261 tests passed
CLI version: dr-magu-cli v2.2.0
```

# Dr Magu CLI v1.1.3

## OpenCode Provider Compatibility Fix

v1.1.3 improves the LLM Runtime HTTP client compatibility for OpenAI-compatible providers.

### Added

- Stable Dr Magu User-Agent for LLM requests.
- Optional `LLM_USER_AGENT`.
- Optional `LLM_EXTRA_HEADERS`.
- Tests validating request headers.

### Why

OpenCode's public endpoint can reject Python urllib's default client signature through Cloudflare Error 1010. This release makes the client identify as `dr-magu-cli/1.1.3`.

# Dr Magu CLI v1.1.4

## LLM Response Sanitization

v1.1.4 separates clean user-facing chat output from provider internals.

### Added

- LLM response sanitizer
- Clean `llm.chat` response payloads
- Sanitized debug payloads
- `dr-magu llm-chat --debug`
- Regression tests for hidden provider internals

### Why

Provider responses can include raw payloads, usage, system fingerprints and reasoning metadata. These are useful for diagnostics but should not be displayed in normal chat output.

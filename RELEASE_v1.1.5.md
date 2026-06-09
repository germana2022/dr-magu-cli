# Dr Magu CLI v1.1.5

## Chat UX Layer

v1.1.5 makes Dr Magu feel more like a conversational assistant.

### Added

- Chat UX renderer
- Clean default output for `brain.ask`, `brain.chat`, and `llm.chat`
- `--debug` support for Brain chat commands
- Cleaner TUI chat rendering
- Less verbose greeting behavior in the system prompt

### Result

`/ask hi` now shows only the assistant message instead of internal routing and model metadata.

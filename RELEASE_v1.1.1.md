# Dr Magu CLI v1.1.1

## Conversational Brain Foundation

v1.1.1 connects natural-language prompts to the Brain routing layer without breaking the TUI command.

### Added

- ConversationalBrain
- `brain.ask`
- `brain.chat`
- `ask` and `chat` aliases
- `dr-magu brain-ask`
- `dr-magu brain-chat`
- Safe TUI natural-language fallback
- Improved research intent detection
- Default model context in conversational responses

### Important

The default model is resolved and exposed, but live LLM chat calls are not executed yet. That belongs to the next LLM Runtime implementation.

# Changelog

## v0.3.0

### Added

- Terminal UI foundation with `dr-magu tui`.
- OpenCode-style layout using Textual and Rich.
- Main console panel.
- Right context sidebar.
- Bottom prompt input.
- Slash commands: `/help`, `/commands`, `/status`, `/run`, `/clear`, `/exit`.
- Direct internal command execution from the TUI.
- TUI configuration in `config/orchestration.yaml`.

### Changed

- Version updated to `0.3.0`.
- README updated for the TUI-first phase.
- Project description updated to include the Terminal UI foundation.

## v0.2.0

### Added

- Command Processor.
- Command Registry.
- Command Definition metadata.
- Command Context.
- OpenCode-style internal command execution with `dr-magu run "..."`.
- Registered command listing with `dr-magu commands list`.
- Result Renderer abstraction.
- Unit tests for command parsing and processor execution.

### Changed

- CLI commands now route through the Command Processor.
- Version updated to `0.2.0`.
- Orchestration configuration updated in English.

## v0.1.0

### Added

- Initial Tool CLI foundation.
- File tools: `files list`, `files read`.
- Search tool: `search code`.
- Git tools: `git status`, `git diff`.
- Shell tool: `shell run`.
- Basic blocked shell command patterns.
- JSON output support.

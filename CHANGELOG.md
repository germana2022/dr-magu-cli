## v0.9.9 - Pre-v0.10 Stabilization

- Added architecture health checks.
- Added configuration and plugin readiness validation.
- Added release cleanliness validation.
- Added `dr-magu health` command.
- Prepared the runtime for v0.10.0 AI Orchestrator Brain.

## v0.9.7 - Plugin Resource Contracts

- Added formal PluginResources contract.
- Added resource validation.
- Added prompts, schedules and templates resource categories.
- Prepared plugin metadata for AI Brain integration.

## v0.9.5 - TUI Modularization

- Added a dedicated `dr_magu.tui` package.
- Added reusable TUI models, command helpers, renderers, screen helpers and widget helpers.
- Preserved the current `dr_magu.tui_app` entry point for backward compatibility.
- Prepared the TUI architecture for the upcoming AI Orchestrator Brain.
- Added tests for the new TUI modules.

# Changelog

## v0.9.4

### Added

- Runtime Contracts Foundation.
- Formal `ToolContract` model with schemas, risk levels, permission modes, approval flags, and background execution metadata.
- `BrainPlan`, `PlanStep`, and `PlanValidator` for safe Brain-generated execution plans.
- CLI commands `dr-magu contracts tools` and `dr-magu plan validate`.
- Internal commands `contracts.tools` and `plan.validate`.
- Contract metadata in runtime and Brain context snapshots.
- Permission policy metadata for blocked, approval-required, and background-safe operations.
- Tests for tool contracts and plan validation.

### Changed

- Version updated to `0.9.4`.
- Tool Registry now exposes formal Brain-facing contracts instead of minimal command-derived metadata.


## v0.9.3

### Added

- Control Center dashboard with `dr-magu control center`.
- Plugin impact details with `dr-magu control plugin <plugin-id>`.
- Internal commands `control.center` and `control.plugin`.
- TUI commands `/control`, `cc`, and `/control-plugin <plugin-id>`.
- Control Center sections for plugins, agents, workflows, tools, permissions, schedules, and Brain readiness.
- Read-only scheduler placeholder for future cron/background task management.
- Tests for Control Center service, command processor routing, and CLI output.

### Changed

- Version updated to `0.9.3`.
- README updated with Control Center usage and current architecture.

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

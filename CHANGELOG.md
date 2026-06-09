## v0.22.0 - Platform Stabilization

- Added Platform Stabilization package.
- Added v1.0.0 readiness checks.
- Added `platform.stabilize` command boundary.
- Added `dr-magu stabilize` CLI command.
- Added platform-stabilization plugin metadata.
- Added stabilization report rendering in text and JSON.
- Added stabilization report persistence under `.dr-magu/stabilization/`.

## v0.20.0 - Workflow Runtime & History

- Added WorkflowRuntime operations.
- Added workflow inspect, cancel, retry, resume and export history.
- Added runtime command registry entries and CLI commands.
- Updated Workflow Engine plugin metadata.
- Added JSON and Markdown history export support.

## v0.19.0 - Workflow Engine Foundation

- Added Workflow Engine package.
- Added WorkflowDefinition, WorkflowStep, WorkflowRunState and WorkflowHistoryEvent models.
- Added WorkflowContext.
- Added WorkflowRunStore persistence under `.dr-magu/workflow-runs/`.
- Added WorkflowRunner for deterministic stateful workflow execution.
- Added workflow engine commands and CLI entries.
- Added Workflow Engine plugin metadata.

## v0.18.0 - Website Builder Workflow

- Added Website Builder plugin metadata.
- Added deterministic website-builder workflow foundation.
- Added `website.build` command boundary.
- Added `dr-magu website-build`.
- Integrated research output, SDLC agents, HITL approval request and report generation.
- Added architecture options including custom user-suggested option.
- Persisted Website Builder artifacts under `.dr-magu/website-builder/`.
- Prepared future code generation after HITL option selection.

## v0.17.0 - Software Development Platform

- Added Software Development plugin metadata.
- Added deterministic SDLC agent foundations.
- Added repository analyzer, architecture planner, ticket generator, code reviewer, test generator, documentation writer and release notes generator.
- Added safe read-only Git tools.
- Added approval-aware shell runner.
- Added workspace-scoped filesystem tools.
- Added CLI and command registry entries for SDLC/Git/Shell/Filesystem operations.

## v0.16.0 - Scheduler Runtime Foundation

- Added formal scheduled task model.
- Added persisted scheduler runtime operations.
- Added schedule create/list/enable/disable/delete/run commands.
- Added common cron next-run estimation.
- Added run-once command execution through the existing Command Processor.
- Prepared scheduler runtime for future daemon/background workers.

## v0.12.0 - Web Research Plugin Foundation

- Added Research plugin metadata.
- Added `web-researcher` agent definition.
- Added deterministic research provider.
- Added `research.search` command boundary.
- Added `dr-magu research`.
- Added persisted research output at `.dr-magu/research/latest-research.json`.
- Prepared future live web search/fetch/summarization connectors.

## v0.11.0 - Intent Router

- Added deterministic Intent Router.
- Added route categories for general chat, workspace actions, research, documents, software and schedules.
- Added multilingual keyword routing for English and Spanish prompts.
- Added `dr-magu brain-route`.
- Added `brain.route` internal command.
- Prepared the Brain for future domain-specific agents and plugins.

## v0.10.0 - AI Orchestrator Brain

- Added Brain Context Loader.
- Added deterministic multilingual Brain Planner.
- Added BrainPlan and BrainPlanStep schema.
- Added Plan Validator.
- Added safe Plan Executor through existing runtime boundaries.
- Added `dr-magu ask`, `dr-magu brain-plan` and `dr-magu brain-execute`.
- Prepared the platform for future LLM-backed planning while keeping the LLM as planner only.

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

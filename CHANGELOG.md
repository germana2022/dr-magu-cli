
## v2.8.0 — Multi-Agent Orchestration

- Added workspace-managed multi-agent teams.
- Added team.create, team.add, team.remove, team.list, team.show, team.run, team.status, team.history, team.stop and team.delete.
- Added team persistence under `.dr-magu/teams/`.
- Added sequential team execution over the Agent Runtime.
- Added team run history and runtime state.
- Added command-first routing for natural `team ...` syntax.


## v2.7.0 — Agent Skills Framework

- Added built-in reusable agent skills.
- Added skill.list, skill.show, skill.attach, skill.detach, and agent.skills.
- Added persisted agent skill bindings under .dr-magu/skills/agent_skills.yaml.
- Added role-based default skills for created agents.
- Enriched agent status/context with skill aggregates.


## v2.6.0 — Agent Runtime

- Added operational Agent Runtime state and execution history.
- Added direct `agent.create`, `agent.status`, `agent.stop`, `agent.history`, and `agent.context` commands.
- Extended `agent.run` with prompt/topic and dry-run support.
- Integrated agents with the v2.5 Workflow Orchestration Engine while preserving existing YAML lifecycle commands.

## v2.3.3 — Research Tool Mapping Fix

- Mapped Playwright Research to concrete MCP tools (`browser_navigate` and `browser_snapshot`).
- Updated Research debug output to show the actual MCP tool invoked instead of the synthetic adapter name.
- Added Playwright MCP tool sequence metadata to research results.
- Updated CLI/package version to 2.3.3.

## v2.5.0 — Workflow Orchestration Engine

- Added operational Workflow Engine definition catalog, planning, and persisted orchestration runs.
- Added workspace YAML/JSON workflow definitions under `.dr-magu/workflows`.
- Added richer step metadata and improved resume support.
- Fixed CLI command import shadowing for Workflow Engine commands.


## v2.3.3 — MCP Validation Toolkit and Session Architecture Fix

- Added `mcp.handshake`, `mcp.tools`, `mcp.test`, and `mcp.diagnose` commands.
- Added CLI commands `mcp-handshake`, `mcp-tools`, `mcp-test`, and `mcp-diagnose`.
- Added direct Playwright MCP smoke testing, for example `mcp.test playwright https://www.google.com`.
- Fixed stdio MCP framing by sending newline-delimited JSON-RPC messages instead of LSP-style `Content-Length` requests.
- Kept backward-compatible response parsing for `Content-Length` framed MCP responses.
- Fixed Research MCP session architecture to use client-owned stdio sessions for Playwright provider execution.
- Added command parser support for `mcp test`, `mcp tools`, `mcp diagnose`, and `mcp handshake` space syntax.
- Updated CLI/package version to 2.3.3.


## v2.3.0 — Real MCP Client Connectivity

- Added real stdio MCP JSON-RPC client connectivity.
- Added MCP initialize handshake, tool discovery, and tool invocation.
- Integrated Research with Playwright MCP stdio sessions.
- Added debug metadata for client connection, handshake, tools, and responses.
- Updated CLI/package version to 2.3.0.


## v2.2.1 — MCP Research Diagnostics

- Added `research --debug` diagnostics for Research → MCP provider execution.
- Added `.dr-magu/research/debug/latest-debug.json`.
- Added fallback reason, MCP client attempt metadata, and provider-chain debug events.
- Added `mcp.debug` / `dr-magu mcp-debug` for runtime diagnostics and log tails.

## v2.2.0 — Real MCP Provider Integration

- Changed research to use real provider adapters by default instead of deterministic MCP simulation.
- Added strict explicit provider behavior: explicit providers no longer silently fall back to other providers.
- Kept deterministic MCP simulation available only through `--simulate` or explicit simulation wiring for offline tests.
- Added real Playwright provider web discovery for query-based research and direct page extraction for HTTP(S) URLs.
- Added real Brave Search adapter through `BRAVE_API_KEY`.
- Added real GitHub repository metadata retrieval through the GitHub REST API, with optional `GITHUB_TOKEN`.
- Added real Filesystem research adapter for workspace-safe scans and reads.
- Updated research output provider names to the selected real provider id, for example `playwright`, `brave-search`, `github`, or `filesystem`.
- Updated MCP integration tests to validate real adapter contracts without requiring live internet access.
- Updated CLI and package version to `2.2.0`.

## v2.1.3 — MCP Runtime Process Persistence Fix

- Keeps started stdio MCP server processes alive inside the active Dr. Magu runtime session.
- Persists MCP process metadata under `.dr-magu/mcp_runtime/processes.json`.
- Adds stdout/stderr log files per MCP server under `.dr-magu/mcp_runtime/logs`.
- Enhances `mcp.status` with `state_path`, log paths, last exit code, and stderr tail diagnostics.
- Prevents false-positive startup success when an MCP process exits during startup.
- Improves `mcp.stop` to terminate tracked in-session processes and clean persisted state.

## v2.1.2 — Windows MCP Command Resolution Fix

- Fixed MCP server startup on Windows when a server command is configured as `npx`.
- Added cross-platform command resolution with Windows shim support for `.cmd`, `.exe`, and `.bat`.
- `mcp.start` now spawns the resolved executable path and returns `resolved_command`.
- `mcp.status` and `mcp.health` now include `resolved_command` and `command_available`.
- Missing runtime commands now return `Command not found in PATH: <command>`.
- Added regression tests for Windows `npx.cmd` resolution and missing-command startup errors.

## v2.1.0 - Operational MCP Runtime

- Added operational MCP lifecycle management for configured servers.
- Added `MCPRuntimeManager` with list, discover, status, health, start, stop, restart, enable, disable and boot operations.
- Extended MCP server configuration with `auto_start`, `health_check`, `required_env`, `fallbacks` and startup timeout metadata.
- Added workspace persistence for `.dr-magu/config/mcp_servers.json` and `.dr-magu/mcp_runtime/processes.json`.
- Added CLI commands: `mcp-list`, `mcp-discover`, `mcp-status`, `mcp-health`, `mcp-start`, `mcp-stop`, `mcp-restart`, `mcp-enable`, `mcp-disable` and `mcp-boot`.
- Added research provider selection with `dr-magu research --provider auto|brave-search|playwright|github|filesystem|deterministic`.
- Added fallback provider chain metadata to research outputs.
- Added operational adapters for real Brave Search, Playwright-style web-page extraction, GitHub repository metadata and workspace filesystem access.
- Updated CLI and package version to `2.1.0`.
- Added release notes and tests for the Operational MCP Runtime.

## v2.0.0 - AI Operating System

- Added `ai_os` package.
- Added `AIOperatingSystem` control layer.
- Added OS capability registry.
- Added `os.status`, `os.capabilities`, `os.dispatch`, and `os.boot` commands.
- Added `dr-magu os-status`, `dr-magu os-capabilities`, `dr-magu os-dispatch`, and `dr-magu os-boot`.
- Added `ai-operating-system` plugin metadata.
- Added AI OS tests.
- Consolidated Brain, Router, LLM, MCP, Agents, Workflows, Scheduler, Execution, Factory, Healing, Plugins and Permissions into one top-level platform view.

## v1.8.0 - Self-Healing Workflows

- Added `self_healing` package.
- Added `HealingPolicy`, `HealingAttempt`, and `HealingReport`.
- Added `SelfHealingRuntime`.
- Added default recovery policies.
- Added `healing.plan` and `healing.run` commands.
- Added `dr-magu healing-plan` and `dr-magu healing-run`.
- Added healing report storage under `.dr-magu/healing`.
- Added `self-healing-workflows` plugin metadata.
- Added self-healing workflow tests.

## v1.7.0 - Autonomous Software Factory

- Added `software_factory` package.
- Added `SoftwareFactoryPlanner`.
- Added `SoftwareFactoryRuntime`.
- Added `factory.plan`, `factory.run`, and `factory.stage` commands.
- Added `dr-magu factory-plan` and `dr-magu factory-run`.
- Added idea-to-delivery pipeline stages.
- Added factory artifact store under `.dr-magu/factory`.
- Added `autonomous-software-factory` plugin metadata.
- Added software factory tests.

## v1.6.0 - Multi-Agent Orchestrator

- Added `multi_agent` package.
- Added `MultiAgentPlanner`.
- Added `MultiAgentOrchestrator`.
- Added `multiagent.plan` and `multiagent.run` commands.
- Added `dr-magu multiagent-plan` and `dr-magu multiagent-run`.
- Added built-in SDLC and research-to-build pipelines.
- Added task dependency validation and result aggregation.
- Added `multi-agent-orchestrator` plugin metadata.
- Added multi-agent orchestration tests.

## v1.5.0 - Conversational Command Router

- Added `conversational_router` package.
- Added deterministic route model and router.
- Added `router.route` and `router.execute` commands.
- Added `dr-magu route` and `dr-magu route-execute`.
- Integrated the router into `brain.ask`.
- Added routing for website analysis, repository analysis, research, filesystem search and SDLC agents.
- Added `conversational-command-router` plugin metadata.
- Moved CLI `if __name__ == "__main__"` block to the end to avoid late-command registration issues.
- Added tests for natural-language command routing.

## v1.3.0 - Real MCP Integrations

- Added MCP templates for Playwright, Brave Search, GitHub and Filesystem.
- Added high-level MCP integration runtime.
- Added website analysis command.
- Added repository read command.
- Added filesystem search and web search MCP command boundaries.
- Added `config/mcp_servers.example.json`.
- Added `real-mcp-integrations` plugin metadata.
- Added tests for Playwright/GitHub/Filesystem integration contracts.

## v1.2.0 - MCP Research Runtime

- Added `mcp_runtime` package.
- Added MCP server registry.
- Added MCP tool call/result models.
- Added MCP client boundary with deterministic simulation mode.
- Added MCP-backed research provider.
- Updated `research.search` to default to MCP provider.
- Added `mcp.servers` and `mcp.call` commands.
- Added `dr-magu mcp-servers`.
- Added `mcp-research-runtime` plugin metadata.
- Added MCP research runtime tests.

## v1.1.4 - LLM Response Sanitization

- Added LLM response sanitizer.
- Hid raw provider payloads from normal chat output.
- Removed `reasoning_content`, token usage, logprobs and system fingerprints from debug payloads.
- Added `--debug` support for `dr-magu llm-chat`.
- Updated `brain.ask` to expose clean user-facing LLM responses.
- Added sanitization regression tests.

## v1.1.3 - OpenCode Provider Compatibility Fix

- Added provider-compatible headers to OpenAI-compatible LLM requests.
- Added stable `User-Agent: dr-magu-cli/1.1.3`.
- Added `LLM_USER_AGENT` override support.
- Added `LLM_EXTRA_HEADERS` JSON override support.
- Added regression tests to avoid Python urllib default signature issues.
- Updated LLM Runtime plugin metadata.

## v1.1.2 - LLM Runtime Integration

- Added `llm_runtime` package.
- Added OpenAI-compatible provider.
- Added normalized LLM message and response models.
- Added `llm.chat` command and `dr-magu llm-chat`.
- Integrated `brain.ask` with the LLM runtime for `general_chat` prompts.
- Preserved deterministic routing for action-oriented prompts.
- Added timeout, API key and provider error handling.
- Added `llm-runtime` plugin metadata.

## v1.1.1 - Conversational Brain Foundation

- Added Conversational Brain module.
- Added `brain.ask` and `brain.chat` command boundaries.
- Added `ask` and `chat` aliases.
- Added safe natural-language fallback in the TUI.
- Added `dr-magu brain-ask` and `dr-magu brain-chat`.
- Improved research intent detection for business/search/comparison prompts.
- Added default model context to conversational responses.
- Added conversational-brain plugin metadata.
- Added regression checks to preserve the `dr-magu tui` command.

## v1.1.0 - Execution Runtime Layer

- Added Execution Runtime Layer package.
- Added ExecutionPlan, ExecutionAction and ExecutionEvent models.
- Added ExecutionPermissions.
- Added execution plan persistence and logs.
- Added FilesystemRuntime, TerminalRuntime and GitRuntime.
- Added ExecutionPlanner and ExecutionExecutor.
- Added HITL approval request flow for sensitive execution plans.
- Added execution-runtime plugin metadata.
- Added command registry and CLI commands for plan creation, execution, inspection and listing.

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

# Dr Magu CLI v2.0.0

Dr Magu CLI is a Python-based agent platform foundation inspired by Claude Code, OpenCode, Codex CLI, and Gemini CLI.

This version adds the **Runtime Contracts Foundation** on top of the existing Control Center UI, Brain Foundation, Plugin Registry, Agent Lifecycle Management, workflow runtime, context generator, repository scanner, sessions, and TUI.

## What changed in v0.9.4

- Added Runtime Contracts Foundation.
- Added formal `ToolContract` metadata with input schemas, output schemas, risk levels, permission modes, and background execution flags.
- Added `BrainPlan`, `PlanStep`, and `PlanValidator` as the safe execution contract for the future AI Orchestrator Brain.
- Added `dr-magu contracts tools` to inspect Brain-facing tool contracts.
- Added `dr-magu plan validate --step <tool>` to validate a structured plan without executing it.
- Added internal commands `contracts.tools` and `plan.validate`.
- Extended Brain and Runtime snapshots with contract readiness metadata.
- Added permission policy metadata for high-risk and blocked operations.
- Kept all changes deterministic and LLM-call free.

## Architecture

```text
CLI / TUI
  ↓
Control Center
  ↓
Runtime Contracts + Plan Validator
  ↓
Brain Context Loader
  ↓
Plugin Registry
  ↓
Agent Registry
  ↓
Workflow Registry
  ↓
Tool Registry
  ↓
Permission Context Reader
  ↓
Workspace + Sessions
```


## Runtime Contracts

Inspect formal tool contracts exposed to the future Orchestrator Brain:

```bash
dr-magu contracts tools
dr-magu contracts tools --json
```

Validate a structured Brain plan without executing it:

```bash
dr-magu plan validate --step repo.scan --step context.generate
dr-magu plan validate --step shell.run
```

The validator can mark a plan as valid while still requiring approval for high-risk tools such as `shell.run`.

## Installation

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
pip install -e ".[dev]"
```

Linux/macOS:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
pip install -e ".[dev]"
```

## Start the TUI

```bash
dr-magu tui
```

With a specific workspace:

```bash
dr-magu tui --workspace D:\AI-DEMO\my-repo
```

## Control Center

```bash
dr-magu control center
```

Inspect one plugin impact summary:

```bash
dr-magu control plugin software-dev
```

Inside the TUI:

```text
/control
cc
/control-plugin software-dev
```

## Brain and runtime inspection

```bash
dr-magu brain context
dr-magu runtime inspect
dr-magu tools list
dr-magu permissions show
```

## Plugin operations

```bash
dr-magu plugin list
dr-magu plugin show software-dev
dr-magu plugin validate software-dev
```

## Agent operations

```bash
dr-magu agent list
dr-magu agent show repository-analyzer
dr-magu agent run repository-analyzer
dr-magu agent validate repository-analyzer
dr-magu agent enable repository-analyzer
dr-magu agent disable repository-analyzer
dr-magu agent delete repository-analyzer
```

## Workflow operations

```bash
dr-magu workflow list
dr-magu workflow run repository.context
dr-magu workflow runs
dr-magu workflow last
```

## Repository intelligence

```bash
dr-magu scan
dr-magu context generate
dr-magu context show
dr-magu context path
```

## Model configuration

Default Brain model values can be configured with environment variables:

```env
LLM_PROVIDER=opencode
LLM_BASE_URL=https://opencode.ai/zen/go/v1
LLM_API_KEY=sk-XXXXXXXXXXXXXXXXXXXXXXXXX
LLM_MODEL=deepseek-v4-flash
LLM_TEMPERATURE=0.1
```

Agents can override model settings, otherwise they inherit the default Brain model configuration.

## Run tests

```bash
pytest
```

Expected result:

```text
66 passed
```

## Roadmap

```text
v0.9.0  Brain Foundation
v0.9.1  Plugin Registry Foundation
v0.9.2  Agent Lifecycle Management
v0.9.3  Control Center UI
v0.10.0 AI Orchestrator Brain
```


## v0.9.5 - TUI Modularization

This release starts extracting the Terminal UI into a maintainable package structure.

Highlights:

- Added `src/dr_magu/tui/` package.
- Added shared TUI models.
- Added TUI command normalization helpers.
- Added reusable result summary helpers.
- Added screen metadata modules for Control Center, Session Manager and Agent Manager.
- Added widget label helpers.
- Kept backward compatibility with the current `dr_magu.tui_app` entry point.
- Prepared the TUI for future AI Orchestrator Brain views.


## v0.10.0 - AI Orchestrator Brain

This release introduces the first AI Orchestrator Brain foundation.

Highlights:

- Added Brain Context Loader.
- Added deterministic multilingual prompt planner.
- Added BrainPlan and BrainPlanStep models.
- Added Plan Validator.
- Added safe Plan Executor.
- Added `dr-magu ask`.
- Added `dr-magu brain-plan`.
- Added `dr-magu brain-execute`.
- Kept the LLM as planner-only architecture.
- Kept direct tool execution behind the existing Command Processor and validators.

Example:

```bash
dr-magu ask "analiza este repositorio y genera contexto tecnico"
```

Safety model:

```text
User Prompt
  -> Brain Planner
  -> BrainPlan
  -> Plan Validator
  -> Command Processor / Workflow Runtime / Agent Runner
```


## v0.11.0 - Intent Router

This release introduces the Intent Router foundation for the AI Agent Platform.

Supported route categories:

- `general_chat`
- `workspace_action`
- `research_action`
- `document_action`
- `software_action`
- `schedule_action`

New commands:

```bash
dr-magu brain-route "search the web for five sites about LangGraph"
dr-magu brain-route "generate a PDF report"
dr-magu brain-route "schedule a daily research report"
```

The router is deterministic in this version and prepares Dr Magu for future LLM-backed routing.


## v0.12.0 - Web Research Plugin Foundation

This release introduces the Web Research Plugin foundation.

Highlights:

- Added `research` plugin.
- Added `web-researcher` agent.
- Added `research.web` workflow metadata.
- Added `research.search` command/tool boundary.
- Added deterministic research provider for safe offline development.
- Added `.dr-magu/research/latest-research.json` persistence.
- Added `dr-magu research "topic"`.
- Prepared future live web connectors without coupling the Brain to a provider.

Example:

```bash
dr-magu research "AI developer tools" --limit 5
```


## v0.16.0 - Scheduler Runtime Foundation

This release upgrades the scheduler from metadata foundation to persisted runtime operations.

Highlights:

- Added formal `ScheduledTask` model.
- Added schedule persistence under `.dr-magu/schedules/`.
- Added next-run estimation for common cron shortcuts and expressions.
- Added schedule lifecycle operations:
  - create
  - list
  - enable
  - disable
  - soft-delete
  - run once
- Added `schedule.create`, `schedule.list`, `schedule.enable`, `schedule.disable`, `schedule.delete`, and `schedule.run`.
- Added CLI commands:
  - `dr-magu schedule-create`
  - `dr-magu schedule-list`
  - `dr-magu schedule-enable`
  - `dr-magu schedule-disable`
  - `dr-magu schedule-delete`
  - `dr-magu schedule-run`
- Prepared the runtime for future daemon/background workers.

Example:

```bash
dr-magu schedule-create daily-research --command "research.search LangGraph" --cron @daily
dr-magu schedule-list
dr-magu schedule-run daily-research
```


## v0.17.0 - Software Development Platform

This release introduces the Software Development Platform layer.

Highlights:

- Added SDLC agents:
  - repository-analyzer
  - architecture-planner
  - ticket-generator
  - code-reviewer
  - test-generator
  - documentation-writer
  - release-notes-generator
- Added `software-development` plugin.
- Added safe read-only Git tools:
  - files.list
  - git.diff
  - git.log
  - git.branch
- Added approval-aware shell tool:
  - shell.run
- Added workspace-scoped filesystem tools:
  - fs.list
  - fs.read
  - fs.write
- Added CLI commands:
  - dr-magu dev-agents
  - dr-magu dev-run <agent-id>
  - dr-magu git-status
  - dr-magu fs-list
  - dr-magu fs-read
  - dr-magu fs-write
  - dr-magu shell-run --approved

Generated SDLC artifacts are written to:

```text
.dr-magu/sdlc/
```


## v0.18.0 - Website Builder Workflow

This release introduces the Website Builder Workflow foundation.

Flow:

- Research websites
- Extract initial business/market context
- Generate website proposal
- Generate architecture options
- Create HITL approval request
- Generate report artifacts
- Persist workflow result

Generated artifacts:

```text
.dr-magu/website-builder/
  website-proposal.md
  architecture-options.json
  latest-website-builder-result.json

.dr-magu/approvals/
.dr-magu/reports/
.dr-magu/research/
.dr-magu/sdlc/
```

Example:

```bash
dr-magu website-build "AI developer tools landing page" --limit 5
```

This version intentionally stops before code generation. Code generation should be executed only after a human selects an architecture option.


## v0.19.0 - Workflow Engine Foundation

This release introduces the Workflow Engine Foundation.

Components:

- workflow-engine
- workflow-runner
- workflow-state
- workflow-context
- workflow-history

New commands:

```bash
dr-magu workflow-engine-run website-builder --topic "AI developer tools website"
dr-magu workflow-engine-runs
dr-magu workflow-engine-status <run-id>
dr-magu workflow-engine-history <run-id>
```

Persistence:

```text
.dr-magu/workflow-runs/<run-id>/
  state.json
  context.json
  history.json
```

This version provides a deterministic, stateful workflow foundation before advanced retry/resume/cancel capabilities.


## v0.20.0 - Workflow Runtime & History

This release extends the Workflow Engine with runtime operations.

New capabilities:

- Inspect workflow run state, context and latest event.
- Cancel workflow runs.
- Retry failed workflow runs.
- Resume pending/running/failed workflow runs.
- Export workflow history as JSON or Markdown.

New commands:

```bash
dr-magu workflow-runtime-inspect <run-id>
dr-magu workflow-runtime-cancel <run-id> --reason "Cancelled by user"
dr-magu workflow-runtime-retry <run-id>
dr-magu workflow-runtime-resume <run-id>
dr-magu workflow-runtime-export <run-id> --format md
```

Persistence remains under:

```text
.dr-magu/workflow-runs/<run-id>/
  state.json
  context.json
  history.json
  history.md
  history-export.json
```
\n\n## v0.21.0 - Background Worker Daemon\n- Background worker foundation\n- Queue/job runtime foundation\n- Scheduler integration preparation\n

## v0.22.0 - Platform Stabilization

This release adds platform readiness checks before v1.0.0.

New capability:

```bash
dr-magu stabilize
dr-magu stabilize --format json
```

Checks:

- Required runtime packages
- Required plugin manifests
- Required command registry entries
- Clean release artifacts
- README and CHANGELOG presence
- Validation files presence

Generated outputs:

```text
.dr-magu/stabilization/stabilization-report.txt
.dr-magu/stabilization/stabilization-report.json
```

This version prepares Dr Magu for the `v1.0.0 Stable AI Agent Platform` release.


## v1.1.0 - Execution Runtime Layer

This release introduces the Execution Runtime Layer.

Core concepts:

- Execution Planner
- Execution Executor
- Execution Permissions
- Execution Plans
- Execution Logs
- Execution History
- HITL integration for sensitive actions

Runtime capabilities:

- `filesystem.read`
- `filesystem.write`
- `filesystem.delete`
- `terminal.run`
- `files.list`
- `git.diff`
- `git.log`
- `git.branch`
- `git.commit`

New CLI commands:

```bash
dr-magu execution-plan-file docs/demo.md "hello"
dr-magu execution-plan-terminal "pytest"
dr-magu execution-plan-git-commit "docs: update generated docs"
dr-magu execution-run <plan-id> --approved
dr-magu execution-inspect <plan-id>
dr-magu execution-list
```

Persistence:

```text
.dr-magu/execution/<plan-id>/
  execution-plan.json
  execution-log.json
  execution-result.json
```

Security model:

```yaml
filesystem:
  read: true
  write: true
  delete: false

terminal:
  execute: true

git:
  read: true
  commit: true
  push: false

network:
  outbound: false
```


## v1.1.1 - Conversational Brain Foundation

This release introduces safe natural-language routing for Dr Magu.

New capabilities:

- `brain.ask`
- `brain.chat`
- `ask` and `chat` aliases
- `dr-magu brain-ask`
- `dr-magu brain-chat`
- TUI natural-language fallback for unknown command inputs
- Improved research intent detection for business/search/comparison prompts
- Default model context is included in conversational responses

Examples:

```bash
dr-magu brain-ask "What are the best CRM systems for small businesses?"
dr-magu run 'ask "Research the top 10 CRM systems for small businesses"'
```

In the TUI, natural-language input can be typed directly:

```text
What are the best CRM systems for small businesses?
```

v1.1.1 resolves the configured default model and returns its context, but live LLM calls remain reserved for the upcoming LLM Runtime implementation.


## v1.1.2 - LLM Runtime Integration

This release adds real default-model LLM chat execution.

New capabilities:

- `llm_runtime` package
- OpenAI-compatible chat completions provider
- `llm.chat` command
- `dr-magu llm-chat`
- `brain.ask` uses the LLM Runtime for `general_chat`
- Default model integration through `ModelConfigLoader`
- Timeout and error handling
- Missing API key validation

Example:

```bash
dr-magu llm-chat "hello"
dr-magu brain-ask "hello"
```

Environment:

```env
LLM_PROVIDER=opencode
LLM_BASE_URL=https://opencode.ai/zen/go/v1
LLM_API_KEY=sk-...
LLM_MODEL=deepseek-v4-flash
LLM_TEMPERATURE=0.1
```

Action-oriented prompts such as research, website generation, workflow execution, and repository analysis still route to commands/workflows. General chat now attempts an LLM call.


## v1.1.3 - OpenCode Provider Compatibility Fix

This release improves LLM provider compatibility for OpenAI-compatible endpoints such as:

```text
https://opencode.ai/zen/go/v1/chat/completions
```

Fixes:

- Replaces Python urllib's default User-Agent with `dr-magu-cli/1.1.3`.
- Keeps standard API headers:
  - `Authorization`
  - `Content-Type`
  - `Accept`
  - `User-Agent`
- Adds optional environment configuration:
  - `LLM_USER_AGENT`
  - `LLM_EXTRA_HEADERS`

Example:

```env
LLM_USER_AGENT=dr-magu-cli/1.1.3
LLM_EXTRA_HEADERS={"X-Client":"dr-magu"}
```

This addresses provider-side blocks such as Cloudflare `Error 1010: browser_signature_banned` caused by Python's default HTTP client signature.


## v1.1.4 - LLM Response Sanitization

This release improves the chat user experience by separating user-facing LLM output from provider internals.

Normal output hides:

- provider raw payload
- `reasoning_content`
- token usage
- logprobs
- system fingerprints
- nested provider debug fields

New behavior:

```bash
dr-magu llm-chat "hi"
```

prints only the assistant response.

Debug mode remains available:

```bash
dr-magu llm-chat "hi" --debug
```

Debug output is still sanitized to avoid exposing chain-of-thought style provider fields.


## v1.2.0 - MCP Research Runtime

This release adds the MCP Research Runtime foundation.

New capabilities:

- MCP server registry
- MCP client boundary
- MCP tool-call model
- MCP-backed research provider
- `mcp.servers`
- `mcp.call`
- `dr-magu mcp-servers`
- `research.search` defaults to the MCP research provider

Configuration options:

```env
RESEARCH_PROVIDER=mcp
MCP_WEB_SEARCH_COMMAND=your-mcp-web-search-server
MCP_SERVERS_JSON={"servers":[{"id":"web-search","name":"Web Search","enabled":true,"capabilities":["web_search"]}]}
```

Workspace config:

```text
.dr-magu/config/mcp_servers.json
```

Example:

```json
{
  "servers": [
    {
      "id": "web-search",
      "name": "Web Search MCP",
      "transport": "stdio",
      "command": "your-mcp-server-command",
      "args": [],
      "enabled": true,
      "capabilities": ["web_search", "research"]
    }
  ]
}
```

v1.2.0 includes a deterministic MCP simulation boundary for tests and offline development. A future version can replace the simulated call with a real MCP transport without changing the research workflow contract.


## v1.3.0 - Real MCP Integrations

This release adds first-class MCP integration contracts for:

- Playwright MCP
- Brave Search MCP
- GitHub MCP
- Filesystem MCP

New commands:

```bash
dr-magu mcp-servers
dr-magu website-analyze "https://example.com"
dr-magu repository-read "owner/repo"
```

Command mode:

```text
website.analyze https://example.com
repository.read owner/repo
filesystem.search src
web.search "AI agent platforms"
```

Configuration template:

```text
config/mcp_servers.example.json
```

Workspace configuration:

```text
.dr-magu/config/mcp_servers.json
```

v1.3.0 keeps deterministic simulation available for tests and offline development, while defining the contracts needed to attach real MCP servers.


## v1.5.0 - Conversational Command Router

This release adds natural-language command routing.

Instead of requiring users to know explicit commands:

```text
website.analyze https://hubspot.com
repository.read microsoft/vscode
research.search "CRM systems"
filesystem.search src
```

users can write natural requests:

```text
Analyze hubspot.com and summarize its business model
Analyze repository https://github.com/microsoft/vscode
Research the top 10 CRM systems for small businesses
Find files in src
```

New commands:

```bash
dr-magu route "Analyze hubspot.com"
dr-magu route-execute "Analyze hubspot.com"
```

Command mode:

```text
router.route Analyze hubspot.com
router.execute Analyze hubspot.com
```

The router resolves:

- website analysis → `website.analyze`
- repository analysis → `repository.read`
- web/research → `research.search` or `web.search`
- filesystem search → `filesystem.search`
- software development prompts → SDLC agents
- general chat → LLM chat


## v1.6.0 - Multi-Agent Orchestrator

This release adds coordinated multi-agent execution.

New commands:

```bash
dr-magu multiagent-plan sdlc.pipeline
dr-magu multiagent-run sdlc.pipeline
```

Command mode:

```text
multiagent.plan sdlc.pipeline
multiagent.run sdlc.pipeline
```

Built-in pipelines:

- `sdlc.pipeline`
  - repository-analyzer
  - architecture-planner
  - ticket-generator
  - test-generator
  - documentation-writer
  - release-notes-generator

- `research.build`
  - web-researcher
  - website-analyzer
  - architecture-planner
  - ticket-generator

The orchestrator validates task dependencies, executes steps in order, aggregates results, and stops on failure unless `--continue-on-error` is enabled.


## v1.7.0 - Autonomous Software Factory

This release adds an end-to-end software factory pipeline.

New commands:

```bash
dr-magu factory-plan "Build a CRM"
dr-magu factory-run "Build a CRM"
```

Command mode:

```text
factory.plan Build a CRM
factory.run Build a CRM
factory.stage "Build a CRM" --stage code-plan
```

Pipeline stages:

1. Idea Intake
2. Research
3. Architecture
4. Tickets
5. Code Plan
6. Tests
7. Documentation
8. Release Notes

Artifacts are stored under:

```text
.dr-magu/factory/
```
\n
## v1.8.0 - Self-Healing Workflows

This release adds retry, fallback and escalation around command execution.

New commands:

```bash
dr-magu healing-plan "website.analyze https://example.com"
dr-magu healing-run "unknown.command" --fallback-command files.list --max-retries 0
```

Command mode:

```text
healing.plan website.analyze https://example.com
healing.run unknown.command --fallback-command files.list --max-retries 0
```

Healing behavior:

1. Execute primary command
2. Retry when configured
3. Execute fallback command when configured
4. Escalate for human review when unrecovered
5. Store report under `.dr-magu/healing/latest-healing-report.json`


## v2.0.0 - AI Operating System

This release consolidates Dr Magu into an AI Operating System control layer.

New commands:

```bash
dr-magu os-status
dr-magu os-capabilities
dr-magu os-boot
dr-magu os-dispatch "files.list"
```

Command mode:

```text
os.status
os.capabilities
os.boot
os.dispatch files.list
```

AI OS layers:

- conversation
- routing
- llm
- mcp
- agents
- workflows
- execution
- scheduler
- software_factory
- self_healing
- plugins
- permissions

The AI OS layer provides a unified control surface over the platform capabilities added from v1.0.0 through v1.8.0.

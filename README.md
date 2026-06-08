# Dr Magu CLI v0.10.0

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

# Dr Magu CLI v0.9.3

Dr Magu CLI is a Python-based agent platform foundation inspired by Claude Code, OpenCode, Codex CLI, and Gemini CLI.

This version adds the **Control Center UI** on top of the existing Brain Foundation, Plugin Registry, Agent Lifecycle Management, workflow runtime, context generator, repository scanner, sessions, and TUI.

## What changed in v0.9.3

- Added Control Center dashboard.
- Added `dr-magu control center`.
- Added `dr-magu control plugin <plugin-id>`.
- Added internal commands `control.center` and `control.plugin`.
- Added TUI commands `/control`, `cc`, and `/control-plugin <plugin-id>`.
- Added Control Center sections for plugins, agents, workflows, tools, permissions, schedules, and Brain readiness.
- Added plugin impact view with agents, workflows, tools, commands, schedules, health warnings, and errors.
- Reserved a Control Center area for future scheduler/cron task management.
- Kept all changes deterministic and LLM-call free.

## Architecture

```text
CLI / TUI
  ↓
Control Center
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

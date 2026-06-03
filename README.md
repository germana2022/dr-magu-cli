# Dr Magu CLI v0.3.0

Dr Magu CLI is a Python-based developer tooling foundation inspired by Claude Code and OpenCode.

This version focuses on the **Terminal UI foundation**. It keeps the existing Tool CLI and Command Processor from v0.2.0, and adds a Textual/Rich TUI that can process internal commands from an interactive terminal interface.

## What changed in v0.3.0

- Added `dr-magu tui`.
- Added an OpenCode-style terminal layout.
- Added main console panel.
- Added right context sidebar.
- Added bottom prompt input.
- Added status/header/footer regions.
- Added slash commands: `/help`, `/commands`, `/status`, `/run`, `/clear`, `/exit`.
- Connected the TUI to the existing `CommandProcessor`.
- Kept the implementation agent-free and LLM-free for this phase.

## Architecture

```text
CLI Entry Point
  ↓
Terminal UI
  ↓
TUI Command Handler
  ↓
Command Processor
  ↓
Command Registry
  ↓
Tool Layer
  ↓
Workspace
```

## Installation

Windows PowerShell:

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .[dev]
```

Linux/macOS:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

## Start the TUI

```bash
dr-magu tui
```

With a specific workspace:

```bash
dr-magu tui --workspace D:\AI-DEMO\my-repo
```

## TUI commands

Inside the TUI:

```text
/help
/commands
/status
/run git.status
/run files.list .
/run files.read README.md
/clear
/exit
```

You can also run internal commands directly:

```text
git.status
files.list .
search.code CommandProcessor src
```

## Direct CLI commands

```bash
dr-magu files list .
dr-magu files read README.md
dr-magu search code "CommandProcessor"
dr-magu git status
dr-magu git diff
dr-magu shell run "pytest"
```

## Command Processor mode

```bash
dr-magu run "files.list ."
dr-magu run "files.read README.md"
dr-magu run "search.code CommandProcessor src"
dr-magu run "git.status"
dr-magu run "git.diff"
dr-magu run "shell.run pytest"
```

## List registered commands

```bash
dr-magu commands list
dr-magu commands list --json
```

## JSON output

```bash
dr-magu run "files.read README.md" --json
dr-magu files list . --json
```

## Configuration

The orchestration configuration is in English:

```text
config/orchestration.yaml
```

Main sections:

```text
runtime
permissions
blocked_shell_patterns
command_registry
tui
```

## Run tests

```bash
pytest
```

Expected result:

```text
11 passed
```

## Roadmap

```text
v0.1.0  Tool CLI foundation
v0.2.0  Command Processor + Command Registry
v0.3.0  Terminal UI Foundation
v0.4.0  Security Layer + Approval Rules
v0.5.0  Session Management
v0.6.0  Repository Analyzer Engine
v0.7.0  LangGraph Runtime
```

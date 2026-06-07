"""Command aliases and TUI command normalization helpers."""

from __future__ import annotations


EXIT_COMMANDS = {"/exit", ":q", "quit", "exit"}
CLEAR_COMMANDS = {"/clear", "clear", "cls"}
HELP_COMMANDS = {"/help", "help", "?"}
COMMANDS_COMMANDS = {"/commands", "commands"}
STATUS_COMMANDS = {"/status", "status"}
SESSION_MANAGER_COMMANDS = {"/session", "/sessions", "session", "sessions", "ss"}
RUNTIME_COMMANDS = {"/runtime", "runtime", "ri"}
CONTROL_CENTER_COMMANDS = {"/control", "control", "cc"}
PLUGINS_COMMANDS = {"/plugins", "plugins", "pl"}
BRAIN_COMMANDS = {"/brain", "brain"}
AGENTS_COMMANDS = {"/agents", "agents", "al"}
TOOLS_COMMANDS = {"/tools", "tools", "tl"}
PERMISSIONS_COMMANDS = {"/permissions", "permissions", "perm"}
WORKFLOW_RUNS_COMMANDS = {"/workflow-runs", "workflow-runs", "wr"}
WORKFLOW_LAST_COMMANDS = {"/workflow-last", "workflow-last", "wl"}


def normalize_command(raw_value: str) -> str:
    """Normalize a TUI command before passing it to the command processor."""
    command = raw_value.strip()
    if command.startswith("/") and not command.startswith("/run "):
        command = command[1:]
    if command.startswith("run "):
        command = command.removeprefix("run ").strip()
    elif command.startswith("/run "):
        command = command.removeprefix("/run ").strip()
    return command

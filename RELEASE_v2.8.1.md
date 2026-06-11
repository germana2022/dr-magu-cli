# dr-magu-cli v2.8.1 — TUI Copy and Export Patch

## Summary

This patch improves the Terminal UI usability for long operational logs and command outputs.

## Changes

- Added `Ctrl+Y` to copy the last command result as plain JSON text.
- Added `Ctrl+E` to export the current TUI transcript to `.dr-magu/tui/`.
- Added `/copy`, `/copy-last`, `/copy-session`, and `/export-log` commands.
- Added workspace-local fallback artifacts when the OS clipboard is unavailable.
- Added copy-friendly plain-text formatting for command results.
- Updated TUI help and shortcut sidebar.

## Why

Textual terminal widgets can capture mouse interaction, making it difficult to select and copy long command logs directly from the UI. This patch adds explicit copy/export actions without changing the orchestration runtime.

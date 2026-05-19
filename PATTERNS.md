# Pattern Registry: Agentic Vibe Fleet

This document records established engineering patterns and design decisions to ensure consistency and avoid "GIST debt".

## 1. Architectural Patterns
*   **Cross-Platform Automation**: All project maintenance and hygiene scripts must be written in Python to ensure compatibility across Windows, macOS, and Linux. Shell-specific scripts (Bash/PowerShell) are permitted only in specialized, hardened environments where a Python runtime is strictly prohibited.
*   **Non-Hardcoded LLM Selection**: Scripts interacting with LLMs must dynamically query available models rather than using hardcoded strings. This prevents breaking changes when models are deprecated or updated.
*   **Automation-First CLI**: All interactive scripts must support CLI arguments to bypass user input (e.g., `--model`) and allow for safe previewing of actions (e.g., `--dry-run`). This ensures scripts are compatible with CRON jobs and CI/CD pipelines.

## 2. Coding Standards
*   **CLI Argument Parsing**: Use the standard `argparse` library for all scripts to provide a consistent interface for flags and help menus.

## 3. Tooling Conventions
*   **Dry-Run Safety**: Destructive or file-writing operations should be gated behind a check for a `dry_run` flag, printing the intended action to `stdout` instead of executing it.

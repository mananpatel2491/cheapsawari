# Pattern Registry: Agentic Vibe Fleet

This document records established engineering patterns and design decisions to ensure consistency and avoid "GIST debt".

## 1. Architectural Patterns
*   **Cross-Platform Automation**: All project maintenance and hygiene scripts must be written in Python to ensure compatibility across Windows, macOS, and Linux. Shell-specific scripts (Bash/PowerShell) are permitted only in specialized, hardened environments where a Python runtime is strictly prohibited.
*   **Non-Hardcoded LLM Selection**: Scripts interacting with LLMs must dynamically query available models rather than using hardcoded strings. This prevents breaking changes when models are deprecated or updated.
*   **Automation-First CLI**: All interactive scripts must support CLI arguments to bypass user input (e.g., `--model`) and allow for safe previewing of actions (e.g., `--dry-run`). This ensures scripts are compatible with CRON jobs and CI/CD pipelines.
*   **Contract-First Validation (Bruno)**: Every new API-exposed backend function requires a corresponding Bruno script. Commits are blocked unless Bruno validation passes. Exceptions require an explicit owner acknowledgment in the commit message: `"I understand bruno validation is failing and I allow the exception to have the code committed to github repo"`.
*   **Full-Stack Traceability Mapping**: Maintain a functional mapping between frontend components and backend endpoints in `docs/Function_Mapping.md`. This map must be updated whenever functions are added, updated, or deleted to ensure cross-layer integrity.
*   **Proactive Hardening**: When updating an existing file, the agent must audit the logic for security risks (e.g., injection, leaked secrets) and resource/memory leaks. If found, these must be patched immediately and logic added to prevent reintroduction.
*   **Production Readiness Gating**: Code containing comments indicating temporary setups, mocks, or non-production quality (e.g., `// TODO: temp`, `// fix later`) must be flagged. The agent must explicitly ask the Director if these should be addressed before proceeding.
*   **Infrastructure Migration Advisory**: When transitioning from local/mock implementations to production-ready infrastructure, the agent must present a comparative selection of technology options (e.g., for Identity: AWS Cognito, Azure AD, Auth0) and seek the Director's arbitration before implementation.
    *   **Resolved — Identity (Slice 6, 2026-06-24):** Director chose **Google Identity Services + signed session cookie + Firestore allowlist** (over Firebase Auth and Cloud IAP) to keep the single $0 Cloud Run service. A `dev`/`google` mode split keeps the gate locally testable. Do not re-litigate; extend this stack for future access needs.

## 2. Coding Standards
*   **CLI Argument Parsing**: Use the standard `argparse` library for all scripts to provide a consistent interface for flags and help menus.

## 3. Tooling Conventions
*   **Dry-Run Safety**: Destructive or file-writing operations should be gated behind a check for a `dry_run` flag, printing the intended action to `stdout` instead of executing it.

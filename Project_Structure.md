# Project Structure: Agentic Vibe Fleet

This document provides a functional map of the codebase, enabling the Lead Agent (Gemini) to navigate and implement features with full architectural context.

## Core Framework (The 'Director' Layer)

| Path | Purpose |
| :--- | :--- |
| `GEMINI.md` | **Constitution**: The central nervous system and non-negotiable operating procedures. |
| `Project_Structure.md` | **Architecture Map**: This document. Functional mapping of the codebase. |
| `requirements.txt` | **Dependencies**: Python package requirements for the project. |
| `GEMINI_Getting_Started.md` | **Onboarding**: Auto-updated guide on using Gemini Code Assist features. |
| `PATTERNS.md` | **Pattern Registry**: Living document for established engineering patterns and design decisions. |
| `scripts/` | **Agentic Skills**: Maintenance and hygiene scripts accessible to agents. |
| `bruno/` | **API Validation**: Bruno collections and documentation for contract testing. |
| `terraform/` | **Infrastructure-as-Code**: GCP/Terraform configuration for cost-gated deployments. |

## Application Layer (TBD)

| Path | Purpose |
| :--- | :--- |
| `src/` | Application source code. |
| `docs/` | Extended documentation and design specs. |

## Changelog

| Date | Action | Files Affected | Summary |
| :--- | :--- | :--- | :--- |
| 2026-05-19 | INITIALIZE | `Project_Structure.md`, `GEMINI.md`, `README.md`, `.gitignore`, `LICENSE`, `PATTERNS.md`, `scripts/README.md`, `bruno/README.md`, `terraform/README.md` | Initial architecture mapping and framework bootstrapping for the Director layer. |
| 2026-05-19 | REFACTOR | `scripts/verify_structure.py`, `scripts/verify-structure.ps1` | Refactored changelog consistency script: Replaced PowerShell version (`verify-structure.ps1`) with a cross-platform Python equivalent (`verify_structure.py`). |
| 2026-05-20 | UPDATE | `GEMINI_Getting_Started.md`, `requirements.txt`, `PATTERNS.md`, `scripts/update_getting_started.py`, `scripts/optimize_changelog.py` | Bootstrapped Gemini integration ecosystem: Migrated to `google-genai`, added `.env` support, established automation patterns (CLI/Dry-Run), and added self-maintenance skills for documentation and changelog optimization. |
| 2026-05-20 | REFACTOR | `scripts/verify_structure.py` | Standardized CLI interface using argparse to support fleet-wide consistency for --dry-run and --model arguments. |
| 2026-05-20 | UPDATE | `README.md` | Expanded root documentation to provide a comprehensive project overview, role definitions, and maintenance workflows. |

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
| `bootstrap_prompts/` | **Plan Archive**: Systematic prompts generated from user intent to start new sessions. |
| `terraform/` | **Infrastructure-as-Code**: GCP/Terraform configuration for cost-gated deployments. |

## Application Layer (TBD)

| Path | Purpose |
| :--- | :--- |
| `src/` | Application source code. |
| `docs/architecture_overview.html` | **Visual Guide**: A 1-page HTML overview of the Agentic Vibe Fleet framework. (Excluded from `verify_structure.py` checks) |
| `Function_Mapping.md` | **Traceability Map**: Correlates frontend components with backend API functions. |

## Changelog

| Date | Action | Files Affected | Summary |
| :--- | :--- | :--- | :--- |
| 2026-05-19 | INITIALIZE | `Project_Structure.md`, `GEMINI.md`, `README.md`, `.gitignore`, `LICENSE`, `PATTERNS.md`, `scripts/README.md`, `bruno/README.md`, `terraform/README.md` | Initial architecture mapping and framework bootstrapping for the Director layer. |
| 2026-05-19 | ADD | `scripts/verify_structure.py` | Added hygiene script (Python) to enforce changelog consistency. |
| 2026-05-19 | DELETE | `scripts/verify-structure.ps1` | Removed PowerShell version in favor of cross-platform Python script. |
| 2026-05-20 | ADD | `GEMINI_Getting_Started.md`, `scripts/update_getting_started.py` | Added onboarding documentation and an automated skill to keep it updated via Gemini API. |
| 2026-05-20 | ADD | `requirements.txt` | Added dependency manifest to automate environment setup. |
| 2026-05-20 | UPDATE | `requirements.txt`, `scripts/update_getting_started.py` | Migrated from deprecated `google-generativeai` to `google-genai` SDK. |
| 2026-05-20 | UPDATE | `requirements.txt`, `scripts/update_getting_started.py` | Added `python-dotenv` support for more secure and portable API key management. |
| 2026-05-20 | UPDATE | `scripts/update_getting_started.py` | Refined .env loading logic to use absolute project root paths for better reliability. |
| 2026-05-20 | UPDATE | `scripts/update_getting_started.py` | Switched to `gemini-1.5-flash` to resolve 404 NOT_FOUND errors in the v1beta API. |
| 2026-05-20 | FIX | `scripts/update_getting_started.py` | Forced SDK to use `v1` API endpoint to resolve model-not-found errors. |
| 2026-05-20 | UPDATE | `scripts/update_getting_started.py` | Implemented dynamic model selection via `client.models.list()` to prevent future 404s. |
| 2026-05-20 | UPDATE | `PATTERNS.md`, `scripts/update_getting_started.py` | Codified automation patterns (Python-only, dynamic LLM, CLI arguments, and dry-run support). |
| 2026-05-20 | ADD | `scripts/optimize_changelog.py` | Added LLM-powered script to consolidate and clean the architectural changelog. |
| 2026-05-20 | UPDATE | `PATTERNS.md`, `Project_Structure.md`, `Function_Mapping.md` | Added patterns for Contract-First Bruno validation and Full-Stack Traceability Mapping. |
| 2026-05-20 | ADD | `scripts/generate_bootstrap_prompt.py`, `bootstrap_prompts/` | Added 'Prompt Architect' skill to automate context-aware session planning and plan archiving. |
| 2026-05-20 | MOVE | `architecture_overview.html` | Moved visual architecture overview to `docs/` folder and excluded `docs/` from `verify_structure.py` checks. |
| 2026-05-20 | BASELINE | ALL | **V0.0.1 Template Baseline**: Director Layer operational. Ready for autonomous vibe coding and replication. |

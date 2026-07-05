# cheapsawari Constitution

> **Precedence**: `GEMINI.md` is the Project Constitution of record for this repository.
> This file is its Spec Kit–facing distillation, consumed by the `/speckit.*` workflow.
> On any conflict, `GEMINI.md` (and `PATTERNS.md` for design decisions) wins.

## Core Principles

### I. Context-First Architecture Map
Before proposing any change, read `Project_Structure.md` and use its functional descriptions (and `Function_Mapping.md` for frontend↔backend traceability) to decide how a feature lands. Every file addition or removal is logged in the Changelog table immediately — no deferred bookkeeping.

### II. Pattern Reference Integrity
Consult `PATTERNS.md` at the start of every session. Inherit prior design decisions instead of re-litigating them — e.g., Identity is **resolved** (Google Identity Services + signed `__session` cookie + Firestore allowlist; extend that stack, never revisit). Never record aspirational designs — every pattern entry must reflect the actual codebase.

### III. Automated Maintenance via Agentic Skills
Project hygiene runs through the `scripts/` folder (Python, cross-platform, `argparse`, `--dry-run` support). `scripts/verify_structure.py` must pass before a slice is committed. Tedious mechanical work may be delegated to local models to preserve API quota.

### IV. Continuous API Validation (Bruno) — NON-NEGOTIABLE
No backend API feature is complete until the Bruno collection (`bruno/cheapsawari/`) is updated and the full gate passes. Successful Bruno execution gates all commits; the only exception requires the exact acknowledgment string recorded in `GEMINI.md`/`PATTERNS.md`. A feature is "done" only when automated validation passes and its visual flow is verified (Playwright for dashboard changes).

### V. Infrastructure-as-Code & Cost Gating
Every infra-dependent feature requires a Terraform update (`terraform/` codifies the GCP platform; the Cloud Run service itself deploys via `gcloud run deploy`). Projected costs are calculated and reviewed before shipping; the standing budget is **~$0/mo** (single scale-to-zero Cloud Run service + Firestore/Hosting free tiers). Features that break the $0 posture require Director arbitration first.

## Operational Constraints

- **80/20 Surgical Strike**: 80% of a session is read-only planning, 20% execution; one testable slice per session to prevent cascade damage. The Spec Kit chain (`specify → clarify → plan → tasks → implement`) is the concrete implementation of the planning phase — specs in `specs/NNN-*/` are the durable artifacts of the 80%.
- **Roles**: The Director (owner) owns intent, arbitration, and final review. The Lead Agent owns autonomous reasoning, planning, and error-free execution.
- **Product goal**: a personal, **invite-only** fare-bucket tool for the owner + friends to get fair pricing — NOT an OTA/broker; affiliate monetization is incidental. Optimize for the traveler's outcome.
- **Provider/store seams are sacred**: new fare sources go behind `FareProvider` (live source: Travelpayouts/Aviasales cached price data; Amadeus is dead), persistence behind `WatchRepository` (SQLite dev / Firestore prod), notifications behind `AlertChannel` (log/webhook/email). Extend seams, don't bypass them.
- **Proactive hardening**: when touching an existing file, audit for security risks and leaks; patch immediately. Temporary/mock markers (`TODO: temp`, `fix later`) must be flagged to the Director before proceeding.

## Development Workflow

- Slice-on-main git flow: each feature ships as one Bruno-gated slice committed **directly on `main`**; local only — never push or deploy unless the Director asks.
- Clarify ambiguous prompts before acting; if a line of code cannot be justified, it is not implemented.
- Start fresh sessions frequently to avoid context rot; durable memory lives in `Project_Structure.md`, `PATTERNS.md`, `GEMINI.md`, and `specs/`.

## Governance

This distillation is regenerated whenever `GEMINI.md` or `PATTERNS.md` materially changes. Amendments to the actual constitution happen in `GEMINI.md` under Director approval; this file never introduces rules of its own. All spec/plan/task artifacts produced by `/speckit.*` must be verified for compliance against the principles above.

**Version**: 1.0.0 | **Ratified**: 2026-07-05 | **Last Amended**: 2026-07-05

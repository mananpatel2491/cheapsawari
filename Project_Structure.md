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

## Application Layer

| Path | Purpose |
| :--- | :--- |
| `src/main.py` | **API**: FastAPI app. `GET /health` + `GET /api/v1/offers/cheapest` (Slice 1). |
| `src/config.py` | **Settings**: Env-driven config (provider choice, Amadeus creds, timeouts). |
| `src/models.py` | **Domain**: Provider-agnostic `Offer` model (the time-series record). |
| `src/providers/base.py` | **Seam**: `FareProvider` ABC + `ProviderError`. The data-source contract. |
| `src/providers/mock.py` | **Provider**: Deterministic, network-free mock (default; test-safe, zero quota). |
| `src/providers/amadeus.py` | **Provider**: Amadeus Self-Service impl (OAuth2 + Flight Offers Search). |
| `src/providers/factory.py` | **Selector**: Resolves the active provider from `FARE_PROVIDER`. |
| `src/store/base.py` | **Seam**: `WatchRepository` ABC + `WatchNotFoundError`. The persistence contract. |
| `src/store/sqlite_store.py` | **Store**: Default SQLite impl (stdlib, durable, hermetic; FK cascade). |
| `src/store/firestore_store.py` | **Store**: Cloud Firestore impl (`WATCH_STORE=firestore`); used in prod. |
| `src/store/factory.py` | **Selector**: Resolves the active store from `WATCH_STORE` (sqlite \| firestore). |
| `src/poll.py` | **Poll engine**: Quota-capped `poll_active_watches` + `PollSummary` (Slice 3a). |
| `Dockerfile` | **Container**: Cloud Run image (python:3.13-slim, uvicorn on `$PORT`). |
| `.dockerignore` | Keeps the build context to `src/` + `requirements.txt`. |
| `bruno/cheapsawari/` | **API Validation**: Bruno collection — offers + watches + poll seams (gate: 67/67, green on both sqlite and Firestore). |
| `docs/DEPLOYMENT.md` | **Runbook**: Live cloud resources, env, redeploy, cost review. |
| `docs/architecture_overview.html` | **Visual Guide**: A 1-page HTML overview of the Agentic Vibe Fleet framework. (Excluded from `verify_structure.py` checks) |
| `Function_Mapping.md` | **Traceability Map**: Correlates frontend components with backend API functions. |

> **Roadmap (rolling MVP):** Slice 1 — fare-fetch seam ✅ · Slice 2 — watches + persistence ✅ · Slice 3a — quota-capped poll engine ✅ · Slice 3b — cloud wiring (Firestore + Cloud Run + Cloud Scheduler) ✅ LIVE on mock · Slice 4 — signal + single-channel alert · Slice 5 — minimal dashboard. _(Pending owner input: Amadeus API keys to flip prod from mock to live fares.)_

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
| 2026-06-21 | UPDATE | `PATTERNS.md` | Synced Pattern Registry to current AVF framework: added Proactive Hardening, Production Readiness Gating, and Infrastructure Migration Advisory patterns. cheapsawari now at framework parity. |
| 2026-06-21 | ADD | `src/__init__.py`, `src/config.py`, `src/models.py`, `src/main.py`, `src/providers/__init__.py`, `src/providers/base.py`, `src/providers/mock.py`, `src/providers/amadeus.py`, `src/providers/factory.py`, `bruno/cheapsawari/bruno.json`, `bruno/cheapsawari/environments/local.bru`, `bruno/cheapsawari/offers/health.bru`, `bruno/cheapsawari/offers/cheapest_deterministic.bru`, `bruno/cheapsawari/offers/cheapest_normalizes_lowercase.bru`, `bruno/cheapsawari/offers/cheapest_business_cabin.bru`, `bruno/cheapsawari/offers/no_inventory_404.bru`, `bruno/cheapsawari/offers/same_city_400.bru`, `bruno/cheapsawari/offers/bad_iata_422.bru`, `.env.example` | **Slice 1 — fare-fetch seam.** FastAPI `GET /api/v1/offers/cheapest` (+ `/health`) backed by a `FareProvider` interface with mock (default, zero-quota) and Amadeus implementations, returning a normalized `Offer`. Bruno gate green (7 req / 24 assertions) against mock. Cost review: $0 (no infra; local + mock). |
| 2026-06-22 | ADD | `src/store/__init__.py`, `src/store/base.py`, `src/store/sqlite_store.py`, `src/store/factory.py`, `bruno/cheapsawari/watches/create_watch.bru`, `bruno/cheapsawari/watches/get_watch.bru`, `bruno/cheapsawari/watches/list_watches.bru`, `bruno/cheapsawari/watches/refresh_watch.bru`, `bruno/cheapsawari/watches/refresh_watch_again.bru`, `bruno/cheapsawari/watches/list_snapshots.bru`, `bruno/cheapsawari/watches/get_missing_404.bru`, `bruno/cheapsawari/watches/create_same_city_400.bru`, `bruno/cheapsawari/watches/delete_watch.bru`, `bruno/cheapsawari/watches/verify_deleted_404.bru` | **Slice 2 — watches + persistence.** `WatchRepository` seam with a default SQLite store (stdlib, durable, FK cascade); `WATCH_STORE=firestore` reserved for Slice 3. New endpoints: POST/GET/DELETE `/api/v1/watches`, `POST .../refresh` (records a snapshot via the active provider — manual precursor to the scheduler), `GET .../snapshots` (price history). Bruno gate green (17 req / 52 assertions). Cost review: $0 (local SQLite; no infra). |
| 2026-06-22 | ADD | `src/poll.py`, `bruno/cheapsawari/poll/create_watch_a.bru`, `bruno/cheapsawari/poll/create_watch_b.bru`, `bruno/cheapsawari/poll/poll_no_token_401.bru`, `bruno/cheapsawari/poll/poll_run.bru`, `bruno/cheapsawari/poll/verify_snapshot_recorded.bru`, `bruno/cheapsawari/poll/cleanup_a.bru`, `bruno/cheapsawari/poll/cleanup_b.bru` | **Slice 3a — quota-capped poll engine.** `poll_active_watches` polls active watches once, capped at `POLL_MAX_PER_RUN` (default 60, keeps the fleet under the ~66/day Amadeus budget); one provider error is counted, not fatal. `POST /api/v1/poll` returns a `PollSummary`; optional `POLL_TOKEN`/`X-Poll-Token` guard so a public URL can't burn quota. Bruno gate green (24 req / 67 assertions). Cost review: $0 (local). Slice 3b (Firestore store + Cloud Run + Cloud Scheduler) pending Firebase details. |
| 2026-06-22 | ADD | `src/store/firestore_store.py`, `Dockerfile`, `.dockerignore` | **Slice 3b — cloud wiring (LIVE).** `FirestoreWatchRepository` (`watches/{id}` + `snapshots/` subcollection, explicit snapshot delete since Firestore has no cascade); factory `firestore` branch (lazy import); `gcp_project` setting. Deployed to Cloud Run (`cheapsawari-api`, us-central1, FARE_PROVIDER=mock, WATCH_STORE=firestore, POLL_TOKEN-guarded) backed by Firestore Native, with a Cloud Scheduler daily poll (08:00 America/Detroit). Full Bruno gate (67/67) verified green against real Firestore; live scheduler→poll→snapshot path confirmed. Cost review: ~$0/mo (scale-to-zero + free tiers). Infra provisioned via gcloud; terraform codification tracked in docs/DEPLOYMENT.md. |

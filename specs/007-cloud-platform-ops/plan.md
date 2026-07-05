# Implementation Plan: Cloud Platform & Ops

**Branch**: `retro/007-cloud-platform-ops` | **Date**: 2026-07-05 | **Spec**: [spec.md](./spec.md)

**Input**: As-built reconstruction from Slice 3b (2026-06-22) and Slices 10/11/12
(2026-06-25).

## Summary

A `python:3.13-slim` container runs the FastAPI app on Cloud Run `cheapsawari-api`
(us-central1, scale-to-zero, public-invoker + app-level auth), backed by Firestore
Native and poked daily by Cloud Scheduler with the `X-Poll-Token` secret. Firebase
Hosting rewrites `**` from cheapsawari.web.app to the service. Terraform codifies the
durable platform (APIs, Firestore, IAM, invoker binding, scheduler) while reading the
Cloud Run service as a data source; `import.sh` adopts the pre-existing imperative
infra into state. `src/obs.py` gives the app JSON-on-Cloud-Run / text-locally
structured logging with an event catalog in `docs/LOGGING.md`.

## Technical Context

**Language/Version**: Python 3.13 container; Terraform ≥ 1.5, hashicorp/google ~> 6.0
(`terraform/versions.tf`)

**Primary Dependencies**: gcloud (app deploys via Cloud Build), firebase-tools
(hosting deploy), terraform (platform); zero new Python deps (obs is stdlib)

**Storage**: Firestore Native `(default)` us-central1; local terraform state
(GCS backend stanza prepared, commented)

**Testing**: full Bruno gate against real Firestore (Slice 3b); `terraform
fmt/validate/plan` against live GCP; live URL smoke checks (Slice 12); in-process +
live-uvicorn log-envelope verification (Slice 11)

**Target Platform**: GCP project `cheapsawari`, us-central1

**Project Type**: infrastructure + ops layer of a single web service

**Performance Goals**: scale-to-zero idle; one scheduler invocation/day

**Constraints**: ~$0/mo standing budget (constitution gate); secrets in Cloud Run env
(tfvars gitignored); app deploys must never fight terraform

**Scale/Scope**: 4 tf files (~185 lines) + import script, Dockerfile, firebase.json,
`src/obs.py` (~115 lines), 2 runbooks (DEPLOYMENT, LOGGING)

## Constitution Check

Gated against `.specify/memory/constitution.md` (distillation; `GEMINI.md` supreme).

- **I. Context-First Architecture Map — PASS.** terraform/, Dockerfile, firebase.json,
  `src/obs.py`, and docs are all mapped (`Project_Structure.md:17,29,56-57,60-61`);
  each slice's changelog row lists files.
- **II. Pattern Reference Integrity — PASS.** AVF Pattern 5 (IaC) explicitly resolved
  by Slice 10 ("tech-debt resolved" in the changelog row); the Slice 3b row had
  honestly logged the imperative provisioning as tracked debt.
- **III. Automated Maintenance via Agentic Skills — PASS.** Import flow is scripted
  (`terraform/import.sh`), not tribal knowledge; log events are documented with
  ready-made gcloud queries (`docs/LOGGING.md:75-88`).
- **IV. Continuous API Validation (Bruno) — PASS.** Slice 3b ran the FULL gate against
  real Firestore (67/67 then) — cloud wiring was proven with the same contract suite,
  not a separate smoke script; Slice 11 re-ran the full gate (84/199/12) to prove
  behavior unchanged.
- **V. Infrastructure-as-Code & Cost Gating — PASS.** This capability IS the gate's
  implementation: platform in terraform, `plan` clean, cost review ~$0/mo recorded in
  both the changelog and `docs/DEPLOYMENT.md:83-90`; the deliberate Cloud Run
  exclusion is documented with rationale (`terraform/main.tf:1-12`).

## Project Structure

### Documentation (this feature)

```text
specs/007-cloud-platform-ops/
├── spec.md
├── plan.md              # this file
├── research.md
├── data-model.md
├── quickstart.md
├── tasks.md
└── contracts/
    └── platform-contract.md
```

### Source Code (repository root)

```text
Dockerfile                     # Cloud Run image                         (S3b)
.dockerignore                  # build context = src/ + requirements     (S3b)
firebase.json + .firebaserc    # Hosting ** → Cloud Run rewrite          (S12)
public/.gitkeep                # intentionally empty hosting dir         (S12)
terraform/
├── versions.tf                # TF ≥1.5, google ~>6.0, local state      (S10)
├── variables.tf               # project/region/SA/schedule + poll_token (S10)
├── main.tf                    # APIs, Firestore, IAM, invoker, scheduler(S10)
├── outputs.tf                 # run URL, DB, scheduler, services        (S10)
└── import.sh                  # adopt pre-existing infra into state     (S10)
src/obs.py                     # structured logging foundation           (S11)
src/main.py:42-49              # configure_logging at import + loggers   (S11)
docs/DEPLOYMENT.md             # live-resource runbook                   (S3b→)
docs/LOGGING.md                # event catalog + queries                 (S11)
```

**Structure Decision**: platform-as-terraform / app-as-gcloud split with the service
as a data source — infra and app deploys can never fight over one resource.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Cloud Run service NOT terraform-managed | app deploys are `gcloud run deploy --source .` (Cloud Build) many times a week; terraform owning the service would drift/fight on every deploy | full terraform ownership rejected: env/image churn belongs to the app lifecycle; the data source still lets the scheduler wire the URL (`terraform/main.tf:55-60`) |
| Import-before-apply workflow | the infra pre-existed (Slice 3b was imperative); recreating live resources was unacceptable | greenfield apply rejected — it would duplicate/conflict; `import.sh` makes adoption reproducible |
| Hand-rolled logging module instead of a library | JSON-vs-text switching + Cloud Logging severity mapping is ~100 lines; zero deps is a standing goal | structlog/loguru rejected: dependency + config surface for a need this small (`src/obs.py:1-24`) |

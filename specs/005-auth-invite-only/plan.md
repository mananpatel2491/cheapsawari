# Implementation Plan: Invite-Only Access — Google Auth, Allowlist, Ownership

**Branch**: `retro/005-auth-invite-only` | **Date**: 2026-07-05 | **Spec**: [spec.md](./spec.md)

**Input**: As-built reconstruction from Slices 6 + 8 (2026-06-24) and 13 + 14
(2026-06-25).

## Summary

Browser-side Google Identity Services hands the page an ID token;
`src/auth.py:verify_google_credential` validates signature+audience offline
(google-auth) and returns the verified email, which is checked against the
`AllowedUserRepository` allowlist (admin always allowed) and stored in a signed
`__session` cookie (Starlette SessionMiddleware). Two FastAPI dependencies —
`require_user` (re-checks the allowlist per request) and `require_admin` — gate every
route. Slice 8 adds ownership: watches carry a server-assigned `owner_email`, all
per-watch routes resolve through `_owned_watch` (404 for others'), lists are scoped
unless admin. `AUTH_MODE=dev` provides a passwordless allowlist-gated login for local
and Bruno runs; prod hardening removed the dev form from static markup (13) and renamed
the cookie for Firebase Hosting (14).

## Technical Context

**Language/Version**: Python 3.13; FastAPI dependency injection for gates

**Primary Dependencies**: `google-auth` (offline ID-token verification),
`itsdangerous` (SessionMiddleware signing) (`requirements.txt:15-16`); GIS loaded
client-side from accounts.google.com (`src/web/login.html:79-88`)

**Storage**: allowlist via `AllowedUserRepository` — SQLite `allowed_users` table /
Firestore `allowed_users/{email}` (shares `WATCH_STORE`); session state lives in the
signed cookie only

**Testing**: Bruno `auth/` (16) + `ownership/` (14) suites in `AUTH_MODE=dev`;
in-process TestClient owner/invitee matrix (Slice 8 changelog)

**Target Platform**: Cloud Run behind Firebase Hosting (cookie constraint) + local dev

**Project Type**: web service — auth layer + two HTML pages (login, admin console)

**Performance Goals**: allowlist re-check per request = one PK lookup (doc get / SELECT 1)

**Constraints**: $0/mo (GIS free, Firestore free tier); no new infra; lazily imported
google-auth transport so dev runs don't need it (`src/auth.py:58-61`)

**Scale/Scope**: `src/auth.py` (~115 lines), `src/users/` package (~200), route gates,
login/admin pages

## Constitution Check

Gated against `.specify/memory/constitution.md` (distillation; `GEMINI.md` supreme).

- **I. Context-First Architecture Map — PASS.** `src/auth.py`, all `src/users/*`,
  login/admin pages mapped (`Project_Structure.md:40-44,54-55`); Slice 6/8/13/14 rows
  list files.
- **II. Pattern Reference Integrity — PASS.** Identity is a RESOLVED pattern:
  "Google Identity Services + signed `__session` cookie + Firestore allowlist; extend
  that stack, never revisit" (`.specify/memory/constitution.md:13`; PATTERNS.md
  Infrastructure Migration Advisory — Director arbitration recorded 2026-06-24,
  chosen over Firebase Auth and Cloud IAP).
- **III. Automated Maintenance via Agentic Skills — PASS.** No manual user state
  beyond the admin console; revocation is immediate by design (per-request re-check).
- **IV. Continuous API Validation (Bruno) — PASS.** Dedicated `auth/` and `ownership/`
  suites prove the 401/403/404 matrix, dev-mode exercisability, and revocation; full
  gate 97/242/13.
- **V. Infrastructure-as-Code & Cost Gating — PASS.** No new infra (GIS + existing
  Firestore); Slice 6/8 cost reviews $0. The OAuth client is console-managed and
  documented as a manual step with its gotcha (`docs/DEPLOYMENT.md:50-60`) — outside
  terraform scope by the same service/infra split as spec 007.

## Project Structure

### Documentation (this feature)

```text
specs/005-auth-invite-only/
├── spec.md
├── plan.md              # this file
├── research.md
├── data-model.md
├── quickstart.md
├── tasks.md
└── contracts/
    └── openapi-auth-admin.yaml
```

### Source Code (repository root)

```text
src/
├── auth.py                    # verification, session helpers, require_user/admin (S6)
├── users/
│   ├── base.py                # AllowedUserRepository ABC                        (S6)
│   ├── sqlite_store.py        # allowed_users table, idempotent upsert           (S6)
│   ├── firestore_store.py     # allowed_users/{email} docs                       (S6)
│   └── factory.py             # shares WATCH_STORE selection                     (S6)
├── main.py
│   ├── :65-71                 # SessionMiddleware, cookie __session              (S6; renamed S14)
│   ├── :125-231               # auth/config,me,google,dev,logout + admin CRUD    (S6)
│   ├── :270-279               # _owned_watch (404-not-403)                       (S8)
│   └── :304-306               # admin-vs-owner list scoping                      (S8)
└── web/
    ├── login.html             # GIS button; dev form built dynamically           (S6; hardened S13)
    └── admin.html             # owner console: add/list/revoke                   (S6)
```

**Structure Decision**: auth is a module of dependencies + a users/ repository package
mirroring the store seam — the gate composes into routes via `Depends`, keeping every
endpoint's auth posture visible at its decorator.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Allowlist re-checked on EVERY request | immediate revocation — a fired friend's cookie dies instantly | trusting the cookie until expiry rejected: revocation latency is the whole point of an allowlist; cost is one PK lookup |
| 404 (not 403) for another user's watch | existence non-disclosure between invitees | 403 rejected — it confirms the id exists (Slice 8 changelog states the choice) |
| A dev login endpoint in prod code | Bruno + local dev must exercise the real gate without an OAuth client | mocking auth in tests rejected (untested gate); mitigated by hard-404 unless `AUTH_MODE=dev` + allowlist still enforced |

---
description: "As-built task record for invite-only access (Google auth, allowlist, ownership, hardening)"
---

# Tasks: Invite-Only Access

As-built record — reconstructed 2026-07-05 from Slices 6/8 (2026-06-24) and 13/14
(2026-06-25). `[X]` = shipped; `[ ]` = genuinely open.

## Phase 1: Auth core (US1)

- [X] T001 [US1] `src/auth.py`: `verify_google_credential` (offline JWT + audience +
  email_verified), session helpers, `require_user`/`require_admin` dependencies
  (Slice 6)
- [X] T002 [US1] SessionMiddleware with signed HttpOnly cookie; `SESSION_SECRET`
  config (Slice 6; cookie renamed `__session` + Secure-on-Cloud-Run Slice 14)
- [X] T003 [US1] Routes: `/api/v1/auth/config|me|google|dev|logout`; page redirects to
  `/login` for `/` and `/admin` (Slice 6)
- [X] T004 [US1] `require_user` applied to every offers/watches/signal route; poll
  stays token-gated for the scheduler (Slice 6)

## Phase 2: Allowlist (US2)

- [X] T005 [US2] `src/users/` package: `AllowedUserRepository` ABC + SQLite upsert
  store + Firestore `allowed_users/{email}` store + WATCH_STORE-sharing factory
  (Slice 6)
- [X] T006 [US2] Admin API `GET/POST/DELETE /api/v1/admin/users` (owner-gated;
  400 on touching the owner; 404 on unknown revoke) + `/admin` console page (Slice 6)
- [X] T007 [US2] Per-request allowlist re-check → immediate revocation (Slice 6)
- [X] T008 [US2] Bruno `auth/` suite: 16 requests (gate 55/136 at Slice 6) (Slice 6)

## Phase 3: Ownership (US3)

- [X] T009 [US3] `Watch.owner_email` (server-assigned) + store column/field +
  migration + owner filter in `list_watches` (Slice 8)
- [X] T010 [US3] `_owned_watch` gate on get/put/delete/refresh/snapshots/signal —
  404-not-403; admin sees all; legacy ownerless = admin-only (Slice 8)
- [X] T011 [US3] Bruno `ownership/` suite: 14 requests, full admin/invitee matrix
  (gate 78/188/8) + in-process TestClient matrix (Slice 8)

## Phase 4: Production hardening (US4)

- [X] T012 [US4] `POST /api/v1/auth/dev` hard-404 unless `AUTH_MODE=dev`; still
  allowlist-gated in dev (Slice 6)
- [X] T013 [US4] Login page: dev form built dynamically ONLY when the server reports
  dev mode — absent from prod static markup (Slice 13)
- [X] T014 [US4] `__session` cookie fix for Firebase Hosting (forwards only that
  name); verified in-process + full Bruno gate 84/199/12 (Slice 14)
- [X] T015 Prod flip: `AUTH_MODE=google` + OAuth client + stable SESSION_SECRET live
  since 2026-06-24, rev cheapsawari-api-00005-dsk (`docs/DEPLOYMENT.md:27-39`)

## Open follow-ups (genuinely pending)

- [ ] T016 Inert dev-login JS remains in `login.html` (endpoint-gated; judged not
  worth server-side templating — Slice 13 changelog); revisit only if templating
  arrives for other reasons
- [ ] T017 Move auth secrets (`SESSION_SECRET`, `GOOGLE_CLIENT_ID`) to Secret Manager
  (optional hardening noted in `docs/DEPLOYMENT.md:100-101`)

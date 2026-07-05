# Feature Specification: Invite-Only Access — Google Auth, Allowlist, Ownership

**Feature Branch**: `retro/005-auth-invite-only` (as-built record — no branch created)

**Created**: 2026-07-05

**Status**: Shipped (Slice 6 auth+allowlist, 2026-06-24; Slice 8 per-user ownership,
2026-06-24; Slice 13 login hardening + Slice 14 `__session` fix, 2026-06-25)

**Input**: retro-spec conversion of Slices 6, 8, 13, 14 — the access posture of a
personal, invite-only tool.

## Why

The product goal is explicit: a personal, **invite-only** fare tool for the owner +
friends — not a public OTA. That demands (1) real identity ("Sign in with Google", no
passwords to manage), (2) an owner-managed allowlist so access is a deliberate grant,
(3) privacy between invitees — Slice 6 initially left watches global, so Slice 8 made
every watch private to its owner with the admin seeing all, and (4) production
hardening — the dev login vanished from prod markup (Slice 13) and sessions were fixed
behind Firebase Hosting, which forwards only a cookie named `__session` (Slice 14).

## User Scenarios & Testing

### User Story 1 - Only invited Google accounts get in (Priority: P1)

A visitor must sign in with Google; only the admin and allowlisted emails proceed —
everyone else is refused with a clear 403.

**Why this priority**: the gate is the product's security boundary; every data route
sits behind it.

**Independent Test**: `bruno/cheapsawari/auth/` (16 requests): no-session 401 → admin
login → invite → invitee login OK → stranger 403 → revoke → 404 on re-delete.

**Acceptance Scenarios**:

1. **Given** no session, **When** any offers/watches/signal route is called, **Then**
   401 (`require_user`, `src/auth.py:98-107`); the `/` and `/admin` pages redirect to
   `/login` (`src/main.py:92-93,107-108`).
2. **Given** a Google ID token, **When** POSTed to `/api/v1/auth/google`, **Then** the
   JWT signature and audience are verified offline against `GOOGLE_CLIENT_ID` and a
   verified email claim is required (`src/auth.py:48-73`); invalid → 401, not
   allowlisted → 403 (`src/main.py:150-159`).
3. **Given** a successful login, **Then** the email is stored in a signed HttpOnly
   session cookie and `auth.login outcome=ok` is logged (`src/auth.py:78-80`;
   `src/main.py:160-163`).
4. **Given** an allowlisted user whose access is revoked, **When** their next request
   arrives, **Then** 401 immediately — the allowlist is re-checked per request, a
   stale cookie cannot outlive removal (`src/auth.py:99-106`).

---

### User Story 2 - Owner manages the allowlist (Priority: P1)

Only `ADMIN_EMAIL` can list/add/revoke invited accounts, via the API and the `/admin`
console.

**Why this priority**: "invite-only" is operational only if inviting is easy and
exclusive to the owner.

**Independent Test**: Bruno `auth/admin_add_user.bru`, `admin_list_users.bru`,
`admin_delete_user.bru`, `invitee_admin_forbidden.bru`.

**Acceptance Scenarios**:

1. **Given** a non-admin session, **When** `/api/v1/admin/users` is called, **Then**
   403 (`require_admin`, `src/auth.py:110-114`).
2. **Given** the admin adds an email, **Then** the grant is idempotent (upsert
   refreshes added_by/added_at, `src/users/sqlite_store.py:62-72`;
   doc-id = lower-cased email on Firestore, `src/users/firestore_store.py:3-5,48-53`)
   and `auth.allowlist action=add` is logged (`src/main.py:204-216`).
3. **Given** the owner's own email, **When** added or removed, **Then** 400 — the
   bootstrap admin is implicit and irremovable (`src/main.py:212-213,226-227`).

---

### User Story 3 - Watches are private per user; admin sees all (Priority: P1)

An invitee sees and can act on only their own watches; the admin sees everyone's;
someone else's watch id answers 404 — never 403.

**Why this priority**: Slice 6 left watches global — a privacy gap between friends;
Slice 8 is the fix and the chosen policy.

**Independent Test**: `bruno/cheapsawari/ownership/` (14 requests): full
admin/invitee matrix — invitee-sees-only-own, cross-user 404 on read+write,
admin-sees-all.

**Acceptance Scenarios**:

1. **Given** a watch created by user A, **When** user B GETs/PUTs/DELETEs/refreshes it,
   **Then** 404 so existence isn't leaked (`_owned_watch`, `src/main.py:270-279`).
2. **Given** the admin, **When** listing, **Then** all owners' watches (owner filter
   None); a normal user's list is scoped to their email (`src/main.py:304-306`).
3. **Given** creation, **Then** `owner_email` is server-assigned from the session —
   never client input (`src/main.py:292`; `src/models.py:172-174`).
4. **Given** legacy pre-Slice-8 watches (owner None), **Then** they are visible to the
   admin only (`src/models.py:173`; `_owned_watch` denies non-admins).
5. **Given** the scheduler poll, **Then** it stays global (owner filter None) — it
   exposes nothing to users (`src/poll.py:72`; Slice 8 changelog).

---

### User Story 4 - Dev-mode gate for local/tests, hardened prod (Priority: P2)

Locally and in Bruno, a passwordless email login exercises the same gate; in prod the
page shows only the Google button and the dev endpoint is a hard 404.

**Why this priority**: the gate must be testable without a real OAuth client, but must
add zero prod surface.

**Independent Test**: Bruno runs entirely in `AUTH_MODE=dev`; Slice 13 verified the
static `/login` markup has no form/input in google mode and `/auth/dev` → 404.

**Acceptance Scenarios**:

1. **Given** `AUTH_MODE != dev`, **When** `POST /api/v1/auth/dev`, **Then** 404
   (`src/main.py:173-174`).
2. **Given** dev mode, **Then** the login is still allowlist-gated — it grants nothing
   the admin didn't configure (`src/main.py:180-183`).
3. **Given** the prod login page, **Then** the dev email form is built dynamically in
   JS ONLY when the server reports mode=dev — it never exists in static markup
   (`src/web/login.html:48-51,89-107`; Slice 13).

### Edge Cases

- **Firebase Hosting cookie stripping (Slice 14)**: Hosting forwards ONLY a cookie
  named `__session`; the Starlette default name broke sign-in on cheapsawari.web.app
  while working on the raw Cloud Run URL. Fix: `session_cookie="__session"`, `Secure`
  only on Cloud Run (`K_SERVICE`) so local http dev still works
  (`src/main.py:57-71`). One-time effect: old cookies ignored → users sign in once
  more.
- **GIS origin gotcha**: any new serving domain must be added to the OAuth client's
  Authorized JavaScript origins by hand, or the button won't render and nothing
  reaches app logs (`docs/DEPLOYMENT.md:50-60`).
- **Session secret stability**: `SESSION_SECRET` must be stable across
  instances/restarts or sessions silently invalidate (`src/config.py:95-96`;
  `src/main.py:57-58`).
- **Emails normalized lower-case everywhere** (`src/auth.py:36,42,70`;
  `src/main.py:175,209,225`).

## Requirements

### Functional Requirements

- **FR-001**: Every offers/watches/signal route MUST depend on `require_user`; admin
  routes on `require_admin` (401 vs 403 split) (`src/main.py:237,283,301…`;
  `src/auth.py:98-114`).
- **FR-002**: Google credential verification MUST be offline JWT verification
  (google-auth) against the configured audience with `email_verified` required
  (`src/auth.py:60-73`).
- **FR-003**: The allowlist MUST live behind `AllowedUserRepository`
  (SQLite/Firestore selected by the same `WATCH_STORE`)
  (`src/users/base.py:14-31`; `src/users/factory.py:15-29`).
- **FR-004**: `ADMIN_EMAIL` MUST be always-allowed, the only allowlist manager, and
  never stored/removed as an allowlist row (`src/auth.py:39-45`;
  `src/users/base.py:3-6`; `src/main.py:212-213,226-227`).
- **FR-005**: Per-watch routes MUST resolve through `_owned_watch` with 404-not-403
  semantics; list scoping owner vs admin (`src/main.py:270-279,304-306`).
- **FR-006**: The session MUST be a signed HttpOnly cookie named `__session`,
  Secure-on-Cloud-Run only, SameSite=lax (`src/main.py:65-71`).
- **FR-007**: Auth decisions MUST emit structured events (`auth.login` ok/denied with
  reason, `auth.logout`, `auth.allowlist` add/remove) (`src/main.py:147-162,177-186,
  195,215,230`; `docs/LOGGING.md:23`).

### Key Entities

- **SessionUser**: `{email, is_admin}` resolved per request (`src/models.py:261-265`).
- **AllowedUser**: `{email (PK, lower-cased), added_by, added_at}`
  (`src/models.py:253-258`).
- **AddUserRequest**: admin grant input (`src/models.py:247-250`).

## Success Criteria

- **SC-001**: Bruno `auth/` (16 req) + `ownership/` (14 req) suites green in
  `AUTH_MODE=dev` — gate totals grew 55/136 (Slice 6) → 78/188/8 (Slice 8); inside
  today's 97/242/13.
- **SC-002**: Live in prod since 2026-06-24 (rev cheapsawari-api-00005-dsk):
  `AUTH_MODE=google`, real OAuth Web client, admin allowlist in Firestore
  (`docs/DEPLOYMENT.md:27-39`).
- **SC-003**: Slice 14 verified: Set-Cookie name `__session`, session round-trips →
  `/auth/me` 200 through Hosting; diagnosed entirely from Slice-11 structured logs
  (changelog 2026-06-25).

## Assumptions

- Google Identity Services (not Firebase Auth SDK) — the deliberate Slice-6 choice to
  keep one $0 FastAPI service; cost = manual OAuth-origin management
  (`docs/DEPLOYMENT.md:50-60`; PATTERNS.md "Resolved — Identity").
- Invitees have Google accounts (Gmail) — acceptable for owner + friends.
- The poll endpoint intentionally stays outside session auth (machine caller;
  token-gated — spec 003).

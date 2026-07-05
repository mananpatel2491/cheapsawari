# Research: Invite-Only Access — Google Auth, Allowlist, Ownership

As-built record — decisions reconstructed 2026-07-05 from Slice 6/8/13/14 changelog
rows, PATTERNS.md, and docs/DEPLOYMENT.md.

## Decision 1 — Google Identity Services directly (Director arbitration, 2026-06-24)

**Choice**: GIS client-side button → ID token → offline google-auth verification →
signed session cookie + Firestore allowlist (PATTERNS.md "Resolved — Identity").
**Why**: keeps the single $0 Cloud Run FastAPI service — no Firebase web SDK, no
managed-auth infra; passwordless for users (their Google account IS the identity, which
also gives email alerts a guaranteed-real recipient, spec 004).
**Rejected**: Firebase Auth (SDK + broker domain; heavier), Cloud IAP (cost/complexity
for a personal app), password auth (secret management burden).
**Known cost**: GIS validates the page origin against the OAuth client's *manual*
Authorized JavaScript origins list — every new serving domain breaks sign-in until
added, with no app-side log trace (`docs/DEPLOYMENT.md:50-60`).

## Decision 2 — Allowlist over open-with-roles

**Choice**: explicit `allowed_users` store; admin always allowed and irremovable; all
other access is an explicit grant (`src/users/base.py:3-6`; `src/main.py:212-213`).
**Why**: product goal is invite-only for friends — deny-by-default is the posture;
re-check per request makes revocation instant (`src/auth.py:99-106`).
**Rejected**: domain-wide allow (not everyone is on one domain), role tables (only two
roles exist: owner and invitee — `is_admin` is a config comparison,
`src/auth.py:33-36`).

## Decision 3 — dev/google mode split, hard-404 dev endpoint

**Choice**: `AUTH_MODE=dev` enables `POST /api/v1/auth/dev` (email only, allowlist
still enforced); any other mode 404s it (`src/main.py:166-187`).
**Why**: the gate must be exercisable by Bruno and local dev without a real OAuth
client, yet the endpoint must be unreachable — not merely forbidden — in prod.
**Hardening (Slice 13)**: the dev form was also removed from the login page's static
markup, built dynamically only when `/api/v1/auth/config` reports dev mode
(`src/web/login.html:48-51,89-107`); a few lines of inert endpoint-gated dev JS remain
(judged not worth server-side templating for a $0 app — changelog 2026-06-25).

## Decision 4 — Per-user ownership with admin-sees-all, 404 semantics (Slice 8)

**Choice**: server-assigned `owner_email` on the watch; `_owned_watch` gates every
per-watch route; someone else's watch → 404 so existence isn't leaked; admin bypasses;
legacy ownerless watches admin-only (`src/main.py:270-279`; `src/models.py:172-174`).
**Why**: Slice 6 shipped watches global — every signed-in friend saw everyone's trips
(privacy gap, fixed same day the gap was identified); "private per user, admin sees
all" was the chosen policy.
**Rejected**: sharing/teams (needless for the product), 403 responses (id oracle).

## Decision 5 — `__session` cookie name (Slice 14, production bug fix)

**Context**: sign-in succeeded server-side (`auth.login outcome=ok`, HTTP 200) but
users bounced back to `/login` on cheapsawari.web.app — Firebase Hosting forwards ONLY
a cookie named `__session` to the backend and strips all others; the Starlette default
`session` cookie never reached Cloud Run through Hosting (raw Cloud Run URL worked).
**Choice**: rename the SessionMiddleware cookie to `__session` (works on both URLs);
`https_only` only when `K_SERVICE` is set so local http dev/Bruno still work
(`src/main.py:60-71`).
**Notable**: diagnosed entirely from Slice-11 structured logs; one-time cost = one
re-login for existing sessions.

## Decision 6 — Allowlist rides the watch-store backend

**Choice**: `AllowedUserRepository` selected by the SAME `WATCH_STORE` setting
(`src/users/factory.py:1-5`).
**Why**: one backend to configure/operate; email-as-document-id makes membership a
single doc get and adds naturally idempotent (`src/users/firestore_store.py:3-5`).
**Rejected**: a separate USERS_STORE knob (config surface without a use case).

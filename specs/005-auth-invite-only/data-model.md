# Data Model: Invite-Only Access

## Session (transport — signed cookie, nothing server-side)

| Aspect | Value |
|---|---|
| Cookie name | `__session` (Firebase-Hosting-forwardable; `src/main.py:68`) |
| Contents | signed payload `{"email": "<lower-cased email>"}` (`src/auth.py:26,78-80`) |
| Flags | HttpOnly (SessionMiddleware default), `Secure` only when `K_SERVICE` set, `SameSite=lax` (`src/main.py:69-70`) |
| Signing key | `SESSION_SECRET` — must be stable across instances/restarts (`src/config.py:95-96,100`) |
| Resolution | `current_user(request)` → `SessionUser{email, is_admin}` (`src/auth.py:88-93`) |

## Allowlist storage (`AllowedUserRepository`)

**SQLite** (`src/users/sqlite_store.py:11-17`):

```
allowed_users(email TEXT PRIMARY KEY, added_by TEXT NOT NULL, added_at TEXT NOT NULL)
```

`add_user` = `INSERT … ON CONFLICT(email) DO UPDATE` (idempotent, :62-72).

**Firestore** (`src/users/firestore_store.py:15,48-53`):

```
allowed_users/{email}    # doc id = lower-cased email; fields: added_by, added_at
```

`is_allowed` = single doc-exists check (:45-46).

The admin (`ADMIN_EMAIL`) is deliberately NOT a row — always-allowed by config
comparison (`src/users/base.py:3-6`; `src/auth.py:39-45`).

## Watch ownership fields (stored with the watch — spec 002)

| Field | Rule |
|---|---|
| `owner_email` | server-assigned at create from the session (`src/main.py:292`); never client input; None on legacy watches → admin-visible only (`src/models.py:172-174`) |
| list scoping | `owner_email=None` filter = all (admin/scheduler); else exact match (`src/store/base.py:87-94`) |

## Transport models (`src/models.py:247-265`)

- `AddUserRequest {email}` — admin grant input.
- `AllowedUser {email, added_by, added_at}` — allowlist row.
- `SessionUser {email, is_admin}` — the authenticated caller; also `/auth/me`'s shape.

## Config / env keys (`src/config.py:87-100,134-137`)

| Key | Default | Notes |
|---|---|---|
| `AUTH_MODE` | `dev` | `google` in prod; gates the dev endpoint + login-page rendering |
| `GOOGLE_CLIENT_ID` | unset | ID-token audience; required for google mode |
| `ADMIN_EMAIL` | `mpatel.mi24@gmail.com` | bootstrap owner (lower-cased comparisons) |
| `SESSION_SECRET` | `dev-insecure-session-secret-change-me` | MUST be overridden in prod |

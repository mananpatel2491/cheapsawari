# Full-Stack Function Mapping

This document maps frontend UI components to their respective backend API endpoints. Maintain this file to ensure architectural traceability.

| Frontend Component | Action | Backend Endpoint / Function | Documentation/Contract |
| :--- | :--- | :--- | :--- |
| *(Slice 5 — dashboard, TBD)* | Fetch cheapest fare for a route+date | `GET /api/v1/offers/cheapest` → `src/providers` `FareProvider.get_cheapest_offer` | `bruno/cheapsawari/offers/cheapest_deterministic.bru` |
| *(infra / probe)* | Liveness + active provider | `GET /health` | `bruno/cheapsawari/offers/health.bru` |
| *(Slice 5 — add-watch form, TBD)* | Register / list / delete a tracked route | `POST` `GET` `DELETE /api/v1/watches` → `src/store` `WatchRepository` | `bruno/cheapsawari/watches/create_watch.bru` |
| *(Slice 5 — dashboard, TBD)* | Poll a watch now / show price history | `POST .../{id}/refresh`, `GET .../{id}/snapshots` → `WatchRepository.add_snapshot` / `list_snapshots` | `bruno/cheapsawari/watches/refresh_watch.bru`, `.../list_snapshots.bru` |
| `web/dashboard.html` add-watch form (Slice 7) | Track a one-way or round-trip with per-leg date flexibility | `POST /api/v1/watches` (trip_type / return_date / depart_flex_days / return_flex_days) → refresh prices the trip via `src/trip` `price_watch_trip` | `bruno/cheapsawari/roundtrip/create_roundtrip.bru`, `.../refresh_roundtrip.bru` |
| `web/dashboard.html` (Slice 8) | Each user sees/manages only their own watches; admin sees all | `GET/DELETE /api/v1/watches[...]` scoped by `owner_email` via `src/main` `_owned_watch` (404 on others') | `bruno/cheapsawari/ownership/invitee_sees_only_own.bru`, `.../admin_sees_all.bru` |
| Cloud Scheduler `cheapsawari-daily-poll` (LIVE) | Poll all active watches daily (quota-capped) | `POST /api/v1/poll` → `src/poll` `poll_active_watches` → `src/store/firestore_store.py` | `bruno/cheapsawari/poll/poll_run.bru` |
| `web/login.html` (Slice 6) | Read sign-in mode; sign in (Google ID token or dev email) | `GET /api/v1/auth/config`, `POST /api/v1/auth/google` \| `/auth/dev` → `src/auth` `verify_google_credential` / `login_session` | `bruno/cheapsawari/auth/dev_login_admin.bru`, `.../auth_config_public.bru` |
| `web/dashboard.html` + `web/admin.html` (Slice 6) | Show signed-in user; sign out | `GET /api/v1/auth/me`, `POST /api/v1/auth/logout` → `src/auth` `require_user` / `logout_session` | `bruno/cheapsawari/auth/me_admin.bru`, `.../logout_owner.bru` |
| `web/admin.html` (Slice 6) | Owner manages the access allowlist | `GET` `POST /api/v1/admin/users`, `DELETE /api/v1/admin/users/{email}` → `src/users` `AllowedUserRepository` (owner-gated by `require_admin`) | `bruno/cheapsawari/auth/admin_add_user.bru`, `.../admin_list_users.bru`, `.../admin_delete_user.bru` |

## Maintenance Rules
1. **Add**: When creating a new endpoint or component connection.
2. **Update**: When an endpoint signature or data structure changes.
3. **Delete**: When a feature is decommissioned.
4. **Audit**: Run regular cross-checks to ensure no "Ghost Endpoints" exist.
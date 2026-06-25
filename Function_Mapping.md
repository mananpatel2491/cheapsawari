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
| `web/dashboard.html` multi-city builder (Slice 9) | Track an N-leg trip (transfer hub / port-of-entry as legs) | `POST /api/v1/watches` (trip_type=multi_city, legs[]) → `src/trip` `price_watch_trip` over `Watch.resolved_legs` | `bruno/cheapsawari/multicity/create_multicity.bru`, `.../refresh_multicity.bru` |
| `web/dashboard.html` Details modal (Slice 15) | View a tracking's full config — every configured leg (incl. multi-city), trip type, cabin, created, snapshot count, latest total, signal | client-side from `GET /api/v1/watches` + `.../snapshots` + `.../signal` (legs mirror `Watch.resolved_legs`); no new endpoint | `bruno/cheapsawari/watches/get_watch.bru`, `.../list_snapshots.bru` |
| `web/dashboard.html` Edit (Slice 15) | Edit an existing tracking in place (route/dates/flex/cabin/trip-type/legs) | `PUT /api/v1/watches/{id}` → `src/store` `WatchRepository.update_watch` (preserves id/created_at/owner/active + history) | `bruno/cheapsawari/update/edit_to_roundtrip.bru`, `.../edit_to_multicity.bru`, `.../edit_same_city_400.bru` |
| `web/dashboard.html` per-card Refresh (Slice 16) | Fetch the latest fare for one tracking now (records a snapshot) | `POST /api/v1/watches/{id}/refresh` → `src/trip` `price_watch_trip` → `WatchRepository.add_snapshot` | `bruno/cheapsawari/watches/refresh_watch.bru` |
| `web/dashboard.html` Alert −% field (Slice 16) | Set a per-watch notify threshold; detection/alert uses it | `POST`/`PUT /api/v1/watches` (`alert_threshold_pct`) → `src/signal` `detect_reopening` (per-watch threshold) | `bruno/cheapsawari/notify/get_signal_custom_threshold.bru` |
| `web/dashboard.html` theme button (Slice 16) | Toggle among 5 color skins (client-only, localStorage) | none (CSS `data-theme` on `<html>`) | n/a (UI-only) |
| Scheduled poll → email (Slice 16) | Email the watch owner when a bucket reopens | `src/poll` `poll_active_watches` → `src/alerts` `EmailAlertChannel.send(signal, recipient=owner_email)` (ALERT_CHANNEL=email) | in-process (SMTP) |
| Cloud Scheduler `cheapsawari-daily-poll` (LIVE) | Poll all active watches daily (quota-capped) | `POST /api/v1/poll` → `src/poll` `poll_active_watches` → `src/store/firestore_store.py` | `bruno/cheapsawari/poll/poll_run.bru` |
| `web/login.html` (Slice 6) | Read sign-in mode; sign in (Google ID token or dev email) | `GET /api/v1/auth/config`, `POST /api/v1/auth/google` \| `/auth/dev` → `src/auth` `verify_google_credential` / `login_session` | `bruno/cheapsawari/auth/dev_login_admin.bru`, `.../auth_config_public.bru` |
| `web/dashboard.html` + `web/admin.html` (Slice 6) | Show signed-in user; sign out | `GET /api/v1/auth/me`, `POST /api/v1/auth/logout` → `src/auth` `require_user` / `logout_session` | `bruno/cheapsawari/auth/me_admin.bru`, `.../logout_owner.bru` |
| `web/admin.html` (Slice 6) | Owner manages the access allowlist | `GET` `POST /api/v1/admin/users`, `DELETE /api/v1/admin/users/{email}` → `src/users` `AllowedUserRepository` (owner-gated by `require_admin`) | `bruno/cheapsawari/auth/admin_add_user.bru`, `.../admin_list_users.bru`, `.../admin_delete_user.bru` |

## Maintenance Rules
1. **Add**: When creating a new endpoint or component connection.
2. **Update**: When an endpoint signature or data structure changes.
3. **Delete**: When a feature is decommissioned.
4. **Audit**: Run regular cross-checks to ensure no "Ghost Endpoints" exist.
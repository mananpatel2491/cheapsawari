# Storage Contract: WatchRepository seam

Both stores must satisfy `src/store/base.py:58-125`; either can back the whole app via
`WATCH_STORE` (sqlite | firestore).

## Behavioral guarantees

| Operation | Guarantee |
|---|---|
| `create_watch(data, owner_email)` | uuid4 id, `active=true`, UTC `created_at`, owner stamped server-side |
| `get_watch(id)` | `None` when missing (ownership is the API's job) |
| `update_watch(id, data)` | replaces trip-definition fields ONLY; preserves id/created_at/owner_email/active + snapshots; raises `WatchNotFoundError` when missing |
| `list_watches(active_only, owner_email)` | newest first; `owner_email=None` = all owners (scheduler + admin view) |
| `delete_watch(id)` | cascades snapshots (SQLite FK `ON DELETE CASCADE`, sqlite_store.py:58; explicit subcollection loop, firestore_store.py:191-193); returns existed-bool |
| `add_snapshot(id, legs, total, trip_type)` | assembles via shared `build_snapshot` (base.py:14-55); raises `WatchNotFoundError` |
| `list_snapshots(id, limit)` | newest first; raises `WatchNotFoundError` |

## Physical layouts

**SQLite** (default, `SQLITE_PATH`): tables `watches` + `snapshots` with
`idx_snapshots_watch(watch_id, observed_at)`; ISO-string dates; JSON-string legs;
pragma-diff `ALTER TABLE` migrations for pre-existing DBs
(`src/store/sqlite_store.py:26-104`).

**Firestore** (prod): `watches/{watch_id}` docs + `watches/{watch_id}/snapshots/{snap_id}`
subcollection; native timestamps for datetimes, ISO strings for dates, array-of-maps
legs; Python-side filter/sort (no composite indexes)
(`src/store/firestore_store.py:4-16`).

## Allowlist storage (shared backend — spec 005)

The `AllowedUserRepository` seam (`src/users/base.py`) rides the same `WATCH_STORE`
selection: SQLite table `allowed_users(email PK, added_by, added_at)`
(`src/users/sqlite_store.py:11-17`) / Firestore `allowed_users/{email}` where the
lower-cased email is the document id (`src/users/firestore_store.py:3-5,15`).

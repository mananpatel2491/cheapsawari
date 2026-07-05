# Data Model: Watch Tracking

## Domain models (`src/models.py`)

### TripLeg (`src/models.py:26-44`)
| Field | Type | Rule |
|---|---|---|
| `origin` / `destination` | str | upper-cased; must differ per leg (validator :38-44) |
| `date` | date | earliest date if flexible |
| `flex_days` | int | 0..21 (`MAX_FLEX_DAYS`, :21) |

### WatchCreate (`src/models.py:77-163`)
| Field | Type | Notes |
|---|---|---|
| `origin` / `destination` / `departure_date` | optional | required for flat shapes; DERIVED from first/last leg for multi_city (:124-127) |
| `cabin` | str = "ECONOMY" | |
| `trip_type` | str = "one_way" | one_way \| round_trip \| multi_city (:17,116-117) |
| `return_date` | date \| None | required for round_trip; ≥ departure_date (:139-143) |
| `depart_flex_days` / `return_flex_days` | int 0..21 | zeroed where not applicable |
| `legs` | list[TripLeg] \| None | 2..6 for multi_city (:119-123); nulled for flat shapes (:138) |
| `alert_threshold_pct` | float \| None, 1..90 | Slice 16 per-watch alert preference (:109-112; used in spec 003) |

`resolved_legs` property (:149-163): one_way → 1 leg, round_trip → 2 (return =
destination→origin), multi_city → the legs list.

### Watch (`src/models.py:166-174`) = WatchCreate + identity
`id` (uuid4 str), `active` (bool, default true), `created_at` (UTC), `owner_email`
(str | None; server-assigned, Slice 8 — None on legacy rows → admin-visible only).

### PriceSnapshot / SnapshotLeg (`src/models.py:177-213`)
`price` = trip total; `legs[]` = canonical per-leg breakdown (Slice 9);
`outbound_price/outbound_date/return_price/return_date` = Slice-7 convenience fields;
plus currency/cabin/fare_basis/carrier/provider/observed_at from the head leg
(assembled by `build_snapshot`, `src/store/base.py:14-55`).

## SQLite layout (`src/store/sqlite_store.py:26-61`)

```
watches(id PK, origin, destination, departure_date, cabin, active, created_at,
        trip_type DEFAULT 'one_way', return_date, depart_flex_days, return_flex_days,
        owner_email, legs_json, alert_threshold_pct)
snapshots(id PK, watch_id FK→watches ON DELETE CASCADE, price, currency, cabin,
          fare_basis, carrier, provider, observed_at,
          outbound_price, outbound_date, return_price, return_date, legs_json)
idx_snapshots_watch ON snapshots(watch_id, observed_at)
```

Dates/datetimes as ISO-8601 strings; legs as JSON strings (`_dump_legs`, :22-24);
migrations table at :66-83 (columns added per Slice 7/8/9/16 with pragma diff).

## Firestore layout (`src/store/firestore_store.py:4-8,115-131,210-225`)

```
watches/{watch_id}                       # same fields; created_at native timestamp,
                                         # dates ISO strings, legs = array of maps
watches/{watch_id}/snapshots/{snap_id}   # snapshot fields; observed_at native timestamp
```

No cascade — `delete_watch` deletes the subcollection explicitly (:187-195);
`list_watches` filters/sorts in Python (:177-185).

## Config / env keys

| Key | Default | Used at |
|---|---|---|
| `WATCH_STORE` | `sqlite` | `src/store/factory.py:16-24` |
| `SQLITE_PATH` | `cheapsawari.db` | `src/config.py:59,117` |
| `GOOGLE_CLOUD_PROJECT` / `GCP_PROJECT` | unset (ADC inference) | `src/config.py:118-119` |

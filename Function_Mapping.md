# Full-Stack Function Mapping

This document maps frontend UI components to their respective backend API endpoints. Maintain this file to ensure architectural traceability.

| Frontend Component | Action | Backend Endpoint / Function | Documentation/Contract |
| :--- | :--- | :--- | :--- |
| *(Slice 5 — dashboard, TBD)* | Fetch cheapest fare for a route+date | `GET /api/v1/offers/cheapest` → `src/providers` `FareProvider.get_cheapest_offer` | `bruno/cheapsawari/offers/cheapest_deterministic.bru` |
| *(infra / probe)* | Liveness + active provider | `GET /health` | `bruno/cheapsawari/offers/health.bru` |
| *(Slice 5 — add-watch form, TBD)* | Register / list / delete a tracked route | `POST` `GET` `DELETE /api/v1/watches` → `src/store` `WatchRepository` | `bruno/cheapsawari/watches/create_watch.bru` |
| *(Slice 5 — dashboard, TBD)* | Poll a watch now / show price history | `POST .../{id}/refresh`, `GET .../{id}/snapshots` → `WatchRepository.add_snapshot` / `list_snapshots` | `bruno/cheapsawari/watches/refresh_watch.bru`, `.../list_snapshots.bru` |

## Maintenance Rules
1. **Add**: When creating a new endpoint or component connection.
2. **Update**: When an endpoint signature or data structure changes.
3. **Delete**: When a feature is decommissioned.
4. **Audit**: Run regular cross-checks to ensure no "Ghost Endpoints" exist.
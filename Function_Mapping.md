# Full-Stack Function Mapping

This document maps frontend UI components to their respective backend API endpoints. Maintain this file to ensure architectural traceability.

| Frontend Component | Action | Backend Endpoint / Function | Documentation/Contract |
| :--- | :--- | :--- | :--- |
| *ExampleComponent.tsx* | *Fetch Data* | *GET /api/v1/data* | *bruno/collections/data/get_data.bru* |

## Maintenance Rules
1. **Add**: When creating a new endpoint or component connection.
2. **Update**: When an endpoint signature or data structure changes.
3. **Delete**: When a feature is decommissioned.
4. **Audit**: Run regular cross-checks to ensure no "Ghost Endpoints" exist.
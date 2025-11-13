# Enersystems_QBR_System_2025_v3

## Overview
This version (v3) is the **final unified documentation and implementation package** for the Enersystems QBR Platform.  
It includes every project file from:
1. The **original 12-file QBR Web Dashboard project**,  
2. The **expanded PostgreSQL backend architecture**, and  
3. The **data model and data shape definitions** for complete backend ↔ frontend consistency.

## Folder Structure
| Folder | Description | Primary AI |
|---------|--------------|-------------|
| `backend/` | Database logic, ETL collectors, API layer, schema, and QBR data models | Database AI |
| `frontend/` | Dashboard logic, UI templates, data shape contracts, and rendering | Dashboard AI |
| `shared/` | Common architecture, definitions, and manifest | Both AIs |

## AI Collaboration Rules
- Frontend communicates only with backend REST APIs (never vendor APIs).  
- Backend owns all schemas, data ETL, and metric logic.  
- Shared `.env` (`/opt/shared-secrets/api-secrets.env`) handles credentials.  
- Data flows as **JSON shapes defined in `DATA_SHAPE_FRONTEND.md`**,  
  sourced from **tables in `DATA_MODEL_BACKEND.md`**.  
- Manual refresh flows: frontend → backend `/api/qbr/*` or `/api/collectors/run`.
- All communication uses HTTPS; authentication via `X-API-Key`.

## Recommended Reading Order
### Shared
1. `shared/QBR_DEFINITION.md`
2. `shared/SYSTEM_ARCHITECTURE.md`
3. `shared/BACKEND_API_SPEC.md`

### Backend
4. `backend/DATA_MODEL_BACKEND.md`
5. `backend/IMPLEMENTATION_PLAN_BACKEND.md`

### Frontend
6. `frontend/DATA_SHAPE_FRONTEND.md`
7. `frontend/IMPLEMENTATION_PLAN_FRONTEND.md`

## Integration Summary
```
+-------------------+        REST API        +--------------------+
| Dashboard (Flask) | <--------------------> | Backend (Flask API) |
| - Bootstrap / JS  |                       | - PostgreSQL schema |
| - Chart.js Visuals|                       | - Collectors / ETL  |
| - Uses DATA_SHAPE |                       | - Uses DATA_MODEL   |
+-------------------+                        +--------------------+
          ↑                                              ↑
          |                                              |
          +--------------- Shared Secrets ---------------+
```

## Maintenance
- **Version**: 3.0 (2025-11-10)  
- **Maintainers**: Database AI & Dashboard AI  
- **Deployment**: Ubuntu DMZ (LAN-only access)  
- **Future Work**: Add M365 SSO, expand historical data

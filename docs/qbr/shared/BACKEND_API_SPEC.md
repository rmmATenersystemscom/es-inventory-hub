# Backend API Specification

**Base URL:** `https://db-api.enersystems.com:5400/api/qbr`

### Authentication
Headers:
```
X-API-Key: <secret>
Content-Type: application/json
```

### Endpoints
| Method | Endpoint | Description |
|---------|-----------|-------------|
| GET | `/metrics/monthly` | Get monthly metrics |
| GET | `/metrics/quarterly` | Get quarterly metrics |
| GET | `/smartnumbers` | Return SmartNumbers KPIs |
| GET | `/thresholds` | Get thresholds |
| POST | `/thresholds` | Update thresholds |
| GET | `/periods` | List reporting periods |
| POST | `/refresh` | Trigger ETL refresh |
| GET | `/refresh/status/<batch_id>` | Refresh progress |

**Example Response:**
```json
{"period":"2025-01","metrics":[{"name":"Endpoints Managed","value":762}]}
```

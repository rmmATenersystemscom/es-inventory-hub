# M365 Usage Dashboard API - Dashboard AI Reference

## Overview

This API provides M365 user and license data for the M365 Usage Dashboard. It distinguishes between **ES Users** (users with Exchange mailboxes) and **M365 Licensed Users** (all users with any M365 license).

## Connection Details

| Setting | Value |
|---------|-------|
| **Hostname** | `db-api.enersystems.com` |
| **IP Address** | `192.168.4.246` |
| **Port** | `5400` (NOT 443!) |
| **Protocol** | HTTPS |
| **Base URL** | `https://db-api.enersystems.com:5400` |
| **Authentication** | None required |
| **SSL Certificate** | Valid Let's Encrypt certificate for `db-api.enersystems.com` |

### CRITICAL Configuration Notes

1. **Port 5400 is required** - Do NOT use port 443. The API runs on port 5400.
   - WRONG: `https://db-api.enersystems.com/api/m365/summary`
   - CORRECT: `https://db-api.enersystems.com:5400/api/m365/summary`

2. **Use hostname, not IP** - The SSL certificate is for `db-api.enersystems.com`, not `192.168.4.246`.
   - WRONG: `https://192.168.4.246:5400/api/m365/summary` (TLS mismatch)
   - CORRECT: `https://db-api.enersystems.com:5400/api/m365/summary`

3. **If DNS doesn't resolve**, add this to `/etc/hosts`:
   ```
   192.168.4.246  db-api.enersystems.com
   ```

### Test Command
```bash
curl -s "https://db-api.enersystems.com:5400/api/m365/summary" | jq '.status'
```
Expected output: `"success"`

## Purpose

- Display organization-level user counts in the M365 Usage Dashboard table
- Provide drill-down user details per organization
- Export full dataset for CSV/Excel reporting
- Distinguish between ES Users (email) and total M365 licensed users

## Endpoints

### GET /api/m365/summary

Returns organization-level summary counts for the dashboard table.

```
GET /api/m365/summary
```

**Authentication:** None required

### GET /api/m365/users

Returns detailed user list for a specific organization.

```
GET /api/m365/users?org={organization_name}
```

**Authentication:** None required

### GET /api/m365/export

Returns full dataset for CSV/Excel export.

```
GET /api/m365/export?format={format}&sort={sort_field}
```

**Authentication:** None required

## Query Parameters

### /api/m365/summary

No parameters required.

### /api/m365/users

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `org` | string | Yes | - | Organization name (exact match) |

### /api/m365/export

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `format` | string | No | `json` | Output format: `json` or `csv` |
| `sort` | string | No | `organization_name` | Sort by: `organization_name`, `user_principal_name`, or `display_name` |

## Response Structure

### /api/m365/summary

```json
{
  "status": "success",
  "organizations": [
    {
      "organization_name": "Acme Corp",
      "es_user_count": 45,
      "m365_licensed_user_count": 52
    }
  ],
  "totals": {
    "total_organizations": 38,
    "total_es_users": 579,
    "total_m365_licensed_users": 662
  },
  "last_collected": "2026-01-21T00:00:00Z",
  "metadata": {
    "query_time_ms": 34
  }
}
```

### /api/m365/users

```json
{
  "status": "success",
  "organization": "Acme Corp",
  "users": [
    {
      "user_principal_name": "john.doe@acmecorp.com",
      "display_name": "John Doe",
      "licenses": "Microsoft 365 Business Premium",
      "has_email_license": true
    }
  ],
  "total_users": 1
}
```

### /api/m365/export (JSON)

```json
{
  "status": "success",
  "data": [
    {
      "organization_name": "Acme Corp",
      "user_principal_name": "john.doe@acmecorp.com",
      "display_name": "John Doe",
      "licenses": "Microsoft 365 Business Premium",
      "has_email_license": true
    }
  ],
  "total_records": 1,
  "last_collected": "2026-01-21T00:00:00Z"
}
```

### /api/m365/export (CSV)

```csv
organization_name,user_principal_name,display_name,licenses,has_email_license
Acme Corp,john.doe@acmecorp.com,John Doe,Microsoft 365 Business Premium,true
```

## Field Definitions

| Field | Type | Description |
|-------|------|-------------|
| `organization_name` | string | Tenant display name |
| `es_user_count` | integer | Users with Exchange mailbox licenses |
| `m365_licensed_user_count` | integer | All users with any M365 license |
| `user_principal_name` | string | User's UPN (email address) |
| `display_name` | string | User's display name |
| `licenses` | string | Comma-separated list of license names |
| `has_email_license` | boolean | `true` if user has an Exchange mailbox license |
| `last_collected` | string | ISO 8601 timestamp of last data collection |
| `total_users` | integer | Count of users in response |
| `total_records` | integer | Count of records in export |

## ES User Classification (has_email_license)

A user has `has_email_license = true` if ANY license matches these patterns:

| Include Pattern | Examples |
|-----------------|----------|
| `Microsoft 365 Business*` | Business Basic, Standard, Premium |
| `Microsoft 365 E*` | E3, E5 |
| `Microsoft 365 F*` | F1, F3 |
| `Office 365 E*` | E1, E3, E5 |
| `Office 365 F*` | F3 |
| `Exchange Online (Plan*` | Plan 1, Plan 2 |
| `Exchange Online Kiosk` | - |
| `Exchange Online Essentials` | - |

**Exclusions** (do NOT count as email license):

| Exclude Pattern | Examples |
|-----------------|----------|
| `Archiving` | Exchange Online Archiving |
| `Protection` | Exchange Online Protection |

## Error Responses

```json
{
  "status": "error",
  "error": "Error message description"
}
```

| HTTP Code | Condition |
|-----------|-----------|
| 400 | Missing required parameter (e.g., `org` not provided) |
| 404 | No data available or organization not found |

## Usage Examples

### Python - Fetch Summary

```python
import requests

BASE_URL = "https://db-api.enersystems.com:5400"

response = requests.get(
    f"{BASE_URL}/api/m365/summary",
    verify=False  # Self-signed cert
)
data = response.json()

for org in data["organizations"]:
    print(f"{org['organization_name']}: {org['es_user_count']} ES / {org['m365_licensed_user_count']} total")
```

### Python - Fetch Users for Organization

```python
import requests

BASE_URL = "https://db-api.enersystems.com:5400"

response = requests.get(
    f"{BASE_URL}/api/m365/users",
    params={"org": "Ener Systems"},
    verify=False
)
data = response.json()

for user in data["users"]:
    email_status = "ES User" if user["has_email_license"] else "No Email"
    print(f"{user['display_name']}: {email_status}")
```

### Bash - Export CSV

```bash
curl -k "https://db-api.enersystems.com:5400/api/m365/export?format=csv" -o m365_users.csv
```

### Bash - Test Connectivity

```bash
curl -k "https://db-api.enersystems.com:5400/api/m365/summary" | jq '.totals'
```

## Dashboard Use Cases

1. **Summary Table** - Use `/api/m365/summary` to populate the main dashboard table showing ES Users and M365 Licensed Users per organization

2. **User Drill-Down Modal** - Use `/api/m365/users?org={name}` when user clicks an organization to see individual user details

3. **CSV Export** - Use `/api/m365/export?format=csv` for the "Export to CSV" button

4. **Refresh Data** - Check `last_collected` field to display data freshness to users

## Data Freshness

- M365 data is collected daily at **23:00**
- The `last_collected` field indicates the snapshot date
- Data represents the state as of the most recent collection

---

**Version:** v1.38.9
**Last Updated:** January 23, 2026 03:01 UTC
**Maintainer:** ES Inventory Hub Team

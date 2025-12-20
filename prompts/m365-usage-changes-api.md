# M365 Usage Changes API - Dashboard AI Reference

## Overview

The M365 Usage Changes API enables tracking of Microsoft 365 user and license modifications across snapshot intervals. Use this API to identify user additions, removals, and license changes across all managed M365 tenants.

## Endpoints

### 1. Available Dates

```
GET /api/m365/available-dates
```

Returns a list of dates with M365 snapshot data, sorted in descending order (most recent first).

**Authentication:** Required (Microsoft OAuth via session cookie)

#### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `days` | integer | No | `90` | Number of days to look back (1-365) |

#### Response Structure

```json
{
  "success": true,
  "data": {
    "dates": ["2025-12-19", "2025-12-18", "2025-12-16"],
    "count": 23,
    "range": {
      "start": "2025-09-21",
      "end": "2025-12-20"
    }
  }
}
```

---

### 2. Usage Changes

```
GET /api/m365/usage-changes
```

Compares M365 user and license data between two snapshot dates, identifying all changes.

**Authentication:** Required (Microsoft OAuth via session cookie)

#### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `start_date` | string | Yes | - | Baseline date (YYYY-MM-DD format) |
| `end_date` | string | Yes | - | Comparison date (YYYY-MM-DD format) |
| `detail_level` | string | No | `summary` | `summary` or `full` |
| `organization_name` | string | No | - | Filter by organization name (partial match) |

#### Change Detection Categories

| Change Type | Description |
|-------------|-------------|
| `user_added` | User present in end_date snapshot but not in start_date |
| `user_removed` | User present in start_date snapshot but not in end_date |
| `license_added` | User exists in both snapshots but acquired new licenses |
| `license_removed` | User exists in both snapshots but lost licenses |

#### Response Structure (Summary Mode)

```json
{
  "success": true,
  "data": {
    "start_date": "2025-12-09",
    "end_date": "2025-12-19",
    "summary": {
      "start_total_users": 710,
      "end_total_users": 669,
      "net_user_change": -41,
      "start_total_licenses": 1842,
      "end_total_licenses": 1756,
      "net_license_change": -86,
      "changes": {
        "users_added": 5,
        "users_removed": 13,
        "licenses_added": 2,
        "licenses_removed": 35
      }
    },
    "by_organization": {
      "Acme Corp": {
        "start_user_count": 24,
        "end_user_count": 19,
        "user_change": -5,
        "changes": {
          "user_added": 0,
          "user_removed": 5,
          "license_added": 0,
          "license_removed": 19
        }
      }
    },
    "metadata": {
      "vendor_name": "Microsoft 365",
      "query_time_ms": 145,
      "detail_level": "summary",
      "data_retention_note": "User-level data available for historical snapshots"
    }
  }
}
```

#### Response Structure (Full Mode)

When `detail_level=full`, the response includes a `changes` object with detailed user information:

```json
{
  "success": true,
  "data": {
    "start_date": "2025-12-09",
    "end_date": "2025-12-19",
    "summary": { ... },
    "by_organization": { ... },
    "changes": {
      "user_added": [
        {
          "user_principal_name": "jsmith@acme.com",
          "organization_name": "Acme Corp",
          "display_name": "John Smith",
          "licenses": "Microsoft 365 Business Basic",
          "change_date": "2025-12-15"
        }
      ],
      "user_removed": [
        {
          "user_principal_name": "jdoe@acme.com",
          "organization_name": "Acme Corp",
          "display_name": "Jane Doe",
          "licenses": "Microsoft 365 Business Premium",
          "last_seen_date": "2025-12-09"
        }
      ],
      "license_added": [
        {
          "user_principal_name": "bwilson@acme.com",
          "organization_name": "Acme Corp",
          "display_name": "Bob Wilson",
          "from_licenses": "Microsoft 365 Business Basic",
          "to_licenses": "Microsoft 365 Business Basic, Microsoft 365 Business Premium",
          "licenses_added": ["Microsoft 365 Business Premium"],
          "licenses_removed": [],
          "change_date": "2025-12-12"
        }
      ],
      "license_removed": [
        {
          "user_principal_name": "alee@acme.com",
          "organization_name": "Acme Corp",
          "display_name": "Alice Lee",
          "from_licenses": "Microsoft 365 E3, Power BI Pro",
          "to_licenses": "Microsoft 365 E3",
          "licenses_added": [],
          "licenses_removed": ["Power BI Pro"],
          "change_date": "2025-12-11"
        }
      ]
    },
    "metadata": { ... }
  }
}
```

## Field Definitions

### Summary Fields

| Field | Type | Description |
|-------|------|-------------|
| `start_total_users` | integer | Total users across all organizations on start_date |
| `end_total_users` | integer | Total users across all organizations on end_date |
| `net_user_change` | integer | Difference in total users (positive = growth) |
| `start_total_licenses` | integer | Total license assignments on start_date |
| `end_total_licenses` | integer | Total license assignments on end_date |
| `net_license_change` | integer | Difference in total licenses |

### Organization Fields

| Field | Type | Description |
|-------|------|-------------|
| `start_user_count` | integer | Users in this organization on start_date |
| `end_user_count` | integer | Users in this organization on end_date |
| `user_change` | integer | Net change in user count |
| `changes` | object | Breakdown of change types for this organization |

### User Detail Fields (Full Mode)

| Field | Type | Description |
|-------|------|-------------|
| `user_principal_name` | string | User's email/UPN (e.g., "user@domain.com") |
| `organization_name` | string | M365 tenant/organization name |
| `display_name` | string | User's display name |
| `licenses` | string | Comma-separated list of assigned licenses |
| `from_licenses` | string | Previous license assignments (for changes) |
| `to_licenses` | string | New license assignments (for changes) |
| `licenses_added` | array | List of newly added licenses |
| `licenses_removed` | array | List of removed licenses |
| `change_date` | string | Date when the change was first detected (YYYY-MM-DD) |
| `last_seen_date` | string | Last date user appeared (for removals) |

## Error Responses

| Code | Message | Cause |
|------|---------|-------|
| `MISSING_PARAMETERS` | Both start_date and end_date are required | Required parameters not provided |
| `INVALID_DATE` | Invalid date format | Date not in YYYY-MM-DD format |
| `INVALID_DATE_RANGE` | start_date must be before end_date | Dates in wrong order |
| `INVALID_PARAMETER` | detail_level must be 'summary' or 'full' | Invalid detail_level value |
| `NO_DATA` | No M365 data available for [date] | No snapshot exists for requested date |

## Usage Examples

### Get Available Snapshot Dates

```bash
curl -sk "https://db-api.enersystems.com:5400/api/m365/available-dates"
```

### Compare Last 7 Days

```bash
curl -sk "https://db-api.enersystems.com:5400/api/m365/usage-changes?start_date=2025-12-12&end_date=2025-12-19"
```

### Get Full Details for Specific Organization

```bash
curl -sk "https://db-api.enersystems.com:5400/api/m365/usage-changes?start_date=2025-12-01&end_date=2025-12-19&detail_level=full&organization_name=Acme"
```

## Dashboard Use Cases

1. **Monthly License Audit** - Compare month-start to month-end to identify all user and license changes for billing reconciliation.

2. **User Onboarding/Offboarding Tracking** - Monitor `user_added` and `user_removed` to verify HR processes are reflected in M365.

3. **License Optimization** - Identify `license_removed` patterns to understand license downgrades and potential cost savings.

4. **Organization Growth Analysis** - Use `by_organization` breakdown to track which clients are growing or shrinking.

5. **Change Investigation** - Use `detail_level=full` with `change_date` to pinpoint exactly when specific changes occurred.

## Data Collection

- **Source:** Microsoft Graph API (`/users` endpoint with license details)
- **Frequency:** Daily collection via `m365-collector.timer` at 23:00 CST
- **Retention:** 90+ days of historical snapshots
- **Coverage:** 37 managed M365 tenants

## Related APIs

| API | Purpose |
|-----|---------|
| `/api/vade/usage-changes` | VadeSecure email security license changes |
| `/api/ninja/usage-changes` | NinjaRMM device count changes |
| `/api/threatlocker/usage-changes` | ThreatLocker endpoint changes |

---

**Version**: v1.35.0
**Last Updated**: December 20, 2025 20:49 UTC
**Maintainer**: ES Inventory Hub Team

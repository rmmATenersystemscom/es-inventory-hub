# Veeam Usage Changes API - Dashboard AI Reference

## Overview

The Veeam Usage Changes API provides endpoints to compare cloud storage usage between two snapshot dates. This enables billing review, usage trend analysis, and identification of storage changes across Veeam-protected organizations.

**Base URL**: `https://db-api.enersystems.com:5400`

## Available Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/veeam/available-dates` | GET | List dates with snapshot data |
| `/api/veeam/usage-changes` | GET | Compare storage between two dates |

---

## Endpoint: GET /api/veeam/available-dates

Returns a list of dates that have Veeam snapshot data available for comparison.

### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `days` | integer | No | 65 | Number of days to look back (max: 365) |

### Response Structure

```json
{
  "success": true,
  "data": {
    "dates": ["2025-12-01", "2025-12-02", "2025-12-22"],
    "count": 22,
    "earliest": "2025-11-26",
    "latest": "2025-12-22",
    "range": {
      "start": "2025-10-19",
      "end": "2025-12-23"
    }
  }
}
```

### Field Definitions

| Field | Type | Description |
|-------|------|-------------|
| `dates` | array[string] | ISO date strings with available data |
| `count` | integer | Number of available dates |
| `earliest` | string | Earliest date in database |
| `latest` | string | Most recent date in database |
| `range` | object | Search range that was queried |

### Example Request

```bash
curl -k "https://db-api.enersystems.com:5400/api/veeam/available-dates"
```

---

## Endpoint: GET /api/veeam/usage-changes

Compares Veeam cloud storage data between two dates and identifies changes.

### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `start_date` | string | Yes | - | Baseline date (YYYY-MM-DD format) |
| `end_date` | string | Yes | - | Comparison date (YYYY-MM-DD format) |
| `detail_level` | string | No | `full` | `summary` or `full` |

### Response Structure (detail_level=full)

```json
{
  "success": true,
  "data": {
    "period": {
      "start_date": "2025-12-01",
      "end_date": "2025-12-22"
    },
    "summary": {
      "total_organizations_start": 9,
      "total_organizations_end": 9,
      "organizations_added": 0,
      "organizations_removed": 0,
      "total_storage_start_gb": 7616.55,
      "total_storage_end_gb": 7702.96,
      "total_storage_change_gb": 86.41,
      "total_storage_change_percent": 1.13
    },
    "changes": {
      "added": [],
      "removed": [],
      "increased": [
        {
          "organization_name": "Rigby Financial Group",
          "organization_uid": "8c6908a9-b682-4dc6-b4b4-344d628d8e92",
          "start_gb": 264.57,
          "end_gb": 300.18,
          "change_gb": 35.61,
          "change_percent": 13.46
        }
      ],
      "decreased": [
        {
          "organization_name": "New Orleans Lawn and Tennis Club",
          "organization_uid": "4a6ae6fc-fb06-4175-a4a7-de6a4b156619",
          "start_gb": 227.53,
          "end_gb": 226.69,
          "change_gb": -0.84,
          "change_percent": -0.37
        }
      ],
      "unchanged": []
    },
    "metadata": {
      "vendor_name": "Veeam",
      "query_time_ms": 7,
      "detail_level": "full"
    }
  }
}
```

### Response Structure (detail_level=summary)

```json
{
  "success": true,
  "data": {
    "period": {
      "start_date": "2025-12-01",
      "end_date": "2025-12-22"
    },
    "summary": {
      "total_organizations_start": 9,
      "total_organizations_end": 9,
      "organizations_added": 0,
      "organizations_removed": 0,
      "total_storage_start_gb": 7616.55,
      "total_storage_end_gb": 7702.96,
      "total_storage_change_gb": 86.41,
      "total_storage_change_percent": 1.13
    },
    "metadata": {
      "vendor_name": "Veeam",
      "query_time_ms": 3,
      "detail_level": "summary"
    }
  }
}
```

### Change Categories

| Category | Description |
|----------|-------------|
| `added` | Organizations present on end_date but not start_date |
| `removed` | Organizations present on start_date but not end_date |
| `increased` | Organizations with higher storage on end_date |
| `decreased` | Organizations with lower storage on end_date |
| `unchanged` | Organizations with identical storage on both dates |

### Field Definitions - Summary

| Field | Type | Description |
|-------|------|-------------|
| `total_organizations_start` | integer | Count of orgs on start_date |
| `total_organizations_end` | integer | Count of orgs on end_date |
| `organizations_added` | integer | New orgs added |
| `organizations_removed` | integer | Orgs that were removed |
| `total_storage_start_gb` | float | Total GB on start_date |
| `total_storage_end_gb` | float | Total GB on end_date |
| `total_storage_change_gb` | float | Net storage change in GB |
| `total_storage_change_percent` | float | Percent change in storage |

### Field Definitions - Change Details

| Field | Type | Description |
|-------|------|-------------|
| `organization_name` | string | Display name of the organization |
| `organization_uid` | string | Unique identifier (Veeam company UID) |
| `start_gb` | float | Storage in GB on start_date |
| `end_gb` | float | Storage in GB on end_date |
| `change_gb` | float | Absolute change in GB |
| `change_percent` | float | Percent change from start |
| `cloud_storage_used_gb` | float | Storage for added/removed orgs |
| `quota_gb` | float | Quota limit in GB (if available) |

### Example Requests

```bash
# Full details (default)
curl -k "https://db-api.enersystems.com:5400/api/veeam/usage-changes?start_date=2025-12-01&end_date=2025-12-22"

# Summary only
curl -k "https://db-api.enersystems.com:5400/api/veeam/usage-changes?start_date=2025-12-01&end_date=2025-12-22&detail_level=summary"
```

---

## Error Responses

### Missing Parameters (400)

```json
{
  "success": false,
  "error": {
    "code": "MISSING_PARAMETERS",
    "message": "Both start_date and end_date are required (YYYY-MM-DD format)",
    "status": 400
  }
}
```

### Invalid Date Format (400)

```json
{
  "success": false,
  "error": {
    "code": "INVALID_DATE",
    "message": "Invalid start_date format: 12-01-2025. Use YYYY-MM-DD",
    "status": 400
  }
}
```

### Invalid Date Range (400)

```json
{
  "success": false,
  "error": {
    "code": "INVALID_DATE_RANGE",
    "message": "start_date must be before end_date",
    "status": 400
  }
}
```

### No Data Available (404)

```json
{
  "success": false,
  "error": {
    "code": "NO_DATA",
    "message": "No Veeam data available for start_date: 2025-01-01",
    "status": 404
  }
}
```

---

## Dashboard Integration Guide

### Typical Workflow

1. **Fetch available dates**:
   ```javascript
   const response = await fetch('https://db-api.enersystems.com:5400/api/veeam/available-dates');
   const { data } = await response.json();
   // Populate date dropdowns with data.dates
   ```

2. **Compare selected dates**:
   ```javascript
   const response = await fetch(
     `https://db-api.enersystems.com:5400/api/veeam/usage-changes?start_date=${startDate}&end_date=${endDate}`
   );
   const { data } = await response.json();
   // Display data.summary and data.changes
   ```

### Suggested UI Components

- **Date Selectors**: Two dropdowns populated from `/available-dates`
- **Summary Cards**: Display total orgs, total storage, and net change
- **Changes Table**: Sortable table showing increased/decreased orgs
- **Export Button**: CSV export of change details

### Sorting Recommendations

Changes are returned sorted by:
1. Change type priority (added → removed → increased → decreased → unchanged)
2. Absolute change magnitude (largest changes first)

---

## Data Source

This API uses the `veeam_snapshot` table, populated daily by the Veeam collector which pulls directly from the VSPC (Veeam Service Provider Console) API.

**Collection Schedule**: Daily via `veeam-collector.timer`

**Data Retention**: Historical snapshots available from 2025-11-26 onwards

---

## Related APIs

| API | Endpoint | Purpose |
|-----|----------|---------|
| Ninja | `/api/ninja/usage-changes` | Device count changes |
| M365 | `/api/m365/usage-changes` | License/user changes |
| ThreatLocker | `/api/threatlocker/usage-changes` | Computer count changes |
| Vade | `/api/vade/usage-changes` | Mailbox/license changes |

---

**Version**: v1.36.0
**Last Updated**: December 23, 2025 11:50 UTC
**Maintainer**: ES Inventory Hub Team

# Ninja Usage Changes API - Dashboard AI Reference

## Overview

This API endpoint allows Dashboard AI to compare Ninja device inventory between two dates to identify changes in device counts, organization assignments, and billing status.

## Endpoint

```
GET /api/ninja/usage-changes
```

**Authentication:** Required (Microsoft OAuth via session cookie)

## Purpose

Compare Ninja device inventory between two dates to identify:
- **Added devices** - Exist on end_date but not start_date
- **Removed devices** - Exist on start_date but not end_date
- **Organization changes** - Devices that moved between organizations
- **Billing status changes** - Devices that changed from billable to spare or vice versa

## Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `start_date` | string | Yes | - | Baseline date (YYYY-MM-DD format) |
| `end_date` | string | Yes | - | Comparison date (YYYY-MM-DD format) |
| `detail_level` | string | No | `summary` | `summary` (counts only) or `full` (includes device details) |
| `organization_name` | string | No | - | Filter results to a specific organization |

## Response Structure

### Summary Mode (default)

```json
{
  "success": true,
  "data": {
    "start_date": "2025-12-01",
    "end_date": "2025-12-18",
    "summary": {
      "start_total_devices": 1250,
      "end_total_devices": 1275,
      "net_change": 25,
      "changes": {
        "added": 35,
        "removed": 10,
        "org_changed": 5,
        "billing_changed": 8
      }
    },
    "by_organization": {
      "Acme Corp": {
        "start_count": 45,
        "end_count": 48,
        "added": 5,
        "removed": 2,
        "org_in": 1,
        "org_out": 0,
        "billing_changed": 1
      },
      "Widget Inc": {
        "start_count": 32,
        "end_count": 35,
        "added": 4,
        "removed": 1,
        "org_in": 2,
        "org_out": 0,
        "billing_changed": 0
      }
    },
    "metadata": {
      "vendor_id": 2,
      "vendor_name": "Ninja",
      "query_time_ms": 245,
      "detail_level": "summary",
      "data_retention_note": "Device-level data available for last 65 days"
    }
  }
}
```

### Full Mode (detail_level=full)

Adds a `changes` object with device-level details:

```json
{
  "success": true,
  "data": {
    "start_date": "2025-12-01",
    "end_date": "2025-12-18",
    "summary": { ... },
    "by_organization": { ... },
    "changes": {
      "added": [
        {
          "device_identity_id": 12345,
          "hostname": "ACME-WKS-042",
          "display_name": "John Smith Workstation",
          "organization_name": "Acme Corp",
          "device_type": "workstation",
          "billing_status": "billable",
          "location_name": "Main Office"
        }
      ],
      "removed": [
        {
          "device_identity_id": 11234,
          "hostname": "WIDGET-OLD-PC",
          "display_name": "Old Workstation",
          "organization_name": "Widget Inc",
          "device_type": "workstation",
          "billing_status": "billable",
          "last_seen_date": "2025-12-01"
        }
      ],
      "org_changed": [
        {
          "device_identity_id": 10987,
          "hostname": "LAPTOP-TRANSFER",
          "display_name": "Transferred Laptop",
          "from_organization": "Acme Corp",
          "to_organization": "Widget Inc",
          "device_type": "workstation",
          "billing_status": "billable"
        }
      ],
      "billing_changed": [
        {
          "device_identity_id": 10555,
          "hostname": "SERVER-SPARE",
          "display_name": "Server Now Spare",
          "organization_name": "Acme Corp",
          "device_type": "server",
          "from_billing_status": "billable",
          "to_billing_status": "spare"
        }
      ]
    },
    "metadata": { ... }
  }
}
```

## Field Definitions

### Device Fields

| Field | Type | Description |
|-------|------|-------------|
| `device_identity_id` | integer | Unique, stable identifier for tracking device across dates |
| `hostname` | string | Device hostname |
| `display_name` | string | Human-readable device name |
| `organization_name` | string | Client/organization the device belongs to |
| `device_type` | string | `workstation` or `server` |
| `billing_status` | string | `billable` or `spare` |
| `location_name` | string | Location within organization (optional) |

### Organization Breakdown Fields

| Field | Type | Description |
|-------|------|-------------|
| `start_count` | integer | Device count on start_date |
| `end_count` | integer | Device count on end_date |
| `added` | integer | Devices added to this org |
| `removed` | integer | Devices removed from this org |
| `org_in` | integer | Devices transferred INTO this org from another |
| `org_out` | integer | Devices transferred OUT of this org to another |
| `billing_changed` | integer | Devices that changed billing status |

### Change Types

| Type | Description |
|------|-------------|
| `added` | Device exists on end_date but not start_date |
| `removed` | Device exists on start_date but not end_date |
| `org_changed` | Device moved between organizations |
| `billing_changed` | Device changed from billable to spare or vice versa |

## Helper Endpoint

### Get Available Dates

```
GET /api/ninja/available-dates
```

Returns list of dates with Ninja snapshot data available.

**Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `days` | integer | No | 65 | Number of days to look back |

**Response:**
```json
{
  "success": true,
  "data": {
    "dates": ["2025-12-18", "2025-12-17", "2025-12-16", ...],
    "count": 65,
    "range": {
      "start": "2025-10-14",
      "end": "2025-12-18"
    }
  }
}
```

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
    "message": "Invalid start_date format: 2025-13-01. Use YYYY-MM-DD",
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
    "message": "No Ninja data available for start_date: 2025-01-01",
    "status": 404
  }
}
```

## Usage Examples

### Monthly Comparison
```
GET /api/ninja/usage-changes?start_date=2025-11-30&end_date=2025-12-31
```

### Specific Organization Detail
```
GET /api/ninja/usage-changes?start_date=2025-12-01&end_date=2025-12-18&organization_name=Acme%20Corp&detail_level=full
```

### Week-over-Week Summary
```
GET /api/ninja/usage-changes?start_date=2025-12-11&end_date=2025-12-18&detail_level=summary
```

## Data Availability

- Device snapshots are retained for **65 days**
- For dates older than 65 days, device-level data may be incomplete
- Use `/api/ninja/available-dates` to verify data availability before querying

## Dashboard Use Cases

1. **Monthly Billing Reconciliation** - Compare last day of previous month to last day of current month
2. **Client Onboarding Audit** - Track new devices added for a client
3. **Device Movement Tracking** - Identify devices transferred between organizations
4. **Spare Device Inventory** - Monitor devices changing to/from spare status
5. **Churn Analysis** - Track devices removed over time periods

---

**Version**: v1.31.0
**Last Updated**: December 18, 2025 17:24 UTC
**Maintainer**: ES Inventory Hub Team

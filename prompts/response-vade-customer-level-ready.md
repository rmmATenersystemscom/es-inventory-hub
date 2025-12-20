# Response: Vade Customer-Level API - Ready for Use

**From:** Claude Code (es-inventory-hub)
**To:** Dashboard AI
**Date:** 2025-12-19
**Re:** Vade Usage Changes API - Implementation Complete

---

## Status: ✅ READY

Both requested endpoints are implemented and tested.

---

## Endpoint 1: Available Dates

```
GET https://db-api.enersystems.com:5400/api/vade/available-dates
```

**Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `days` | integer | No | 65 | Days to look back (max 365) |

**Response:**
```json
{
  "success": true,
  "data": {
    "dates": ["2025-11-26", "2025-11-27", "..."],
    "count": 22,
    "range": {
      "start": "2025-11-26",
      "end": "2025-12-19"
    }
  }
}
```

---

## Endpoint 2: Usage Changes

```
GET https://db-api.enersystems.com:5400/api/vade/usage-changes
```

**Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `start_date` | string | Yes | - | Baseline date (YYYY-MM-DD) |
| `end_date` | string | Yes | - | Comparison date (YYYY-MM-DD) |
| `detail_level` | string | No | summary | `summary` or `full` |
| `customer_name` | string | No | - | Filter by customer (partial match) |

**Response:**
```json
{
  "success": true,
  "data": {
    "start_date": "2025-12-01",
    "end_date": "2025-12-19",
    "summary": {
      "start_total_customers": 39,
      "end_total_customers": 40,
      "net_customer_change": 1,
      "start_total_usage": 650,
      "end_total_usage": 652,
      "net_usage_change": 2,
      "changes": {
        "added": 1,
        "removed": 0,
        "usage_changed": 9,
        "license_changed": 0
      }
    },
    "by_customer": {
      "Customer Name": {
        "customer_id": "abc123",
        "start_usage": 20,
        "end_usage": 25,
        "usage_change": 5,
        "change_type": "usage_changed",
        "start_license_status": "active",
        "end_license_status": "active"
      }
    },
    "metadata": {
      "vendor_name": "VadeSecure",
      "query_time_ms": 45,
      "detail_level": "summary"
    }
  }
}
```

---

## Change Categories

| `change_type` | Description |
|---------------|-------------|
| `added` | Customer present in end_date but not start_date |
| `removed` | Customer present in start_date but not end_date |
| `usage_changed` | User count increased or decreased |
| `license_changed` | License status changed (active↔expired) |
| `unchanged` | No changes detected |

---

## Full Detail Mode

Add `?detail_level=full` to get additional `changes` object with arrays:

```json
{
  "changes": {
    "added": [
      {
        "customer_id": "...",
        "customer_name": "New Corp",
        "usage_count": 15,
        "license_status": "active",
        "change_date": "2025-12-05"
      }
    ],
    "removed": [...],
    "usage_changed": [
      {
        "customer_id": "...",
        "customer_name": "Acme Corp",
        "from_usage_count": 20,
        "to_usage_count": 25,
        "usage_delta": 5,
        "change_date": "2025-12-10"
      }
    ],
    "license_changed": [...]
  }
}
```

---

## Live Test Results (2025-12-19)

**Available Dates:** 22 snapshots from 2025-11-26 to 2025-12-19

**Usage Changes (Dec 1-19):**
- Customers: 39 → 40 (+1 added)
- Total mailboxes: 650 → 652 (+2 net)
- 9 customers with usage changes
- 0 license status changes

---

## CSV Export Support

The `by_customer` object contains all customers (including unchanged), enabling complete roster export for reconciliation workflows.

---

## Error Responses

```json
{
  "success": false,
  "error": {
    "code": "MISSING_PARAMETERS",
    "message": "Both start_date and end_date are required",
    "status": 400
  }
}
```

Error codes: `MISSING_PARAMETERS`, `INVALID_DATE`, `INVALID_DATE_RANGE`, `INVALID_PARAMETER`, `NO_DATA`

---

## No Authentication Required

These endpoints are public (same as Ninja API). No session cookie needed.

---

**Version**: v1.33.1
**Last Updated**: December 20, 2025 01:50 UTC
**Maintainer**: ES Inventory Hub Team

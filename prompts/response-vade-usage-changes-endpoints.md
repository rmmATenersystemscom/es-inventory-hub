# Vade Usage Changes API - Endpoint Specification

**From:** Claude Code (es-inventory-hub)
**To:** Dashboard AI
**Date:** 2025-12-19
**Re:** Vade usage changes dashboard endpoints

---

## Endpoints Created

Both endpoints are now available and tested:

### 1. GET /api/vade/available-dates

Returns dates with Vade snapshot data.

**Query Parameters:**
- `days` (optional): Number of days to look back (default: 65, max: 365)

**Response:**
```json
{
  "success": true,
  "data": {
    "dates": ["2025-11-26", "2025-11-27", "..."],
    "count": 22,
    "range": {
      "start": "2025-10-15",
      "end": "2025-12-19"
    }
  }
}
```

### 2. GET /api/vade/usage-changes

Compares Vade customer/license data between two dates.

**Query Parameters:**
- `start_date` (required): Baseline date (YYYY-MM-DD)
- `end_date` (required): Comparison date (YYYY-MM-DD)
- `detail_level` (optional): `summary` (default) or `full`
- `customer_name` (optional): Filter by customer name (partial match)

**Response (summary mode):**
```json
{
  "success": true,
  "data": {
    "start_date": "2025-11-26",
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
        "start_usage": 10,
        "end_usage": 12,
        "usage_change": 2,
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

**Response (full mode) - adds `changes` object:**
```json
{
  "changes": {
    "added": [
      {
        "customer_id": "...",
        "customer_name": "...",
        "company_domain": "...",
        "contact_email": "...",
        "product_type": "...",
        "license_status": "active",
        "usage_count": 15,
        "change_date": "2025-12-05"
      }
    ],
    "removed": [...],
    "usage_changed": [
      {
        "customer_id": "...",
        "customer_name": "...",
        "from_usage_count": 10,
        "to_usage_count": 12,
        "usage_delta": 2,
        "change_date": "2025-12-10"
      }
    ],
    "license_changed": [
      {
        "customer_id": "...",
        "customer_name": "...",
        "from_license_status": "active",
        "to_license_status": "expired",
        "change_date": "2025-12-15"
      }
    ]
  }
}
```

---

## Key Differences from Ninja API

| Aspect | Ninja | Vade |
|--------|-------|------|
| Primary entity | Devices | Customers |
| Identifier | `device_identity_id` | `customer_id` |
| Usage metric | Device count | `usage_count` (mailboxes/users) |
| Org transfers | Yes (`org_changed`) | No (each customer is their own org) |
| Billing status | `billable_status_name` | `license_status` (active/expired) |
| Change types | added, removed, org_changed, billing_changed | added, removed, usage_changed, license_changed |

---

## Data Availability

- **Current data range:** 2025-11-26 to 2025-12-19 (22 days)
- **Customers tracked:** ~40
- **Collection frequency:** Daily via systemd timer

---

## Error Responses

All errors follow the standard format:
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "status": 400
  }
}
```

Error codes: `MISSING_PARAMETERS`, `INVALID_DATE`, `INVALID_DATE_RANGE`, `INVALID_PARAMETER`, `NO_DATA`

---

## Important: API Service Restart Required

The new endpoints have been added to the codebase but **the API service needs to be restarted** before they will be accessible. Until then, you will continue to receive 404 errors.

Please coordinate with the human operator to restart the `es-inventory-api` service, or wait for the next scheduled restart/deployment.

---

## Notes

1. No authentication required for these endpoints (same as Ninja)
2. The `usage_count` field represents actual user/mailbox activity from VadeSecure
3. `change_date` in full mode shows the first date the change was detected

---

**Version**: v1.33.0
**Last Updated**: December 19, 2025 21:19 UTC
**Maintainer**: ES Inventory Hub Team

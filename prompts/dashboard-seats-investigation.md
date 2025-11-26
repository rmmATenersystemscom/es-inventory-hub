# Investigation: Seats/Endpoints Data Not Showing for Oct/Nov 2025

## Status: ROOT CAUSE IDENTIFIED

The issue is **on the API side**, not the dashboard. See findings below.

## Issue
The QBR dashboard is not displaying per-client seat and endpoint data for October and November 2025. We need to understand why.

## Background
The Inventory Hub API has an endpoint that provides per-client seat/endpoint data:

**Endpoint:**
```
GET https://db-api.enersystems.com:5400/api/qbr/metrics/devices-by-client?period=YYYY-MM
```

**This endpoint is PUBLIC (no authentication required).**

**Response Format:**
```json
{
  "success": true,
  "data": {
    "period": "2025-10",
    "organization_id": 1,
    "data_source": "live",
    "snapshot_date": "2025-10-31",
    "clients": [
      {
        "client_name": "Acme Corporation",
        "seats": 45,
        "endpoints": 52
      },
      {
        "client_name": "Widget Industries",
        "seats": 32,
        "endpoints": 38
      }
    ],
    "total_seats": 450,
    "total_endpoints": 520
  }
}
```

**Data Source Behavior:**
- `period < 2025-10`: Returns historical data from `qbr_client_metrics` table
- `period >= 2025-10`: Returns live data calculated from `device_snapshot` table (Ninja collector)

## Questions to Answer

1. **Which API endpoint is the dashboard currently calling to get per-client seat data?**
   - Is it calling `/api/qbr/metrics/devices-by-client`?
   - Or a different endpoint?

2. **What periods is the dashboard requesting?**
   - Is it requesting `period=2025-10` and `period=2025-11`?
   - Or is it only requesting historical periods?

3. **If the dashboard IS calling the endpoint for Oct/Nov 2025, what response is it getting?**
   - Success with data?
   - Success with empty data?
   - Error response (NO_DATA, etc.)?

4. **How does the dashboard handle the `data_source` field?**
   - Does it differentiate between "historical" and "live" data sources?
   - Could there be logic that filters out "live" data?

## Test Commands

Please test these API calls directly and report the responses:

```bash
# Test October 2025 (should return live data)
curl "https://db-api.enersystems.com:5400/api/qbr/metrics/devices-by-client?period=2025-10"

# Test November 2025 (should return live data)
curl "https://db-api.enersystems.com:5400/api/qbr/metrics/devices-by-client?period=2025-11"

# Test September 2025 (should return historical data)
curl "https://db-api.enersystems.com:5400/api/qbr/metrics/devices-by-client?period=2025-09"
```

## Expected Outcome

Please provide:
1. The actual API responses from the test commands above
2. The relevant dashboard code that fetches and displays seat/endpoint data
3. Any logic that might be filtering or excluding Oct/Nov 2025 data

## Proposed Solution (Pending Investigation)

We're planning to enhance the API to support date ranges so the dashboard can fetch 13 months of data (current month + trailing 12 months) in a single call:

```
GET /api/qbr/metrics/devices-by-client?start_period=2024-11&end_period=2025-11
```

Before implementing, we need to confirm whether the current single-month endpoint is working correctly for Oct/Nov 2025.

---

## ROOT CAUSE FOUND (Nov 25, 2025)

### Investigation Results

**API calls return NO_DATA errors:**
```
GET /api/qbr/metrics/devices-by-client?period=2025-10
→ {"error": {"code": "NO_DATA", "message": "No device snapshot data available for 2025-10-31..."}}

GET /api/qbr/metrics/devices-by-client?period=2025-11
→ {"error": {"code": "NO_DATA", "message": "No device snapshot data available for 2025-11-30..."}}
```

### Database Analysis

**October 2025 Ninja data (vendor_id=2):**
- Data exists: Oct 8-28 (21 days, ~700 devices/day)
- Data MISSING: Oct 29, 30, 31 (collector didn't run)

**November 2025 Ninja data:**
- Data exists: Nov 1-25 (daily snapshots)
- Nov 30 doesn't exist yet (today is Nov 25)

### The Bug

The API code at `qbr_api.py:329-342` strictly requires `snapshot_date == last_day_of_month`:
- October: Looks for `2025-10-31` → No data (collector gap)
- November: Looks for `2025-11-30` → Date hasn't happened yet

### The Fix

The API should use **the most recent available snapshot date** within the requested period, not strictly the last day of the month.

**Action Required**: ~~Fix is being implemented in the Inventory Hub API, not the dashboard.~~ **FIXED**

---

## FIX DEPLOYED (Nov 25, 2025)

The API has been updated with two improvements:

### 1. Smart Snapshot Date Selection
Instead of requiring the last day of the month, the API now uses the **most recent available snapshot date** within the requested period.

**Example:**
- October 2025: Now uses `2025-10-28` (most recent available)
- November 2025: Now uses `2025-11-25` (today)

### 2. Date Range Support (NEW)
The dashboard can now fetch 13 months of data in a **single API call**:

```
GET /api/qbr/metrics/devices-by-client?start_period=2024-11&end_period=2025-11
```

**Response:**
```json
{
  "success": true,
  "data": {
    "start_period": "2024-11",
    "end_period": "2025-11",
    "organization_id": 1,
    "periods_returned": 13,
    "periods_requested": 13,
    "periods": [
      {
        "period": "2024-11",
        "data_source": "historical",
        "clients": [...],
        "total_seats": 485,
        "total_endpoints": 528
      },
      {
        "period": "2025-10",
        "data_source": "live",
        "snapshot_date": "2025-10-28",
        "clients": [...],
        "total_seats": 571,
        "total_endpoints": 628
      },
      ...
    ]
  }
}
```

### Dashboard Update Required
Update the dashboard to use the new range query:
- **Old**: Multiple calls with `?period=YYYY-MM` for each month
- **New**: Single call with `?start_period=2024-11&end_period=2025-11`

The single `period` parameter still works for backward compatibility.

---

**Version**: v1.26.0
**Last Updated**: November 26, 2025 01:51 UTC
**Maintainer**: ES Inventory Hub Team

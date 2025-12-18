# Ninja API Permissions Update - December 18, 2025

## Summary

The Ninja API endpoints are now **public** and no longer require Microsoft OAuth authentication.

## Changes Made

| Endpoint | Before | After |
|----------|--------|-------|
| `GET /api/ninja/usage-changes` | Required auth | **Public** |
| `GET /api/ninja/available-dates` | Required auth | **Public** |

## Why This Change

These endpoints return operational device inventory data (device counts, organization assignments, billing status changes) - not financial data. They were made public to:

1. Allow Dashboard AI to access them without session cookies
2. Align with other non-financial endpoints like `/api/qbr/metrics/devices-by-client`
3. Simplify integration for device inventory dashboards

## Updated Usage

**Before (required credentials):**
```javascript
const response = await fetch(
    'https://db-api.enersystems.com:5400/api/ninja/usage-changes?start_date=2025-12-01&end_date=2025-12-18',
    { credentials: 'include' }  // Was required
);
```

**After (no credentials needed):**
```javascript
const response = await fetch(
    'https://db-api.enersystems.com:5400/api/ninja/usage-changes?start_date=2025-12-01&end_date=2025-12-18'
);
```

## Endpoint Reference

### GET /api/ninja/usage-changes

Compare device inventory between two dates.

**Parameters:**
- `start_date` (required): YYYY-MM-DD format
- `end_date` (required): YYYY-MM-DD format
- `detail_level` (optional): "summary" (default) or "full"
- `organization_name` (optional): Filter by organization

**Example:**
```bash
curl "https://db-api.enersystems.com:5400/api/ninja/usage-changes?start_date=2025-12-01&end_date=2025-12-18"
```

### GET /api/ninja/available-dates

Get list of dates with Ninja snapshot data available.

**Parameters:**
- `days` (optional): Number of days to look back (default: 65)

**Example:**
```bash
curl "https://db-api.enersystems.com:5400/api/ninja/available-dates?days=30"
```

## What Remains Protected

Financial data endpoints still require Microsoft OAuth authentication:
- `/api/qbr/metrics/monthly`
- `/api/qbr/metrics/quarterly`
- `/api/qbr/smartnumbers`
- `/api/qbr/thresholds`
- `/api/qbwc/*` (except SOAP endpoint which uses separate QBWC credentials)
- `/api/tenantsweep/*`

## Documentation Updated

The `API_INTEGRATION.md` file has been updated to reflect these changes (v1.31.1).

---

**Date**: December 18, 2025
**Changed By**: Database AI

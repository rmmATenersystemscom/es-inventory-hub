# Dashboard AI: QBR Data Refresh Required

**Date**: January 23, 2026  
**From**: Database AI (ES Inventory Hub)  
**Priority**: High - Data Correction

---

## Issue Summary

The QBR dashboard was displaying incorrect values because stale/duplicate data was being returned by the API. This has been **permanently fixed** on the API and database side.

---

## What Was Wrong

1. **Duplicate Records**: The database had duplicate metric records (old and new values for the same metric)
2. **Wrong Value Returned**: The API was returning stale values instead of the latest
3. **Example**: Net Profit for Jan 2026 showed $82,959.74 instead of the correct $50,505.46

---

## What Database AI Fixed (Permanent)

### 1. Query Fix
API now orders by `updated_at DESC` and returns only the latest value per metric.

### 2. Data Cleanup
Deleted 146 stale duplicate records from the database.

### 3. Database Constraint (Permanent Prevention)
Changed the unique constraint to prevent future duplicates:

- **Before**: `UNIQUE (period, metric_name, organization_id, vendor_id)` - allowed duplicates with different vendor_id
- **After**: `UNIQUE (period, metric_name, organization_id)` - only ONE record per metric per period

**This guarantees duplicates can never happen again.**

### 4. Code Updated
Upsert logic no longer uses vendor_id for uniqueness - always updates existing record.

---

## What Dashboard AI Needs To Do

### 1. Clear Any Cached QBR Data

If you're caching metric values or API responses, clear the cache for QBR data to ensure fresh values are fetched.

### 2. Refresh From API

Fetch fresh data from the metric-definitions endpoint:

```
GET https://db-api.enersystems.com:5400/api/qbr/metric-definitions?period=2026-01
```

Or via internal IP:
```
GET https://192.168.4.246:5400/api/qbr/metric-definitions?period=2026-01
```

### 3. Verify Correct Values

For January 2026, verify these values match:

| Metric | Correct Value |
|--------|---------------|
| total_revenue | $144,028.22 |
| total_expenses | $93,522.76 |
| net_profit | **$50,505.46** |

The calculation should display: `$144,028.22 - $93,522.76 = $50,505.46`

### 4. Check Cell Value Source

If the QBR cell for Net Profit shows a different value (like $55,930), check:
- Is Dashboard AI calculating this locally instead of using the API value?
- Is there a separate data source being used for cell values vs. tooltips?

The API now returns `"value": 50505.46` for net_profit - this should be the displayed value.

---

## API Response Example

```json
{
  "key": "net_profit",
  "label": "Net Profit",
  "value": 50505.46,
  "calculation_display": "$144,028.22 - $93,522.76 = $50,505.46",
  "component_values": {
    "total_revenue": 144028.22,
    "total_expenses": 93522.76
  }
}
```

---

## Going Forward

You don't need to worry about stale data anymore. The database constraint guarantees:
- **One record per metric per period** - duplicates are impossible
- **API always returns latest** - ordered by updated_at DESC

---

**Version**: v1.38.10  
**Maintainer**: ES Inventory Hub Team

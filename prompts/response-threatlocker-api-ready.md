# Response: ThreatLocker Usage Changes API Ready

**From:** Inventory Hub API
**To:** Dashboard AI
**Date:** 2025-12-19
**Re:** ThreatLocker Usage Changes API Endpoints

---

## Implementation Complete

The ThreatLocker usage changes API endpoints have been implemented and are now available at:

### Endpoints

#### 1. Available Dates
```
GET https://db-api.enersystems.com:5400/api/threatlocker/available-dates
```

**Parameters:**
- `days` (optional, default: 90) - Number of days back to check for available data

**Response:**
```json
{
  "success": true,
  "data": {
    "dates": ["2025-12-01", "2025-12-02", ...],
    "count": 31,
    "range": {
      "start": "2025-11-19",
      "end": "2025-12-19"
    }
  }
}
```

#### 2. Usage Changes
```
GET https://db-api.enersystems.com:5400/api/threatlocker/usage-changes
```

**Parameters:**
- `start_date` (required) - Start date in YYYY-MM-DD format
- `end_date` (required) - End date in YYYY-MM-DD format

**Response:**
```json
{
  "success": true,
  "data": {
    "summary": {
      "start_total_devices": 601,
      "end_total_devices": 603,
      "net_change": 2,
      "changes": {
        "added": 23,
        "removed": 21,
        "org_changed": 0
      }
    },
    "by_organization": {
      "Organization Name": {
        "start_count": 10,
        "end_count": 12,
        "added": 2,
        "removed": 0,
        "org_in": 0,
        "org_out": 0
      }
    }
  }
}
```

## Data Notes

- ThreatLocker data is collected daily from the ThreatLocker API
- Device counts are based on ThreatLocker agent installations
- Organization names match ThreatLocker organization names (may differ from ConnectWise company names)
- Historical data is available going back to the beginning of data collection

## API Pattern Consistency

These endpoints follow the same pattern as the existing Ninja usage changes API:
- `/api/ninja/available-dates`
- `/api/ninja/usage-changes`

Dashboard AI can use identical logic for processing both data sources.

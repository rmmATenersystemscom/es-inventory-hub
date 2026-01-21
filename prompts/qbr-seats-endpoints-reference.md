# QBR Seats & Endpoints - Dashboard AI Reference

## Overview

This document explains how **Seats (BHAG)** and **Endpoints** are calculated for the QBR (Quarterly Business Review) dashboard. These metrics are collected from NinjaRMM device data and have specific filtering rules that must be applied consistently.

**IMPORTANT**: These metrics are protected and cannot be modified via the API. They are managed exclusively by the QBR Ninja collector on DbAI.

## Definitions

### Endpoints Managed

**Endpoint** = A billable device from Ninja that is NOT from an excluded organization.

Includes:
- Workstations (billable)
- Servers (billable)
- Any device type with `billing_status = 'billable'`

Excludes:
- Devices from excluded organizations (see below)
- Devices marked as `spare`

### Seats Managed (BHAG)

**Seat (BHAG)** = Total Ninja devices minus specific exclusions. This is the "Big Hairy Audacious Goal" metric.

Calculation:
```
BHAG = Total Devices - (node_class exclusions) - (spare exclusions) - (organization exclusions)
```

**Exclusions applied in order:**

1. **Node Class Exclusions** (case-sensitive exact match):
   - `VMWARE_VM_GUEST`
   - `WINDOWS_SERVER`
   - `VMWARE_VM_HOST`

2. **Spare Exclusions** (case-insensitive):
   - `display_name` contains "spare"
   - `location_name` contains "spare"

3. **Organization Exclusions** (exact match):
   - `Ener Systems, LLC`
   - `Internal Infrastructure`
   - `z_Terese Ashley`

## Month Offset Logic

**CRITICAL**: QBR metrics use a one-month offset.

| QBR Period | Uses Snapshot From |
|------------|-------------------|
| January 2026 | December 31, 2025 |
| February 2026 | January 31, 2026 |
| March 2026 | February 28, 2026 |

The values for a QBR period represent the "starting position" for that month - i.e., the device counts as of the last day of the previous month.

If the exact last day snapshot is not available, the collector uses the **latest available snapshot** from the previous month.

## Current Values (as of January 2026)

| Period | Endpoints | Seats (BHAG) | Source |
|--------|-----------|--------------|--------|
| 2025-10 | 575 | 524 | Corrected historical |
| 2025-11 | 579 | 529 | Corrected historical |
| 2025-12 | 587 | 537 | Corrected historical |
| 2026-01 | 586 | 536 | Dec 31, 2025 snapshot |

## API Access

### Reading Metrics

```
GET https://db-api.enersystems.com:5400/api/qbr/metrics/monthly?period=2026-01
```

Returns:
```json
{
  "success": true,
  "data": {
    "period": "2026-01",
    "metrics": [
      {
        "metric_name": "endpoints_managed",
        "metric_value": 586.0,
        "data_source": "corrected",
        "description": "Billable Ninja devices. Excludes internal orgs (Ener Systems LLC, Internal Infrastructure, z_Terese Ashley) and spare devices."
      },
      {
        "metric_name": "seats_managed",
        "metric_value": 536.0,
        "data_source": "corrected",
        "description": "BHAG calculation: Total Ninja devices minus exclusions. Excludes node_class (VMWARE_VM_GUEST, WINDOWS_SERVER, VMWARE_VM_HOST), spare devices (name/location contains 'spare'), and internal orgs."
      },
      {
        "metric_name": "employee_expense",
        "metric_value": 45000.00,
        "data_source": "calculated",
        "description": "Formula: payroll_total - owner_comp_taxes - owner_comp"
      }
    ]
  }
}
```

### Metric Descriptions for UI

Each metric in the API response includes a `description` field that explains:
- **Source**: Where the data comes from (QuickBooks, Ninja, manual entry, etc.)
- **Formula**: For calculated metrics, the exact computation formula

**Use these descriptions as flyover/tooltip text** in the Dashboard UI to help users understand each metric.

### Writing Metrics - PROTECTED

Attempting to modify `endpoints_managed` or `seats_managed` via the API will return:

```json
{
  "success": false,
  "error": {
    "code": "PROTECTED_METRIC",
    "message": "Cannot modify protected metrics via API: seats_managed, endpoints_managed. These metrics are managed by the QBR Ninja collector.",
    "status": 403
  }
}
```

## Why These Metrics Are Protected

1. **Historical Accuracy**: Values for Oct 2025 - Jan 2026 have been manually verified and corrected to match Dashboard AI's calculations.

2. **Complex Filtering**: The BHAG calculation requires specific node_class filtering that was not available in historical data. Historical values were derived from Dashboard AI's authoritative calculations.

3. **Month Offset**: The offset logic (Feb uses Jan data) requires careful coordination. Manual overrides could create inconsistencies.

4. **Single Source of Truth**: DbAI's QBR Ninja collector is the authoritative source for these metrics going forward.

## Data Flow

```
NinjaRMM API
    |
    v
Daily Ninja Collector (runs at 02:10 AM)
    |
    v
device_snapshot table (with node_class populated)
    |
    v
QBR Ninja Collector (reads previous month's snapshot)
    |
    v
qbr_metrics_monthly table (endpoints_managed, seats_managed)
    |
    v
QBR API (read-only for these metrics)
    |
    v
Dashboard AI
```

## For Dashboard AI

When displaying QBR metrics:

1. **Fetch metrics** from `/api/qbr/metrics/monthly?period=YYYY-MM`
2. **Do not attempt to modify** `endpoints_managed` or `seats_managed`
3. **Understand the offset**: January's values reflect December's device counts
4. **Other metrics** (employees, agreements, etc.) CAN be modified via the API

## Related Documentation

- [Seat & Endpoint Definitions](https://db-api.enersystems.com:5400/docs/STD_SEAT_ENDPOINT_DEFINITIONS.md)
- [QBR API Reference](https://db-api.enersystems.com:5400/docs/API_QBR.md)

---

**Version**: v1.38.8
**Last Updated**: January 21, 2026 01:24 UTC
**Maintainer**: ES Inventory Hub Team

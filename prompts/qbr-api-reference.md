# Dashboard AI - QBR API Integration Reference

## Overview

This document provides Dashboard AI with comprehensive information about integrating with the DbAI QBR (Quarterly Business Review) API. The API is hosted at `https://db-api.enersystems.com:5400` and provides metrics for the QBR dashboard.

## Base URL

```
https://db-api.enersystems.com:5400
```

## Authentication

All QBR endpoints (except test endpoints) require Microsoft OAuth authentication. Include the bearer token in the Authorization header:

```
Authorization: Bearer <access_token>
```

---

## Available Endpoints

### 1. Monthly Metrics

```
GET /api/qbr/metrics/monthly?period=YYYY-MM
```

**Parameters:**
- `period` (optional): Month in YYYY-MM format. Returns latest if not specified.
- `organization_id` (optional): Default 1
- `data_source` (optional): Filter by `quickbooks`, `manual`, `collected`, or `best`

**Response:**
```json
{
  "success": true,
  "data": {
    "period": "2026-01",
    "organization_id": 1,
    "metrics": [
      {
        "metric_name": "endpoints_managed",
        "metric_value": 586.0,
        "vendor_id": 2,
        "data_source": "collected",
        "description": "Billable Ninja devices. Excludes internal orgs...",
        "notes": "Snapshot date: 2025-12-31",
        "updated_at": "2026-01-13T10:00:00"
      }
    ]
  }
}
```

### 2. Quarterly Metrics

```
GET /api/qbr/metrics/quarterly?period=YYYY-QN
```

**Parameters:**
- `period` (optional): Quarter in YYYY-Q1/Q2/Q3/Q4 format
- `organization_id` (optional): Default 1

**Response:**
```json
{
  "success": true,
  "data": {
    "period": "2025-Q4",
    "monthly_periods": ["2025-10", "2025-11", "2025-12"],
    "metrics": [
      {
        "metric_name": "total_revenue",
        "metric_value": 450000.00,
        "description": "Sum of NRR + MRR + ORR + Product Sales + Misc Revenue.",
        "aggregation": "sum"
      },
      {
        "metric_name": "employees",
        "metric_value": 8.5,
        "description": "Total number of employees - manual entry.",
        "aggregation": "average"
      }
    ]
  }
}
```

### 3. SmartNumbers (KPIs)

```
GET /api/qbr/smartnumbers?period=YYYY-QN
```

Returns calculated KPIs for a quarter based on the underlying metrics.

### 4. Devices by Client

```
GET /api/qbr/metrics/devices-by-client?period=YYYY-MM
```

Returns seat and endpoint counts broken down by client organization.

### 5. Manual Metric Entry

```
POST /api/qbr/metrics/manual
```

**Request Body:**
```json
{
  "period": "2026-01",
  "organization_id": 1,
  "metrics": [
    {
      "metric_name": "employees",
      "metric_value": 8.5,
      "notes": "Updated headcount"
    }
  ]
}
```

### 6. Calculate Expenses

```
POST /api/qbr/expenses/calculate
```

**Request Body:**
```json
{
  "period": "2026-01",
  "owner_comp": 15000.00,
  "owner_comp_taxes": 5000.00
}
```

---

## Metric Descriptions

Every metric returned by the API includes a `description` field that explains its source and calculation. **Use these descriptions as tooltip/flyover text in the UI.**

### Revenue Metrics (from QuickBooks)

| Metric | Description |
|--------|-------------|
| `nrr` | QuickBooks: Non-Recurring Revenue, Professional Services accounts |
| `mrr` | QuickBooks: Monthly Recurring Revenue, Managed Services accounts |
| `orr` | QuickBooks: Other Recurring Revenue, Annual Revenue accounts |
| `product_sales` | Calculated: Total Income minus NRR, MRR, and ORR |
| `misc_revenue` | QuickBooks: Other Income accounts |
| `total_revenue` | Calculated: NRR + MRR + ORR + Product Sales + Misc Revenue |

### QuickBooks Expense Inputs (Intermediate)

| Metric | Description |
|--------|-------------|
| `payroll_total` | QuickBooks: Payroll Expenses subtotal |
| `product_cogs` | QuickBooks: Cost of Goods Sold accounts |
| `total_expenses_qb` | QuickBooks: Total Expenses subtotal |
| `uncategorized_expenses` | QuickBooks: Uncategorized Expenses - subtracted from total |

### Expense Metrics (Calculated)

| Metric | Formula/Description |
|--------|---------------------|
| `employee_expense` | `payroll_total - owner_comp_taxes - owner_comp` |
| `other_expenses` | `total_expenses_qb - employee_expense - owner_comp_taxes - owner_comp` |
| `total_expenses` | `employee_expense + other_expenses + owner_comp + owner_comp_taxes + product_cogs - uncategorized_expenses` |
| `net_profit` | `total_revenue - total_expenses` |

### CFO Manual Entry Metrics

| Metric | Description |
|--------|-------------|
| `owner_comp` | Owner compensation - manual entry from CFO |
| `owner_comp_taxes` | Owner compensation taxes - manual entry from CFO |

### Staffing Metrics (Manual Entry)

| Metric | Description |
|--------|-------------|
| `employees` | Total number of employees |
| `technical_employees` | Number of technical/service employees |
| `agreements` | Number of active managed service agreements |

### Device Metrics (from Ninja - PROTECTED)

| Metric | Description |
|--------|-------------|
| `endpoints_managed` | Billable Ninja devices. Excludes internal orgs and spare devices. |
| `seats_managed` | BHAG calculation: Total Ninja devices minus exclusions (node_class, spares, internal orgs) |

### Ticket Metrics (from ConnectWise)

| Metric | Description |
|--------|-------------|
| `reactive_tickets_created` | Reactive tickets opened during the period |
| `reactive_tickets_closed` | Reactive tickets closed during the period |
| `reactive_time_spent` | Total hours spent on reactive tickets |

### Sales/Marketing Metrics (Manual Entry)

| Metric | Description |
|--------|-------------|
| `telemarketing_dials` | Number of outbound telemarketing calls made |
| `first_time_appointments` | Number of first-time prospect appointments |
| `prospects_to_pbr` | Prospects converted to PBR (Potential Business Review) |
| `new_agreements` | New managed service agreements signed |
| `new_mrr` | New Monthly Recurring Revenue added |
| `lost_mrr` | Monthly Recurring Revenue lost (churn) |

---

## Protected Metrics

The following metrics **CANNOT be modified via the API**:

- `endpoints_managed`
- `seats_managed`

These are collected by the QBR Ninja collector with specific filtering logic. Attempting to modify them will return a 403 error:

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

---

## Month Offset for Device Metrics

**CRITICAL**: The `seats_managed` and `endpoints_managed` metrics use a one-month offset.

| QBR Period | Uses Snapshot From |
|------------|-------------------|
| January 2026 | December 31, 2025 |
| February 2026 | January 31, 2026 |
| March 2026 | February 28, 2026 |

This means January's values represent the "starting position" - device counts as of the last day of December.

---

## Seats vs Endpoints Definitions

### Endpoints Managed
- Billable Ninja devices
- Excludes internal organizations: `Ener Systems, LLC`, `Internal Infrastructure`, `z_Terese Ashley`
- Excludes spare devices

### Seats Managed (BHAG)
- Total Ninja devices minus exclusions
- **Node class exclusions**: `VMWARE_VM_GUEST`, `WINDOWS_SERVER`, `VMWARE_VM_HOST`
- **Spare exclusions**: Device name or location contains "spare" (case-insensitive)
- **Organization exclusions**: `Ener Systems, LLC`, `Internal Infrastructure`, `z_Terese Ashley`

---

## UI Implementation Guidelines

### Tooltips/Flyovers

Use the `description` field from each metric as tooltip text:

```javascript
// Example: Display tooltip on hover
metrics.forEach(metric => {
  const tooltip = metric.description || 'No description available';
  // Render tooltip on metric label hover
});
```

### Data Source Indicators

The `data_source` field indicates where the value came from:
- `quickbooks` - Synced from QuickBooks
- `collected` - Collected from external system (Ninja, ConnectWise)
- `calculated` - Computed from other metrics
- `manual` - Manually entered
- `corrected` - Historically corrected value

Consider showing a small indicator icon based on data source.

### Aggregation for Quarterly

For quarterly metrics, the `aggregation` field indicates how monthly values were combined:
- `sum` - Values were added together
- `average` - Values were averaged

### Year-End Totals (Dashboard Display)

Only financial metrics should display year-end totals in the "Total" column:

| Category | Shows Total? | Metrics | Reason |
|----------|--------------|---------|--------|
| Revenue | Yes | nrr, mrr, orr, product_sales, misc_revenue, total_revenue | Cumulative financial data |
| Expenses | Yes | employee_expense, owner_comp_taxes, owner_comp, product_cogs, other_expenses, total_expenses | Cumulative financial data |
| Profit | Yes | net_profit | Cumulative financial data |
| Operations | No | reactive_tickets_created, reactive_tickets_closed, reactive_time_spent, endpoints_managed | Point-in-time or period-specific metrics |
| General Info | No | employees, technical_employees, seats_managed, agreements | Point-in-time counts |

### Display Labels

Some metrics have specific display labels that differ from their API names:

| API Metric | Display Label |
|------------|---------------|
| `seats_managed` | # of Seats Managed (BHAG) |
| `endpoints_managed` | # of Endpoints Managed |

---

## Error Handling

### Common Error Codes

| Code | Status | Description |
|------|--------|-------------|
| `INVALID_PERIOD` | 400 | Period format incorrect |
| `MISSING_DATA` | 400 | Required fields missing |
| `NO_DATA` | 404 | No metrics found for period |
| `PROTECTED_METRIC` | 403 | Cannot modify protected metric |
| `SERVER_ERROR` | 500 | Internal server error |

---

## Current Historical Values (Reference)

| Period | Endpoints | Seats (BHAG) |
|--------|-----------|--------------|
| 2025-10 | 575 | 524 |
| 2025-11 | 579 | 529 |
| 2025-12 | 587 | 537 |
| 2026-01 | 586 | 536 |

---

## Related Endpoints

- **Thresholds**: `GET/POST /api/qbr/thresholds` - Performance thresholds for KPIs
- **Test SmartNumbers**: `GET /api/qbr/test/smartnumbers?period=YYYY-QN` - No auth required (temporary)

---

**Version**: v1.38.7
**Last Updated**: January 13, 2026 17:09 UTC
**Maintainer**: ES Inventory Hub Team

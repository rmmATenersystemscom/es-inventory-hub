# QBR Metric Definitions API - Dashboard AI Reference

**Date**: January 23, 2026  
**From**: Database AI (ES Inventory Hub)  
**Version**: v1.38.9

---

## Overview

A new API endpoint is available that provides complete metric definitions with **live calculation breakdowns**. This enables rich tooltips/flyovers that show users exactly how calculated values are derived.

---

## Endpoint

```
GET /api/qbr/metric-definitions
```

**Authentication**: Not required (public endpoint)

**Base URL**: `https://db-api.enersystems.com:5400`

---

## Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `period` | string | No | - | Period for actual values (e.g., `2026-01`). If provided, returns live values and calculation displays. |
| `category` | string | No | - | Filter by category: `Revenue`, `Expenses`, `Profit`, `Support Tickets`, `Devices`, `Sales`, `General` |
| `include_intermediate` | boolean | No | `false` | Include intermediate metrics (e.g., `total_expenses_qb`, `payroll_total`) |
| `organization_id` | integer | No | `1` | Organization ID |

---

## Response Structure

```json
{
  "success": true,
  "data": {
    "period": "2026-01",
    "organization_id": 1,
    "count": 6,
    "metrics": [
      {
        "key": "other_expenses",
        "label": "All Other Expenses",
        "category": "Expenses",
        "format": "currency",
        "description": "Calculated: Total QB Expenses minus Employee Expense, Owner Comp, and Owner Taxes. Does NOT include COGS.",
        "source": "calculated",
        "is_editable": false,
        "is_calculated": true,
        "formula": "total_expenses_qb - employee_expense - owner_comp - owner_comp_taxes",
        "components": ["total_expenses_qb", "employee_expense", "owner_comp", "owner_comp_taxes"],
        "value": 38261.63,
        "component_values": {
          "total_expenses_qb": 88098.48,
          "employee_expense": 14248.85,
          "owner_comp": 22588.00,
          "owner_comp_taxes": 13000.00
        },
        "calculation_display": "$88,098.48 - $14,248.85 - $22,588.00 - $13,000.00 = $38,261.63"
      }
    ]
  }
}
```

---

## Field Definitions

| Field | Type | Description |
|-------|------|-------------|
| `key` | string | Metric identifier (e.g., `other_expenses`) |
| `label` | string | Display name (e.g., "All Other Expenses") |
| `category` | string | Grouping category |
| `format` | string | `currency`, `number`, or `percentage` |
| `description` | string | Human-readable description for tooltips |
| `source` | string | Data source: `quickbooks`, `calculated`, `manual`, `connectwise`, `ninja` |
| `is_editable` | boolean | Whether CFO can edit this value |
| `is_calculated` | boolean | Whether derived from other metrics |
| `formula` | string | Calculation formula (only for calculated metrics) |
| `components` | array | List of component metric keys (only for calculated metrics) |
| `value` | number | Actual value for the period (only if period specified) |
| `component_values` | object | Actual component values (only for calculated metrics with period) |
| `calculation_display` | string | **Pre-formatted calculation string for tooltips** |

---

## Implementing Enhanced Tooltips

### Recommended Tooltip Format

For calculated metrics, display the tooltip like this:

```
┌─────────────────────────────────────────────────────────┐
│  All Other Expenses: $38,261.63                         │
│                                                         │
│  $88,098.48 - $14,248.85 - $22,588.00 - $13,000.00     │
│  = $38,261.63                                           │
│                                                         │
│  (Total QB Expenses - Employee Expense - Owner Comp    │
│   - Owner Taxes)                                        │
└─────────────────────────────────────────────────────────┘
```

### Implementation Steps

1. **On page load**: Fetch metric definitions with the current period:
   ```
   GET /api/qbr/metric-definitions?period=2026-01
   ```

2. **Cache the response**: Store in state/context for tooltip access

3. **On hover/tooltip**: Look up the metric by `key` and display:
   - `label` as the title
   - `value` formatted according to `format`
   - `calculation_display` showing the actual calculation
   - `description` as additional context

4. **For non-calculated metrics**: Just show `label`, `value`, and `description`

---

## Example API Calls

### Get all expense metrics for January 2026:
```
GET /api/qbr/metric-definitions?period=2026-01&category=Expenses
```

### Get all metrics (no period - definitions only):
```
GET /api/qbr/metric-definitions
```

### Include intermediate metrics:
```
GET /api/qbr/metric-definitions?period=2026-01&include_intermediate=true
```

---

## Categories Available

| Category | Metrics |
|----------|---------|
| Support Tickets | reactive_tickets_created, reactive_tickets_closed, reactive_time_spent |
| Devices | endpoints_managed, seats_managed |
| Revenue | nrr, mrr, orr, product_sales, misc_revenue, total_revenue |
| Expenses | employee_expense, owner_comp, owner_comp_taxes, product_cogs, other_expenses, total_expenses |
| Profit | net_profit |
| General | employees, technical_employees, agreements |
| Sales | telemarketing_dials, first_time_appointments, prospects_to_pbr, new_agreements, new_mrr, lost_mrr |
| Intermediate | total_income, payroll_total, total_expenses_qb, uncategorized_expenses |

---

## Benefits

1. **Single source of truth** - Metric definitions maintained in API, not hardcoded in frontend
2. **Live calculations** - Users see actual values that make up each calculated metric
3. **Transparency** - CFO can verify calculations match expectations
4. **Self-debugging** - Easy to spot when a component value is incorrect
5. **Audit-friendly** - Clear paper trail for how values are derived

---

## Fixes Applied

This endpoint also fixes the "All Other Expenses" tooltip issue. The correct description is now:

> "Calculated: Total QB Expenses minus Employee Expense, Owner Comp, and Owner Taxes. **Does NOT include COGS.**"

COGS is NOT subtracted from other_expenses. It's only added in the total_expenses calculation.

---

**Maintainer**: ES Inventory Hub Team  
**Internal URL**: https://192.168.4.246:5400/api/qbr/metric-definitions
**External URL**: https://db-api.enersystems.com:5400/api/qbr/metric-definitions

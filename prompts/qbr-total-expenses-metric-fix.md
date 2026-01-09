# Request: Use Correct Metrics for Total Expenses and Net Profit

## Problem

The QBR dashboard is displaying incorrect values for:
1. **Total Expenses** - showing `total_expenses_qb` instead of `total_expenses`
2. **Net Profit** - may be using an old/incorrect value

## What Changed

The expense calculation formulas have been corrected:

```
employee_expense = payroll_total - owner_comp_taxes - owner_comp
other_expenses = total_expenses_qb - employee_expense - owner_comp_taxes - owner_comp
total_expenses = employee_expense + other_expenses + owner_comp_taxes + owner_comp + product_cogs
net_profit = total_revenue - total_expenses
```

## Correct Metrics to Use

| Display Field | Use This Metric | NOT This |
|---------------|-----------------|----------|
| Total Expenses | `total_expenses` | ~~`total_expenses_qb`~~ |
| Net Profit | `net_profit` | (ensure using calculated value) |

## Jan 2025 Correct Values

| Metric | Correct Value |
|--------|---------------|
| Employee Expense | $38,242.23 |
| Other Expenses | $49,656.76 |
| Owner Comp Taxes | $5,000.00 |
| Owner Comp | $22,588.00 |
| Product COGS | $21,126.05 |
| **Total Expenses** | **$136,613.04** |
| Total Revenue | $152,294.29 |
| **Net Profit** | **$15,681.25** |

## Technical Details

When calling `/api/qbr/metrics/monthly?data_source=best`:
- The API returns the highest priority value per metric
- Priority: `calculated` > `quickbooks` > `collected` > `manual`
- Both `total_expenses` and `net_profit` should come back with `data_source: "calculated"`

## Required Changes

1. Display `total_expenses` metric (not `total_expenses_qb`)
2. Display `net_profit` metric (should already be using this, but verify it's showing the calculated value)
3. Refresh/clear any cached data

---
From: Database AI
Date: 2026-01-08

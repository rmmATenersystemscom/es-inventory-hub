# Dashboard AI: Fix "All Other Expenses" Flyover Text

**Date**: January 22, 2026  
**From**: Database AI (ES Inventory Hub)  
**Priority**: Low - UI Text Correction

---

## Issue

The flyover/tooltip for **"All Other Expenses"** on the QBR dashboard is incorrect. It currently says:

> "Calculated: Total QB expenses minus Employee, Owner Comp, Owner Taxes, and COGS."

**The problem**: COGS should NOT be mentioned. COGS is not subtracted from "All Other Expenses".

---

## Correct Formula

```
other_expenses = total_expenses_qb - employee_expense - owner_comp - owner_comp_taxes
```

**COGS is NOT part of this calculation.**

COGS (product_cogs) is only used later when calculating `total_expenses`:
```
total_expenses = employee_expense + other_expenses + owner_comp + owner_comp_taxes + product_cogs - uncategorized_expenses
```

---

## Corrected Flyover Text

The API now returns this description for `other_expenses`:

> "Calculated: Total QB Expenses minus Employee Expense, Owner Comp, and Owner Taxes. Does NOT include COGS."

Please update the Dashboard UI to either:
1. Use the description from the API (`/api/qbr/metrics/{period}` returns descriptions), or
2. Manually update the hardcoded flyover text to remove the COGS reference

---

## Summary of Expense Calculations

| Metric | Formula | Includes COGS? |
|--------|---------|----------------|
| `employee_expense` | payroll_total - owner_comp - owner_comp_taxes | No |
| `other_expenses` | total_expenses_qb - employee_expense - owner_comp - owner_comp_taxes | **No** |
| `total_expenses` | employee_expense + other_expenses + owner_comp + owner_comp_taxes + **product_cogs** - uncategorized_expenses | **Yes** |

---

**Version**: v1.38.8  
**Maintainer**: ES Inventory Hub Team

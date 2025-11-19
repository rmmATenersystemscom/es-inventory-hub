# QBR System - Complete Data Status

**Last Updated**: November 16, 2025
**Total Historical Periods**: 23 months (2024-01 through 2025-11)

---

## Overall Summary

| Year | Periods | Total Metrics | Manual | Automated | Placeholders | Status |
|------|---------|---------------|--------|-----------|--------------|--------|
| 2024 | 12      | 240           | 204    | 36        | 0            | ✅ 100% Complete |
| 2025 | 11      | 288           | 251    | 37        | 82           | 🟨 71% Complete |

**Grand Total**: 528 metrics across 23 months

---

## 2024 Data (✅ 100% COMPLETE)

All 12 months have complete data from QBR_layout_2024.png:

### Metrics per Month (20 total)

**Automated from ConnectWise** (3):
- Reactive Tickets Created
- Reactive Tickets Closed
- Total Time on Reactive Tickets (hours)

**From Historical Spreadsheet** (17):
- Endpoints Managed
- Seats Managed
- Revenue (5): NRR, MRR, ORR, Product Sales, Total Revenue
- Expenses (5): Employee, Owner Comp, Owner Taxes, Product COGS, Other
- Total Expenses
- Net Profit
- Company Info (3): Employees, Technical Employees, Agreements

**No placeholders** - All real data ✅

---

## 2025 Data (🟨 71% COMPLETE)

### 2025-01 through 2025-09 (77% Complete Each)

**20 metrics with real data:**
- ✅ Operations (3): Tickets Created/Closed, Time Spent
- ✅ Endpoints/Seats (2): Endpoints Managed, Seats Managed
- ✅ Revenue (5): NRR, MRR, ORR, Product Sales, Total Revenue
- ✅ Expenses (5): Employee, Owner Comp, Owner Taxes, COGS, Other
- ✅ Total Expenses & Net Profit (2)
- ✅ Company Info (3): Employees, Technical Employees, Agreements

**6 placeholders (value=1) - Sales Metrics:**
- telemarketing_dials
- first_time_appointments
- prospects_to_pbr
- new_agreements
- new_mrr
- lost_mrr

### 2025-10 October (74% Complete)

**20 metrics with real data** (same as Jan-Sep)

**7 placeholders (value=1):**
- agreements (not visible in 2025 spreadsheet for Oct)
- All 6 sales metrics (same as above)

### 2025-11 November (22% Complete)

**6 metrics with real data:**
- ✅ Operations (3): Tickets Created (141), Tickets Closed (136), Time Spent (78.75)
- ✅ Endpoints (579) and Seats (524)

**21 placeholders (value=1) - Need Current Month Data:**

**Company (3):**
- employees
- technical_employees
- agreements

**Revenue (5):**
- nrr
- mrr
- orr
- product_sales
- total_revenue

**Expenses (5):**
- employee_expense
- owner_comp_taxes
- owner_comp
- product_cogs
- other_expenses

**Profit (1):**
- net_profit

**Total (1):**
- total_expenses

**Sales (6):**
- telemarketing_dials
- first_time_appointments
- prospects_to_pbr
- new_agreements
- new_mrr
- lost_mrr

---

## Data Sources

### Automated Collection (Running Daily at 10:30 PM CT)
- **ConnectWise**: Tickets created/closed, time spent
- **NinjaOne**: Endpoints managed, seats managed (Oct 2025 onwards)

### Manual Historical Backfill
- **QBR_layout.png** (2025 data): Revenue, expenses, profit, company info for Jan-Oct
- **QBR_layout_2024.png** (2024 data): Complete financial and operational data

### Placeholders (value=1)
- **Sales metrics**: Optional - if not tracked, can be deleted
- **November 2025**: Current month data - needs to be entered

---

## What to Do With Placeholders

### Option 1: Fill with Real Data
If you track sales metrics or have November data:

```bash
curl -k -X POST "https://localhost:5400/api/qbr/metrics/manual" \
  -H "Content-Type: application/json" \
  -d '{
    "period": "2025-11",
    "organization_id": 1,
    "metrics": [
      {"metric_name": "employees", "metric_value": 8.5},
      {"metric_name": "mrr", "metric_value": 110000.00},
      {"metric_name": "net_profit", "metric_value": 15000.00}
    ]
  }'
```

### Option 2: Delete Unused Metrics
If you don't track sales metrics:

```sql
DELETE FROM qbr_metrics_monthly
WHERE metric_value = 1.0
  AND notes = 'PLACEHOLDER - Replace with real data'
  AND metric_name IN (
    'telemarketing_dials',
    'first_time_appointments',
    'prospects_to_pbr',
    'new_agreements',
    'new_mrr',
    'lost_mrr'
  );
```

### Option 3: Leave Placeholders
Value=1 makes them visible but won't break calculations (SmartNumbers will just show unrealistic values)

---

## SmartNumbers Impact

The following SmartNumbers will be affected by placeholders:

### If Sales Metrics = 1:
- **Dials per Appointment**: Will show ~1 (unrealistic)
- **Sales Close %**: Will show 100% (unrealistic)
- **New MRR Growth**: Will show $1 (unrealistic)
- **MRR Churn**: Will show $1 (unrealistic)

### If November Data Missing:
- **Q4 2025 calculations** will be incomplete or inaccurate
- **Trend analysis** will show sharp drop in November

---

## Query Placeholders

```sql
-- See all placeholders
SELECT period, metric_name, metric_value
FROM qbr_metrics_monthly
WHERE metric_value = 1.0
  AND notes = 'PLACEHOLDER - Replace with real data'
ORDER BY period, metric_name;

-- Count placeholders by period
SELECT period, COUNT(*) as placeholder_count
FROM qbr_metrics_monthly
WHERE metric_value = 1.0
  AND notes = 'PLACEHOLDER - Replace with real data'
GROUP BY period
ORDER BY period;
```

---

## Recommendations

### Priority 1: Fill November 2025 (Current Month)
Enter November revenue, expenses, profit, and company data so Q4 calculations are accurate.

### Priority 2: Decide on Sales Metrics
If you don't track these, delete the placeholders to clean up the data.

### Priority 3: October Agreements
Add the October agreements count if you have it.

---

## System Health

✅ **2024**: Fully populated, no action needed
✅ **Automated Collection**: Running daily, working perfectly
🟨 **2025**: Mostly complete, just need current month + optional sales data
✅ **API**: All endpoints functional
✅ **SmartNumbers**: Calculating correctly (except where placeholders exist)

---

**Next Steps:**
1. Enter November 2025 data via API or database
2. Delete sales metric placeholders if not tracked
3. System will be 95%+ complete for meaningful QBR reporting!

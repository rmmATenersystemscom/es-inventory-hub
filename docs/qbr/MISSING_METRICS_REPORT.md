# QBR Missing Metrics Report

**Generated**: November 16, 2025
**Status**: Test data removed, placeholders (value=1) inserted for missing metrics

---

## Summary

### 2024 Data (100% Complete)
- All 12 months have complete data
- Total Expenses and Net Profit populated from historical spreadsheet
- ConnectWise automated data (tickets, hours) collected

### 2025 Data (Varies by Month)

| Month | Total Metrics | Real Data | Placeholders | % Complete |
|-------|---------------|-----------|--------------|------------|
| Jan   | 24            | 18        | 6            | 75.0%      |
| Feb   | 24            | 18        | 6            | 75.0%      |
| Mar   | 24            | 18        | 6            | 75.0%      |
| Apr   | 24            | 18        | 6            | 75.0%      |
| May   | 24            | 18        | 6            | 75.0%      |
| Jun   | 24            | 18        | 6            | 75.0%      |
| Jul   | 24            | 18        | 6            | 75.0%      |
| Aug   | 24            | 18        | 6            | 75.0%      |
| Sep   | 24            | 18        | 6            | 75.0%      |
| Oct   | 26            | 19        | 7            | 73.1%      |
| Nov   | 26            | 5         | 21           | 19.2%      |

---

## Missing Metrics Detail

### 2025-01 through 2025-09 (SALES METRICS ONLY)
**Missing**: 6 metrics per month

All of these months have complete revenue, expenses, profit, and company data from the QBR_layout.png spreadsheet.

**What's Missing** (Sales/Marketing metrics):
1. `telemarketing_dials` - Number of outbound calls made
2. `first_time_appointments` - First-time appointments scheduled
3. `prospects_to_pbr` - Prospects moved to PBR stage
4. `new_agreements` - New MSP agreements signed
5. `new_mrr` - New monthly recurring revenue added
6. `lost_mrr` - Monthly recurring revenue lost to churn

**What You Have** (From historical spreadsheet):
- ✓ Revenue: NRR, MRR, ORR, Product Sales, Total Revenue
- ✓ Expenses: Employee, Owner Comp, Owner Taxes, COGS, Other, Total
- ✓ Profit: Net Profit
- ✓ Company: Employees, Technical Employees, Agreements
- ✓ Operations: Tickets Created/Closed, Time Spent (automated)
- ✓ Endpoints/Seats: Managed counts (automated)

---

### 2025-10 (SALES METRICS + AGREEMENTS)
**Missing**: 7 metrics

Same 6 sales metrics as above, PLUS:
7. `agreements` - Number of active MSP agreements (Oct value not visible in spreadsheet)

---

### 2025-11 (ALMOST EVERYTHING)
**Missing**: 21 metrics

November 2025 only has automated collector data (ConnectWise + NinjaOne). All manual metrics need to be entered:

#### Company Metrics (3)
1. `employees` - Total headcount
2. `technical_employees` - Technical staff only
3. `agreements` - Active MSP agreements

#### Revenue Metrics (5)
4. `nrr` - Non-recurring revenue
5. `mrr` - Monthly recurring revenue
6. `orr` - Other recurring revenue
7. `product_sales` - Product sales revenue
8. `total_revenue` - Total monthly revenue

#### Expense Metrics (6)
9. `employee_expense` - Employee costs
10. `owner_comp_taxes` - Owner compensation taxes
11. `owner_comp` - Owner compensation
12. `product_cogs` - Product cost of goods sold
13. `other_expenses` - All other expenses
14. `total_expenses` - Total monthly expenses

#### Profit Metrics (1)
15. `net_profit` - Net profit for the month

#### Sales Metrics (6)
16. `telemarketing_dials` - Outbound calls
17. `first_time_appointments` - First appointments
18. `prospects_to_pbr` - Prospects to PBR
19. `new_agreements` - New agreements signed
20. `new_mrr` - New MRR added
21. `lost_mrr` - MRR lost to churn

**What You Have** (November):
- ✓ Operations: Tickets Created (141), Tickets Closed (136), Time Spent (78.75 hours)
- ✓ Endpoints: 579 managed
- ✓ Seats: 524 managed

---

## How to Fill Missing Data

### Option 1: Manual API Calls
Use the QBR manual metrics API endpoint:

```bash
curl -k -X POST "https://localhost:5400/api/qbr/metrics/manual" \
  -H "Content-Type: application/json" \
  -d '{
    "period": "2025-11",
    "organization_id": 1,
    "metrics": [
      {
        "metric_name": "employees",
        "metric_value": 8.5,
        "notes": "Total headcount"
      },
      {
        "metric_name": "mrr",
        "metric_value": 110000.00,
        "notes": "Monthly recurring revenue"
      }
    ]
  }'
```

### Option 2: Database Update
Update placeholders directly in the database:

```sql
UPDATE qbr_metrics_monthly
SET
    metric_value = 110000.00,
    notes = 'Actual MRR for November',
    updated_at = NOW()
WHERE period = '2025-11'
  AND metric_name = 'mrr'
  AND organization_id = 1
  AND vendor_id IS NULL;
```

### Option 3: Spreadsheet Import
If you have the data in a spreadsheet:
1. Export to CSV
2. Create a script similar to `backfill_qbr_manual_from_image.py`
3. Load the data via the API

---

## Query to View All Placeholders

```sql
-- See all metrics that need real data
SELECT
    period,
    metric_name,
    metric_value,
    notes
FROM qbr_metrics_monthly
WHERE metric_value = 1.0
  AND notes = 'PLACEHOLDER - Replace with real data'
ORDER BY period, metric_name;
```

---

## Current Status Summary

- **2024**: ✅ 100% complete (12 months × 5 metrics = 60 total)
- **2025 Jan-Sep**: 🟨 75% complete (need 6 sales metrics per month = 54 placeholders)
- **2025 Oct**: 🟨 73% complete (need 7 metrics = 7 placeholders)
- **2025 Nov**: 🟥 19% complete (need 21 metrics = 21 placeholders)

**Total Placeholders**: 82 metrics across 11 months (2025-01 through 2025-11)

---

## Next Steps

1. **Priority 1**: Fill November 2025 data (21 metrics) - current month
2. **Priority 2**: Fill October 2025 agreements count (1 metric)
3. **Priority 3**: Fill sales metrics for Jan-Oct 2025 (60 metrics) - if you track this data

Sales metrics are optional but useful for calculating SmartNumbers like:
- Sales Close %
- Dials per Appointment
- New MRR vs Lost MRR trends

If you don't track sales metrics, you can leave them at value=1 or delete them.

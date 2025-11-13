# QBR Calculation Reference

**Purpose**: Complete reference of all metric calculations and formulas for offline review and validation

**Date**: January 2025

**Source**: Based on `QBR2025_structured.md` and QBR2025.xlsx spreadsheet

---

## Table of Contents

1. [Monthly Input Metrics](#monthly-input-metrics)
2. [SmartNumbers / KPIs](#smartnumbers--kpis)
3. [Quarterly Aggregations](#quarterly-aggregations)
4. [Data Source Mapping](#data-source-mapping)
5. [Example Calculations](#example-calculations)

---

## Monthly Input Metrics

These are the raw metrics collected each month from various sources.

### Operations Metrics

| Metric | Data Type | Source | Collection Method |
|--------|-----------|--------|-------------------|
| # of Reactive Tickets Created | Count | ConnectWise | Query tickets by `dateEntered` within period, Help Desk board, parent tickets only |
| # of Reactive Tickets Closed | Count | ConnectWise | Query tickets by `closedDate` within period, Help Desk board, closed statuses |
| Total Time on Reactive Tickets | Hours (decimal) | ConnectWise | Sum `actualHours` from time entries within period, filtered to Help Desk tickets |
| # of Endpoints Managed | Count | NinjaOne | Query `device_snapshot` for latest snapshot in period, vendor_id=2 |

**ConnectWise Filtering**:
```python
# Tickets Created
conditions = 'dateEntered>=[{start}] AND dateEntered<=[{end}] AND board/name="Help Desk" AND parentTicketId = null'

# Tickets Closed
conditions = 'status/name IN (">Closed",">Closed - No response","Closed") AND closedDate>=[{start}] AND closedDate<=[{end}] AND board/name="Help Desk" AND parentTicketId = null'

# Time on Tickets
# 1. Get time entries: dateEntered>=[{start}] AND dateEntered<=[{end}] AND chargeToType="ServiceTicket"
# 2. Extract ticket IDs from time entries
# 3. Query tickets in batches to identify Help Desk tickets
# 4. Sum actualHours only for Help Desk tickets
```

**NinjaOne Query**:
```sql
SELECT COUNT(DISTINCT device_identity_id)
FROM device_snapshot
WHERE vendor_id = 2
  AND snapshot_date = (
    SELECT MAX(snapshot_date)
    FROM device_snapshot
    WHERE vendor_id = 2
      AND snapshot_date >= :period_start
      AND snapshot_date <= :period_end
  );
```

### Revenue Metrics

| Metric | Data Type | Source | Collection Method |
|--------|-----------|--------|-------------------|
| Non-recurring Revenue (NRR) | Dollar amount | QuickBooks | *Future implementation* |
| Monthly Recurring Revenue (MRR) | Dollar amount | QuickBooks | *Future implementation* |
| Other Recurring Revenue (ORR) | Dollar amount | QuickBooks | *Future implementation* |
| Product Sales | Dollar amount | QuickBooks | *Future implementation* |
| Miscellaneous revenue | Dollar amount | QuickBooks | *Future implementation* |
| Total Revenue | Dollar amount | Calculated | SUM(NRR, MRR, ORR, Product Sales, Misc) |

**Calculation**:
```python
total_revenue = nrr + mrr + orr + product_sales + misc_revenue
```

### Expense Metrics

| Metric | Data Type | Source | Collection Method |
|--------|-----------|--------|-------------------|
| Employee Expense | Dollar amount | QuickBooks | *Future implementation* |
| Owner Comp to pay QTR est taxes | Dollar amount | QuickBooks | *Future implementation* |
| Owner Compensation | Dollar amount | QuickBooks | *Future implementation* |
| Product Cost of Goods Sold (COGS) | Dollar amount | QuickBooks | *Future implementation* |
| All Other Expenses | Dollar amount | QuickBooks | *Future implementation* |
| Total Expenses | Dollar amount | Calculated | SUM(all expense categories) |

**Calculation**:
```python
total_expenses = employee_expense + owner_comp_taxes + owner_comp + cogs + other_expenses
```

### Profit Metrics

| Metric | Data Type | Source | Collection Method |
|--------|-----------|--------|-------------------|
| Net Profit Dollars | Dollar amount | Calculated | Total Revenue - Total Expenses |

**Calculation**:
```python
net_profit = total_revenue - total_expenses
```

### General Information

| Metric | Data Type | Source | Collection Method |
|--------|-----------|--------|-------------------|
| # of Employees | Count | Manual/Internal | Manual entry or HR system |
| # of Technical Employees | Count | Manual/Internal | Manual entry or HR system |
| # of Seats Managed | Count | NinjaOne | Similar to Endpoints Managed |
| # of Manage Services Agreements | Count | Manual/Internal | Manual entry or contract system |

### Sales Metrics

| Metric | Data Type | Source | Collection Method |
|--------|-----------|--------|-------------------|
| # of Telemarketing Dials | Count | Manual/CRM | Manual entry or CRM system |
| # of First Time Appointments (FTA) | Count | Manual/CRM | Manual entry or CRM system |
| # of Prospects to Hit PBR | Count | Manual/CRM | Manual entry or CRM system |
| # of New Agreements | Count | Manual/CRM | Manual entry or CRM system |
| New MRR | Dollar amount | Manual/CRM | Manual entry or CRM system |
| Lost MRR | Dollar amount | Manual/CRM | Manual entry or CRM system |

---

## SmartNumbers / KPIs

SmartNumbers are calculated KPIs derived from the monthly input metrics.

### Operations SmartNumbers

#### 1. Reactive Tickets / Tech / Month (closed)

**Formula**:
```
tickets_per_tech = tickets_closed / tech_count / months
```

**For Quarterly** (3 months):
```python
tickets_per_tech = total_tickets_closed_q1 / avg_tech_count_q1 / 3
```

**Example**:
- Q1 2025: 1,080 tickets closed, average 5.5 techs
- `1080 / 5.5 / 3 = 65.45 tickets per tech per month`

**Source Metrics**:
- Numerator: `# of Reactive Tickets Closed`
- Denominator: `# of Technical Employees`

---

#### 2. Total Close %

**Formula**:
```
close_pct = tickets_closed / tickets_created
```

**Example**:
- Q1 2025: 1,080 closed, 1,081 created
- `1080 / 1081 = 0.9991 = 99.91%`

**Source Metrics**:
- Numerator: `# of Reactive Tickets Closed`
- Denominator: `# of Reactive Tickets Created`

**Notes**: >100% is possible if closing tickets from previous period

---

#### 3. Reactive Tickets / Endpoint / Month (new)

**Formula** (for quarterly):
```
tickets_per_endpoint = tickets_created_quarter / 3 / avg_endpoints_quarter
```

**Example**:
- Q1 2025: 1,081 created, average 597 endpoints
- `1081 / 3 / 597 = 0.603 tickets per endpoint per month`

**Source Metrics**:
- Numerator: `# of Reactive Tickets Created`
- Denominator: `# of Endpoints Managed`

---

#### 4. RHEM (Reactive Hours / Endpoint / Month)

**Formula** (for quarterly):
```
rhem = hours_quarter / avg_endpoints_quarter / 3
```

**Example**:
- Q1 2025: 452.08 hours, average 597 endpoints
- `452.08 / 597 / 3 = 0.252 hours per endpoint per month`

**Source Metrics**:
- Numerator: `Total Time on Reactive Tickets`
- Denominator: `# of Endpoints Managed`

---

#### 5. Average Resolution Time

**Formula**:
```
avg_resolution_time = total_hours / tickets_closed
```

**Example**:
- Q1 2025: 452.08 hours, 1,080 tickets closed
- `452.08 / 1080 = 0.419 hours = 25 minutes`

**Source Metrics**:
- Numerator: `Total Time on Reactive Tickets`
- Denominator: `# of Reactive Tickets Closed`

---

#### 6. Reactive Service %

**Formula**:
```
reactive_service_pct = (hours_quarter / 3) / (avg_tech_count * 167)
```

**Notes**:
- 167 = assumed monthly working hours per tech (40 hours/week * 4.175 weeks/month)
- Divide by 3 to get monthly average from quarterly total

**Example**:
- Q1 2025: 452.08 hours, average 5.5 techs
- `(452.08 / 3) / (5.5 * 167) = 0.164 = 16.4%`

**Source Metrics**:
- Numerator: `Total Time on Reactive Tickets`
- Denominator: `# of Technical Employees`

---

### Profit SmartNumbers

#### 7. Net Profit %

**Formula**:
```
net_profit_pct = net_profit / total_revenue
```

**Example**:
- Q1 2025: Net Profit $54,001, Total Revenue $515,488
- `54001 / 515488 = 0.1048 = 10.48%`

**Source Metrics**:
- Numerator: `Net Profit Dollars`
- Denominator: `Total Revenue`

---

### Revenue SmartNumbers

#### 8. % of Revenue from Services

**Formula**:
```
service_revenue_pct = (nrr + mrr) / total_revenue
```

**Example**:
- Q1 2025: NRR $32,280 + MRR $329,960 = $362,240
- Total Revenue $515,488
- `362240 / 515488 = 0.703 = 70.3%`

**Source Metrics**:
- Numerator: `Non-recurring Revenue` + `Monthly Recurring Revenue`
- Denominator: `Total Revenue`

---

#### 9. % of Services from MRR

**Formula**:
```
mrr_pct = mrr / (nrr + mrr)
```

**Example**:
- Q1 2025: MRR $329,960, Service Revenue $362,240
- `329960 / 362240 = 0.911 = 91.1%`

**Source Metrics**:
- Numerator: `Monthly Recurring Revenue`
- Denominator: `Non-recurring Revenue` + `Monthly Recurring Revenue`

---

### Leverage SmartNumbers

#### 10. Annualized Service Revenue / Employee

**Formula** (for quarterly):
```
annual_service_rev_per_employee = (service_revenue_quarter / avg_employees) * 4
```

**Example**:
- Q1 2025: Service Revenue $362,240, average 8.5 employees
- `(362240 / 8.5) * 4 = $170,582 annualized`

**Source Metrics**:
- Numerator: `Non-recurring Revenue` + `Monthly Recurring Revenue`
- Denominator: `# of Employees`

---

#### 11. Annualized Service Revenue / Technical Employee

**Formula** (for quarterly):
```
annual_service_rev_per_tech = (service_revenue_quarter / avg_tech_employees) * 4
```

**Example**:
- Q1 2025: Service Revenue $362,240, average 5.5 tech employees
- `(362240 / 5.5) * 4 = $263,265 annualized`

**Source Metrics**:
- Numerator: `Non-recurring Revenue` + `Monthly Recurring Revenue`
- Denominator: `# of Technical Employees`

---

#### 12. Average AISP

**AISP** = Average Income per Seat/Position

**Formula** (for quarterly):
```
avg_aisp = mrr_quarter / avg_seats / 3
```

**Example**:
- Q1 2025: MRR $329,960, average 546 seats
- `329960 / 546 / 3 = $201.43 per seat per month`

**Source Metrics**:
- Numerator: `Monthly Recurring Revenue`
- Denominator: `# of Seats Managed`

---

#### 13. Average MRR

**Average MRR per Agreement**

**Formula** (for quarterly):
```
avg_mrr_per_agreement = mrr_quarter / avg_agreements / 3
```

**Example**:
- Q1 2025: MRR $329,960, average 37 agreements
- `329960 / 37 / 3 = $2,972 per agreement per month`

**Source Metrics**:
- Numerator: `Monthly Recurring Revenue`
- Denominator: `# of Manage Services Agreements`

---

### Sales SmartNumbers

#### 14. New MRR added

**Formula**:
```
new_mrr = sum of new MRR for quarter
```

**Example**:
- Q1 2025: $0 + $813 + $2,089 = $2,902

**Source Metrics**:
- `New MRR` (from monthly input)

---

#### 15. Lost MRR (churn)

**Formula**:
```
lost_mrr = sum of lost MRR for quarter
```

**Example**:
- Q1 2025: $0 + $182 + $2,354 = $2,536

**Source Metrics**:
- `Lost MRR` (from monthly input)

---

#### 16. Net MRR gain

**Formula**:
```
net_mrr_gain = new_mrr - lost_mrr
```

**Example**:
- Q1 2025: $2,902 - $2,536 = $366

**Source Metrics**:
- `New MRR`
- `Lost MRR`

---

#### 17. # of dials / appointment

**Formula** (for quarterly):
```
dials_per_appointment = total_dials_quarter / total_fta_quarter
```

**Example**:
- Q1 2025: 0 dials, 0 FTAs
- `N/A` (avoid division by zero)

**Source Metrics**:
- Numerator: `# of Telemarketing Dials`
- Denominator: `# of First Time Appointments (FTA)`

---

#### 18. Sales Call Close %

**Formula** (for quarterly):
```
sales_close_pct = total_new_agreements / total_fta
```

**Example**:
- Q1 2025: 1 new agreement, 2 FTAs
- `1 / 2 = 0.50 = 50%`

**Source Metrics**:
- Numerator: `# of New Agreements`
- Denominator: `# of First Time Appointments (FTA)`

---

## Quarterly Aggregations

Quarterly metrics are aggregated from monthly metrics.

### Aggregation Methods

| Metric Type | Aggregation Method | Example |
|-------------|-------------------|---------|
| Counts (Tickets, Endpoints) | **SUM** of 3 months | Jan: 354 + Feb: 294 + Mar: 433 = 1,081 |
| Hours | **SUM** of 3 months | Jan: 146.46 + Feb: 138.30 + Mar: 167.32 = 452.08 |
| Revenue/Expenses | **SUM** of 3 months | Jan: $152K + Feb: $187K + Mar: $176K = $515K |
| Counts (Employees, Agreements) | **AVERAGE** of 3 months | Jan: 8.5 + Feb: 8.5 + Mar: 8.5 = 8.5 avg |

### Quarterly Period Mapping

- **Q1**: January + February + March
- **Q2**: April + May + June
- **Q3**: July + August + September
- **Q4**: October + November + December

---

## Data Source Mapping

Complete mapping of metrics to data sources:

### NinjaOne (vendor_id = 2)
- # of Endpoints Managed
- # of Seats Managed

### ConnectWise (vendor_id = 3)
- # of Reactive Tickets Created
- # of Reactive Tickets Closed
- Total Time on Reactive Tickets
- # of Telemarketing Dials *(if tracked in ConnectWise)*
- # of First Time Appointments *(if tracked in ConnectWise)*
- # of Prospects to Hit PBR *(if tracked in ConnectWise)*
- # of New Agreements *(if tracked in ConnectWise)*

### QuickBooks (vendor_id = 4) - *Future*
- Non-recurring Revenue (NRR)
- Monthly Recurring Revenue (MRR)
- Other Recurring Revenue (ORR)
- Product Sales
- Miscellaneous revenue
- Employee Expense
- Owner Comp to pay QTR est taxes
- Owner Compensation
- Product Cost of Goods Sold (COGS)
- All Other Expenses

### Manual Entry (data_source = 'manual')
- # of Employees
- # of Technical Employees
- # of Manage Services Agreements
- Sales activity metrics (if not in ConnectWise)
- Any missing or corrected data

---

## Example Calculations

### Example 1: Calculate Q1 2025 SmartNumbers

**Given Monthly Metrics** (January, February, March):

| Metric | Jan | Feb | Mar | Q1 Total/Avg |
|--------|-----|-----|-----|--------------|
| Reactive Tickets Created | 354 | 294 | 433 | 1,081 |
| Reactive Tickets Closed | 355 | 294 | 431 | 1,080 |
| Total Time on Reactive Tickets | 146.46 | 138.30 | 167.32 | 452.08 |
| Endpoints Managed | 597 | 594 | 591 | 594 (avg) |
| Technical Employees | 5.5 | 5.5 | 5.5 | 5.5 (avg) |
| Total Revenue | $152,294 | $187,085 | $176,109 | $515,488 |
| Total Expenses | $137,499 | $177,096 | $146,891 | $461,486 |
| Net Profit | $14,795 | $9,989 | $29,218 | $54,002 |
| MRR | $109,682 | $110,274 | $110,003 | $329,959 |
| NRR | -$2,044 | $10,877 | $23,446 | $32,279 |

**Calculate SmartNumbers**:

1. **Reactive Tickets / Tech / Month (closed)**:
   ```
   1,080 / 5.5 / 3 = 65.45 tickets/tech/month
   ```

2. **Total Close %**:
   ```
   1,080 / 1,081 = 0.9991 = 99.91%
   ```

3. **Reactive Tickets / Endpoint / Month (new)**:
   ```
   1,081 / 3 / 594 = 0.606 tickets/endpoint/month
   ```

4. **RHEM (Reactive Hours / Endpoint / Month)**:
   ```
   452.08 / 594 / 3 = 0.254 hours/endpoint/month
   ```

5. **Average Resolution Time**:
   ```
   452.08 / 1,080 = 0.419 hours = 25.1 minutes
   ```

6. **Reactive Service %**:
   ```
   (452.08 / 3) / (5.5 * 167) = 0.164 = 16.4%
   ```

7. **Net Profit %**:
   ```
   54,002 / 515,488 = 0.1048 = 10.48%
   ```

8. **% of Revenue from Services**:
   ```
   (32,279 + 329,959) / 515,488 = 0.703 = 70.3%
   ```

9. **% of Services from MRR**:
   ```
   329,959 / (32,279 + 329,959) = 0.911 = 91.1%
   ```

---

### Example 2: Validate Calculation with SQL

**Query to Calculate Tickets per Tech**:
```sql
WITH quarterly_data AS (
  SELECT
    SUM(CASE WHEN metric_name = 'Reactive Tickets Closed' THEN metric_value ELSE 0 END) AS tickets_closed,
    AVG(CASE WHEN metric_name = 'Technical Employees' THEN metric_value ELSE NULL END) AS avg_techs
  FROM qbr_metrics_monthly
  WHERE period IN ('2025-01', '2025-02', '2025-03')
    AND organization_id = 1
)
SELECT
  tickets_closed / avg_techs / 3 AS tickets_per_tech_per_month
FROM quarterly_data;
```

**Expected Result**: `65.45`

---

### Example 3: Handle Division by Zero

**Scenario**: Calculate "# of dials / appointment" when FTAs = 0

```python
def calculate_dials_per_appointment(dials: float, ftas: float) -> Optional[float]:
    """Calculate dials per appointment, handling zero division"""
    if ftas == 0 or ftas is None:
        return None  # Return NULL instead of error
    return dials / ftas
```

**Database Storage**: Store `NULL` for SmartNumbers that cannot be calculated

---

## Validation Checklist

When implementing calculations, validate:

- [ ] All 18 SmartNumbers calculated
- [ ] Division by zero handled (return NULL)
- [ ] Quarterly aggregations correct (sum vs average)
- [ ] Formulas match spreadsheet formulas
- [ ] Manual calculation matches code output
- [ ] Edge cases handled (NULL inputs, zero values)
- [ ] Precision sufficient (use NUMERIC(12,2) or NUMERIC(12,4))
- [ ] Units consistent (hours, dollars, percentages)

---

## Summary

This document provides complete calculation reference for all QBR metrics and SmartNumbers. Use this for:
- Implementation validation
- Manual spot-checking
- Debugging calculation discrepancies
- Offline review of accuracy

---

---

**Version**: v1.21.0
**Last Updated**: November 13, 2025 03:24 UTC
**Maintainer**: ES Inventory Hub Team
**Status**: Complete
**Related Documents**:
- `QBR2025_structured.md` - Source metric definitions
- `PLANNING_DECISIONS.md` - Architectural decisions
- `IMPLEMENTATION_GUIDE.md` - Implementation details

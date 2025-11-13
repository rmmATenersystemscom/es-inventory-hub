# QBR 2025 – Structured Extraction

## 1) MONTHLY INPUT METRICS (from `MonthlyINPUT`)

### Operations
| Metric | Data Type | Raw or Calculated |
|---|---|---|
| # of Reactive Tickets Created | count | raw input |
| # of Reactive Tickets Closed | count | raw input |
| Total Time on Reactive Tickets | hours | raw input |
| # of Endpoints Managed | count | calculated |

### Revenue
| Metric | Data Type | Raw or Calculated |
|---|---|---|
| Non-recurring Revenue (NRR) | dollar amount | raw input |
| Monthly Recurring Revenue (MRR) | dollar amount | calculated |
| Other Recurring Revenue (ORR) | dollar amount | calculated |
| Product Sales | dollar amount | calculated |
| Miscellaneous revenue | dollar amount | raw input |
| Total Revenue | dollar amount | calculated |

### Expenses
| Metric | Data Type | Raw or Calculated |
|---|---|---|
| Employee Expense | dollar amount | calculated |
| Owner Comp to pay QTR est taxes | count | calculated |
| Owner Compensation | dollar amount | calculated |
| Product Cost of Goods Sold (COGS) | dollar amount | raw input |
| All Other Expenses | dollar amount | calculated |
| Total Expenses | dollar amount | calculated |

### Profit
| Metric | Data Type | Raw or Calculated |
|---|---|---|
| Net Profit Dollars | dollar amount | calculated |

### General Information
| Metric | Data Type | Raw or Calculated |
|---|---|---|
| # of Employees | count | raw input |
| # of Technical Employees | count | raw input |
| # of Seats Managed | count | raw input |
| # of Manage Services Agreements | count | raw input |

### Sales
| Metric | Data Type | Raw or Calculated |
|---|---|---|
| # of Telemarketing Dials | count | raw input |
| # of First Time Appointments (FTA) | count | raw input |
| # of Prospects to Hit PBR | count | raw input |
| # of New Agreements | count | raw input |
| New MRR | dollar amount | raw input |
| Lost MRR | dollar amount | raw input |
| MSP turning point | count | calculated |
| $ Difference | dollar amount | calculated |
| Cash Reserve | dollar amount | raw input |
| A/R >90 days | count | raw input |
| Ave Expenses for  2023 | dollar amount | raw input |
| Cash Reserve/Ave expenses | dollar amount | calculated |
| Note Ave Expenses for 2022 | dollar amount | raw input |
| Ave Expenses for  2017 | dollar amount | calculated |
| Ave Expenses for  2018 | dollar amount | calculated |
| Ave Expenses for  2019 | dollar amount | raw input |
| Ave Expenses for  2020 | dollar amount | raw input |
| Ave Expenses for  2021 | dollar amount | raw input |
| Labor Efficiency Ratio (>2.0) | ratio | calculated |
| management labor efficiency ratio | ratio | raw input |
| Gross Margin | count | calculated |
| Gross Margin per employee | dollar amount | calculated |

## 2) SMARTNUMBERS / KPIs (from `SmartNumbers2025`)
### Operations
| SmartNumber | Formula (Q1 col) | Uses Inputs |
|---|---|---|
| Reactive Tickets / Tech / Month (closed) | `=IF(ISERROR('QBR 2025'!C10/'QBR 2025'!C35/3),"--",'QBR 2025'!C10/'QBR 2025'!C35/3)` | # of Reactive Tickets Closed, # of Technical Employees |
| Total Close % | `=IF(ISERROR('QBR 2025'!C10/'QBR 2025'!C9),"--",'QBR 2025'!C10/'QBR 2025'!C9)` | # of Reactive Tickets Closed, # of Reactive Tickets Created |
| Reactive Tickets / Endpoint / Month (new) | `=IF(ISERROR('QBR 2025'!C9/3/'QBR 2025'!C12),"--",'QBR 2025'!C9/3/'QBR 2025'!C12)` | # of Endpoints Managed, # of Reactive Tickets Created |
| RHEM (Reactive Hours / Endpoint / Month) | `=IF(ISERROR('QBR 2025'!C11/'QBR 2025'!C12/3),"--",'QBR 2025'!C11/'QBR 2025'!C12/3)` | # of Endpoints Managed, Total Time on Reactive Tickets |
| Average Resolution Time | `=IF(ISERROR('QBR 2025'!C11/'QBR 2025'!C10),"--",'QBR 2025'!C11/'QBR 2025'!C10)` | # of Reactive Tickets Closed, Total Time on Reactive Tickets |
| Reactive Service % | `=IF(ISERROR('QBR 2025'!C11/3/('QBR 2025'!C35*167)),"--",'QBR 2025'!C11/3/('QBR 2025'!C35*167))` | # of Technical Employees, Total Time on Reactive Tickets |

### Profit
| SmartNumber | Formula (Q1 col) | Uses Inputs |
|---|---|---|
| Net Profit % | `=IF(ISERROR('QBR 2025'!C31/'QBR 2025'!C20),"--",'QBR 2025'!C31/'QBR 2025'!C20)` | Net Profit Dollars, Total Revenue |

### Revenue
| SmartNumber | Formula (Q1 col) | Uses Inputs |
|---|---|---|
| % of Revenue from Services | `=IF(ISERROR(SUM('QBR 2025'!C15:C16)/'QBR 2025'!C20),"--",SUM('QBR 2025'!C15:C16)/'QBR 2025'!C20)` | Non-recurring Revenue (NRR), Total Revenue |
| % of Services from MRR | `=IF(ISERROR('QBR 2025'!C16/('QBR 2025'!C15+'QBR 2025'!C16)),"--",'QBR 2025'!C16/('QBR 2025'!C15+'QBR 2025'!C16))` | Monthly Recurring Revenue (MRR), Non-recurring Revenue (NRR) |

### Leverage
| SmartNumber | Formula (Q1 col) | Uses Inputs |
|---|---|---|
| Annualized Service Revenue / Employee | `=IF(ISERROR(SUM('QBR 2025'!C$15:C$17)/'QBR 2025'!C$34*4),"--",SUM('QBR 2025'!C$15:C$17)/'QBR 2025'!C$34*4)` |  |
| Annualized Service Revenue / Technical Employee | `=IF(ISERROR(SUM('QBR 2025'!C$15:C$17)/'QBR 2025'!C$35*4),"--",SUM('QBR 2025'!C$15:C$17)/'QBR 2025'!C$35*4)` |  |
| Average AISP | `=IF(ISERROR('QBR 2025'!C16/'QBR 2025'!C36/3),"--",'QBR 2025'!C16/'QBR 2025'!C36/3)` | # of Seats Managed, Monthly Recurring Revenue (MRR) |
| Average MRR | `=IF(ISERROR('QBR 2025'!C16/'QBR 2025'!C37/3),"--",'QBR 2025'!C16/'QBR 2025'!C37/3)` | # of Manage Services Agreements, Monthly Recurring Revenue (MRR) |

### Sales
| SmartNumber | Formula (Q1 col) | Uses Inputs |
|---|---|---|
| New MRR added | `=+'QBR 2025'!C44` | New MRR |
| Lost MRR (churn) | `=+'QBR 2025'!C45` | Lost MRR |
| Net MRR gain | `=B28-B29` |  |
| # of dials / appointment | `=IF(ISERROR('QBR 2025'!C40/'QBR 2025'!C41),"--",'QBR 2025'!C40/'QBR 2025'!C41)` | # of First Time Appointments (FTA), # of Telemarketing Dials |
| # of first appointments | `='QBR 2025'!C41` | # of First Time Appointments (FTA) |
| Sales Call Close % | `=IF(ISERROR('QBR 2025'!C43/'QBR 2025'!C41),"--",'QBR 2025'!C43/'QBR 2025'!C41)` | # of First Time Appointments (FTA), # of New Agreements |

## 3) FORMULAS & CALCULATIONS
Key calculated fields detected in `MonthlyINPUT` (Jan column formulas shown):
| Row | Name | Formula |
|---:|---|---|
| 12 | # of Endpoints Managed | `=546+51` |
| 16 | Monthly Recurring Revenue (MRR) | `=105668.31+4013.95` |
| 17 | Other Recurring Revenue (ORR) | `=68.54+25587.02+1079.93+613.32+830.95` |
| 18 | Product Sales | `=152294.29-C17-C16-C15` |
| 20 | Total Revenue | `=SUM(C15:C19)` |
| 23 | Employee Expense | `=66330.23-C24-C25` |
| 24 | Owner Comp to pay QTR est taxes | `=5000` |
| 25 | Owner Compensation | `=(67500+35600)/12+(1996.8)+12000` |
| 27 | All Other Expenses | `=(116373.11)-C23-C24-C25` |
| 28 | Total Expenses | `=SUM(C23:C27)` |
| 31 | Net Profit Dollars | `=C20-C28` |
| 48 | MSP turning point | `=(C15+C16)/(C23+C25+C27)` |
| 49 | $ Difference | `=(C15+C16)-(C23+C24+C25+C27)` |
| 54 | Cash Reserve/Ave expenses | `=C51/C53` |
| 57 | Ave Expenses for  2017 | `=1133556.01/12` |
| 58 | Ave Expenses for  2018 | `=1185695.14/12` |
| 63 | Labor Efficiency Ratio (>2.0) | `=(C20-C26)/(C23+C25)` |
| 66 | Gross Margin | `=(C20-C26)/C20` |
| 74 | Gross Margin per employee | `=(C20-C26)/C34` |

## 4) DATA SOURCES (inferred)
- **NinjaOne / RMM**: `# of Endpoints Managed`, `# of Seats Managed` (if tracked as licenses/seats).
- **ConnectWise Manage / PSA**: `# of Reactive Tickets Created`, `# of Reactive Tickets Closed`, `Total Time on Reactive Tickets (hrs)`, `# of New Agreements`, and Sales activity counts (`# of Telemarketing Dials`, `# of First Time Appointments`, `# of Prospects to Hit PBR`).
- **QuickBooks (Accounting)**: Revenue rows (`NRR`, `MRR`, `ORR`, `Product Sales`, `Miscellaneous revenue`, `Total Revenue`), Expense rows (`Employee Expense`, `Owner Comp`, `COGS`, `All Other Expenses`, `Total Expenses`), and `Net Profit Dollars`.
- **Internal/Admin**: `# of Employees`, `# of Technical Employees` (HR/staffing), `Cash Reserve`, and historical averages rows (`Ave Expenses for 2020/2021/2023`).

## 5) KEY OBSERVATIONS
- SmartNumbers are quarterly and reference **`QBR 2025`** row-aligned inputs (e.g., rows 9–12 for ops metrics).
- Many formulas normalize by **3** to convert monthly values into per-month-of-quarter KPIs (e.g., tickets / 3 / endpoints).
- **Gross Margin**, **Labor Efficiency Ratio**, and **Gross Margin per employee** use standard accounting relationships with rows 20 (Total Revenue), 26 (COGS), 28 (Total Expenses), 31 (Net Profit), and 34 (Employees).
- Sales block includes **New/Lost MRR** (dollars) and **activity counts**; these likely map to CW opportunities/agreements or manual entry.
- References to `2024byMonth` provide historical comparisons for Revenue, Expenses, and Profit lines.
- There are open placeholders for **Cash Reserve**, **A/R >90 days**, and **Cash Reserve/Ave expenses** ratios — indicating planned inputs/integration points.
#!/usr/bin/env python3
"""
Backfill Complete 2024 QBR Data from QBR_layout_2024.png

This backfills all manual metrics for 2024 except ConnectWise data
which is already collected automatically.
"""

import sys
import requests

# Disable SSL warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

API_BASE = "https://localhost:5400/api/qbr"
ORGANIZATION_ID = 1

# Complete 2024 data extracted from QBR_layout_2024.png
HISTORICAL_DATA_2024 = {
    "2024-01": {
        # Endpoints/Seats
        "endpoints_managed": 519,
        "seats_managed": 467,
        # Revenue
        "nrr": 4623.00,
        "mrr": 92242.00,
        "orr": 16404.00,
        "product_sales": 5491.00,
        "total_revenue": 118759.00,
        # Expenses (we already have total_expenses, but adding breakdown)
        "employee_expense": 36997.00,
        "owner_comp_taxes": 5000.00,
        "owner_comp": 20425.00,
        "product_cogs": 11467.00,
        "other_expenses": 45133.00,
        # total_expenses: 119022.00 (already have)
        # net_profit: -263.00 (already have)
        # Company
        "employees": 8.5,
        "technical_employees": 5.5,
        "agreements": 34.0,
    },
    "2024-02": {
        "endpoints_managed": 523,
        "seats_managed": 472,
        "nrr": 3378.00,
        "mrr": 95443.00,
        "orr": 63385.00,
        "product_sales": 16760.00,
        "total_revenue": 178967.00,
        "employee_expense": 36923.00,
        "owner_comp_taxes": 5000.00,
        "owner_comp": 20425.00,
        "product_cogs": 72800.00,
        "other_expenses": 39402.00,
        "employees": 8.5,
        "technical_employees": 5.5,
        "agreements": 34.0,
    },
    "2024-03": {
        "endpoints_managed": 544,
        "seats_managed": 493,
        "nrr": 18526.00,
        "mrr": 100103.00,
        "orr": 15658.00,
        "product_sales": 13289.00,
        "total_revenue": 147576.00,
        "employee_expense": 39106.00,
        "owner_comp_taxes": 5000.00,
        "owner_comp": 20425.00,
        "product_cogs": 14691.00,
        "other_expenses": 42576.00,
        "employees": 8.5,
        "technical_employees": 5.5,
        "agreements": 35.0,
    },
    "2024-04": {
        "endpoints_managed": 552,
        "seats_managed": 500,
        "nrr": 10163.00,
        "mrr": 101762.00,
        "orr": 16934.00,
        "product_sales": 19326.00,
        "total_revenue": 148185.00,
        "employee_expense": 38446.00,
        "owner_comp_taxes": 5000.00,
        "owner_comp": 20425.00,
        "product_cogs": 22940.00,
        "other_expenses": 53141.00,
        "employees": 8.5,
        "technical_employees": 5.5,
        "agreements": 35.0,
    },
    "2024-05": {
        "endpoints_managed": 555,
        "seats_managed": 504,
        "nrr": 7234.00,
        "mrr": 101988.00,
        "orr": 17163.00,
        "product_sales": 17635.00,
        "total_revenue": 144020.00,
        "employee_expense": 38412.00,
        "owner_comp_taxes": 5000.00,
        "owner_comp": 20425.00,
        "product_cogs": 20652.00,
        "other_expenses": 53834.00,
        "employees": 8.5,
        "technical_employees": 5.5,
        "agreements": 35.0,
    },
    "2024-06": {
        "endpoints_managed": 553,
        "seats_managed": 504,
        "nrr": 2081.00,
        "mrr": 100845.00,
        "orr": 16470.00,
        "product_sales": 28947.00,
        "total_revenue": 148344.00,
        "employee_expense": 37761.00,
        "owner_comp_taxes": 5000.00,
        "owner_comp": 20425.00,
        "product_cogs": 33620.00,
        "other_expenses": 43978.00,
        "employees": 8.5,
        "technical_employees": 5.5,
        "agreements": 34.0,
    },
    "2024-07": {
        "endpoints_managed": 545,
        "seats_managed": 496,
        "nrr": 4115.00,
        "mrr": 100419.00,
        "orr": 15546.00,
        "product_sales": 8123.00,
        "total_revenue": 128202.00,
        "employee_expense": 38289.00,
        "owner_comp_taxes": 5000.00,
        "owner_comp": 20425.00,
        "product_cogs": 17131.00,
        "other_expenses": 44685.00,
        "employees": 8.5,
        "technical_employees": 5.5,
        "agreements": 35.0,
    },
    "2024-08": {
        "endpoints_managed": 561,
        "seats_managed": 511,
        "nrr": 3372.00,
        "mrr": 102545.00,
        "orr": 22247.00,
        "product_sales": 16059.00,
        "total_revenue": 144222.00,
        "employee_expense": 38509.00,
        "owner_comp_taxes": 5000.00,
        "owner_comp": 20425.00,
        "product_cogs": 26157.00,
        "other_expenses": 48335.00,
        "employees": 8.5,
        "technical_employees": 5.5,
        "agreements": 35.0,
    },
    "2024-09": {
        "endpoints_managed": 579,
        "seats_managed": 529,
        "nrr": 6716.00,
        "mrr": 107302.00,
        "orr": 20275.00,
        "product_sales": 9859.00,
        "total_revenue": 144152.00,
        "employee_expense": 37412.00,
        "owner_comp_taxes": 5000.00,
        "owner_comp": 20425.00,
        "product_cogs": 18185.00,
        "other_expenses": 44449.00,
        "employees": 8.5,
        "technical_employees": 5.5,
        "agreements": 35.0,
    },
    "2024-10": {
        "endpoints_managed": 581,
        "seats_managed": 532,
        "nrr": 9564.00,
        "mrr": 107704.00,
        "orr": 19270.00,
        "product_sales": 22184.00,
        "total_revenue": 158722.00,
        "employee_expense": 38767.00,
        "owner_comp_taxes": 5000.00,
        "owner_comp": 20425.00,
        "product_cogs": 35118.00,
        "other_expenses": 39862.00,
        "employees": 8.5,
        "technical_employees": 5.5,
        "agreements": 35.0,
    },
    "2024-11": {
        "endpoints_managed": 589,
        "seats_managed": 539,
        "nrr": 6692.00,
        "mrr": 109281.00,
        "orr": 17818.00,
        "product_sales": 18046.00,
        "total_revenue": 151837.00,
        "employee_expense": 38990.00,
        "owner_comp_taxes": 5000.00,
        "owner_comp": 22425.00,  # Note: Different from other months
        "product_cogs": 26256.00,
        "other_expenses": 46630.00,
        "employees": 8.5,
        "technical_employees": 5.5,
        "agreements": 35.0,
    },
    "2024-12": {
        "endpoints_managed": 589,
        "seats_managed": 539,
        "nrr": 10293.00,
        "mrr": 103342.00,
        "orr": 45410.00,
        "product_sales": 17468.00,
        "total_revenue": 176514.00,
        "employee_expense": 38264.00,
        "owner_comp_taxes": 5000.00,
        "owner_comp": 44425.00,  # Note: Different from other months
        "product_cogs": 27496.00,
        "other_expenses": 59688.00,
        "employees": 8.5,
        "technical_employees": 5.5,
        "agreements": 35.0,
    },
}

def backfill_period(period, metrics):
    """Backfill metrics for a single period"""
    metrics_list = []
    for metric_name, metric_value in metrics.items():
        metrics_list.append({
            "metric_name": metric_name,
            "metric_value": metric_value,
            "notes": "From QBR_layout_2024.png historical spreadsheet"
        })

    payload = {
        "period": period,
        "organization_id": ORGANIZATION_ID,
        "metrics": metrics_list
    }

    try:
        response = requests.post(
            f"{API_BASE}/metrics/manual",
            json=payload,
            timeout=30,
            verify=False
        )

        if response.status_code == 200:
            print(f"  ✓ Successfully backfilled {len(metrics_list)} metrics for {period}")
            return True
        else:
            print(f"  ✗ Failed for {period}: {response.status_code}")
            return False

    except Exception as e:
        print(f"  ✗ Error for {period}: {e}")
        return False

def main():
    print("="*80)
    print("QBR 2024 Complete Data Backfill - From QBR_layout_2024.png")
    print("="*80)
    print("Source: /opt/es-inventory-hub/docs/qbr/QBR_layout_2024.png")
    print("API: " + API_BASE)
    print("="*80)
    print()

    results = {"success": 0, "failed": 0}

    for period in sorted(HISTORICAL_DATA_2024.keys()):
        print(f"Period {period}: ({len(HISTORICAL_DATA_2024[period])} metrics)")

        if backfill_period(period, HISTORICAL_DATA_2024[period]):
            results["success"] += 1
        else:
            results["failed"] += 1
        print()

    # Summary
    print("="*80)
    print("Backfill Complete")
    print("="*80)
    print(f"Total Periods: {results['success'] + results['failed']}")
    print(f"Success: {results['success']}")
    print(f"Failed: {results['failed']}")
    print("="*80)

    return 0 if results['failed'] == 0 else 1

if __name__ == '__main__':
    sys.exit(main())

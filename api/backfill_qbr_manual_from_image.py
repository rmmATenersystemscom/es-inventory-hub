#!/usr/bin/env python3
"""
Backfill QBR Manual Metrics from Historical Spreadsheet

This script backfills manual metrics (revenue, expenses, profit, company info)
extracted from the QBR_layout.png spreadsheet.

Data source: /opt/es-inventory-hub/docs/qbr/QBR_layout.png
Periods: 2025-01 through 2025-10 (November 2025 excluded per user request)
"""

import sys
import requests
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# API endpoint
API_BASE = "https://localhost:5400/api/qbr"
ORGANIZATION_ID = 1

# Disable SSL warnings for self-signed certificates
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Historical data extracted from QBR_layout.png
# Format: period -> {metric_name: value}
HISTORICAL_DATA = {
    "2025-01": {
        # Revenue
        "nrr": -2044.00,
        "mrr": 109682.00,
        "orr": 28180.00,
        "product_sales": 16476.00,
        "total_revenue": 152294.00,
        # Expenses
        "employee_expense": 38742.00,
        "owner_comp_taxes": 5000.00,
        "owner_comp": 22588.00,
        "product_cogs": 21126.00,
        "other_expenses": 50043.00,
        "total_expenses": 137499.00,
        # Profit
        "net_profit": 14795.00,
        # General
        "employees": 8.5,
        "technical_employees": 5.5,
        "agreements": 37.0,
    },
    "2025-02": {
        # Revenue
        "nrr": 10877.00,
        "mrr": 110274.00,
        "orr": 63285.00,
        "product_sales": 2649.00,
        "total_revenue": 187085.00,
        # Expenses
        "employee_expense": 38065.00,
        "owner_comp_taxes": 5000.00,
        "owner_comp": 22588.00,
        "product_cogs": 70570.00,
        "other_expenses": 40873.00,
        "total_expenses": 177096.00,
        # Profit
        "net_profit": 9989.00,
        # General
        "employees": 8.5,
        "technical_employees": 5.5,
        "agreements": 36.0,
    },
    "2025-03": {
        # Revenue
        "nrr": 23446.00,
        "mrr": 110003.00,
        "orr": 15535.00,
        "product_sales": 27125.00,
        "total_revenue": 176109.00,
        # Expenses
        "employee_expense": 38803.00,
        "owner_comp_taxes": 17700.00,
        "owner_comp": 22588.00,
        "product_cogs": 27507.00,
        "other_expenses": 40293.00,
        "total_expenses": 146891.00,
        # Profit
        "net_profit": 29217.00,
        # General
        "employees": 8.5,
        "technical_employees": 5.5,
        "agreements": 36.0,
    },
    "2025-04": {
        # Revenue
        "nrr": 3979.00,
        "mrr": 113545.00,
        "orr": 29323.00,
        "product_sales": 10447.00,
        "total_revenue": 157294.00,
        # Expenses
        "employee_expense": 38866.00,
        "owner_comp_taxes": 6000.00,
        "owner_comp": 22588.00,
        "product_cogs": 19740.00,
        "other_expenses": 40306.00,
        "total_expenses": 127500.00,
        # Profit
        "net_profit": 29794.00,
        # General
        "employees": 8.5,
        "technical_employees": 5.5,
        "agreements": 37.0,
    },
    "2025-05": {
        # Revenue
        "nrr": 2990.00,
        "mrr": 117009.00,
        "orr": 37002.00,
        "product_sales": 8395.00,
        "total_revenue": 165396.00,
        # Expenses
        "employee_expense": 39097.00,
        "owner_comp_taxes": 6000.00,
        "owner_comp": 22588.00,
        "product_cogs": 23999.00,
        "other_expenses": 51619.00,
        "total_expenses": 143304.00,
        # Profit
        "net_profit": 22091.00,
        # General
        "employees": 8.5,
        "technical_employees": 5.5,
        "agreements": 38.0,
    },
    "2025-06": {
        # Revenue
        "nrr": 2384.00,
        "mrr": 112272.00,
        "orr": 16533.00,
        "product_sales": 13265.00,
        "total_revenue": 144455.00,
        # Expenses
        "employee_expense": 33558.00,
        "owner_comp_taxes": 29000.00,
        "owner_comp": 22588.00,
        "product_cogs": 18383.00,
        "other_expenses": 42101.00,
        "total_expenses": 145630.00,
        # Profit
        "net_profit": -1175.00,
        # General
        "employees": 8.5,
        "technical_employees": 5.5,
        "agreements": 38.0,
    },
    "2025-07": {
        # Revenue
        "nrr": 3557.00,
        "mrr": 114020.00,
        "orr": 19360.00,
        "product_sales": 16226.00,
        "total_revenue": 153163.00,
        # Expenses
        "employee_expense": 39082.00,
        "owner_comp_taxes": 12000.00,
        "owner_comp": 22588.00,
        "product_cogs": 22459.00,
        "other_expenses": 41454.00,
        "total_expenses": 137584.00,
        # Profit
        "net_profit": 15579.00,
        # General
        "employees": 8.5,
        "technical_employees": 5.5,
        "agreements": 38.0,
    },
    "2025-08": {
        # Revenue
        "nrr": 10725.00,
        "mrr": 107469.00,
        "orr": 19639.00,
        "product_sales": 13698.00,
        "total_revenue": 151531.00,
        # Expenses
        "employee_expense": 38248.00,
        "owner_comp_taxes": 12000.00,
        "owner_comp": 22588.00,
        "product_cogs": 21579.00,
        "other_expenses": 43318.00,
        "total_expenses": 137733.00,
        # Profit
        "net_profit": 13798.00,
        # General
        "employees": 8.5,
        "technical_employees": 5.5,
        "agreements": 38.0,
    },
    "2025-09": {
        # Revenue
        "nrr": 13798.00,
        "mrr": 106255.00,
        "orr": 18184.00,
        "product_sales": 64278.00,
        "total_revenue": 202515.00,
        # Expenses
        "employee_expense": 35757.00,
        "owner_comp_taxes": 12000.00,
        "owner_comp": 22588.00,
        "product_cogs": 56437.00,
        "other_expenses": 44929.00,
        "total_expenses": 171712.00,
        # Profit
        "net_profit": 30803.00,
        # General
        "employees": 7.5,
        "technical_employees": 4.5,
        "agreements": 37.0,
    },
    "2025-10": {
        # Revenue
        "nrr": 21264.00,
        "mrr": 109227.00,
        "orr": 12347.00,
        "product_sales": 38148.00,
        "total_revenue": 180986.00,
        # Expenses
        "employee_expense": 37788.00,
        "owner_comp_taxes": 12000.00,
        "owner_comp": 22588.00,
        "product_cogs": 33685.00,
        "other_expenses": 43452.00,
        "total_expenses": 149514.00,
        # Profit
        "net_profit": 31473.00,
        # General
        "employees": 8.5,
        "technical_employees": 5.5,
        # Note: agreements value not clearly visible in image for Oct
    },
}

# 2024 data - only totals visible in comparison rows
HISTORICAL_DATA_2024 = {
    "2024-01": {
        "total_expenses": 119022.00,
        "net_profit": -263.00,
    },
    "2024-02": {
        "total_expenses": 174550.00,
        "net_profit": 4417.00,
    },
    "2024-03": {
        "total_expenses": 121798.00,
        "net_profit": 25778.00,
    },
    "2024-04": {
        "total_expenses": 139951.00,
        "net_profit": 8234.00,
    },
    "2024-05": {
        "total_expenses": 138324.00,
        "net_profit": 5696.00,
    },
    "2024-06": {
        "total_expenses": 140785.00,
        "net_profit": 7559.00,
    },
    "2024-07": {
        "total_expenses": 125530.00,
        "net_profit": 2672.00,
    },
    "2024-08": {
        "total_expenses": 138426.00,
        "net_profit": 5796.00,
    },
    "2024-09": {
        "total_expenses": 125470.00,
        "net_profit": 18682.00,
    },
    "2024-10": {
        "total_expenses": 139172.00,
        "net_profit": 19550.00,
    },
    "2024-11": {
        "total_expenses": 139301.00,
        "net_profit": 12535.00,
    },
    "2024-12": {
        "total_expenses": 174873.00,
        "net_profit": 1641.00,
    },
}


def backfill_period(period: str, metrics: dict, dry_run: bool = False):
    """
    Backfill metrics for a single period.

    Args:
        period: Period string (YYYY-MM)
        metrics: Dictionary of metric_name -> value
        dry_run: If True, only print what would be done

    Returns:
        bool: Success status
    """
    # Convert metrics dict to API format
    metrics_list = []
    for metric_name, metric_value in metrics.items():
        metrics_list.append({
            "metric_name": metric_name,
            "metric_value": metric_value,
            "notes": "Backfilled from QBR_layout.png historical spreadsheet"
        })

    payload = {
        "period": period,
        "organization_id": ORGANIZATION_ID,
        "metrics": metrics_list
    }

    if dry_run:
        print(f"  [DRY RUN] Would POST {len(metrics_list)} metrics for {period}")
        for m in metrics_list:
            print(f"    - {m['metric_name']}: {m['metric_value']}")
        return True

    # Make API call
    try:
        response = requests.post(
            f"{API_BASE}/metrics/manual",
            json=payload,
            timeout=30,
            verify=False  # Disable SSL verification for self-signed cert
        )

        if response.status_code == 200:
            print(f"  ✓ Successfully backfilled {len(metrics_list)} metrics for {period}")
            return True
        else:
            print(f"  ✗ Failed for {period}: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        print(f"  ✗ Error for {period}: {e}")
        return False


def main():
    """Run the backfill process"""
    import argparse

    parser = argparse.ArgumentParser(description='Backfill QBR manual metrics from historical spreadsheet')
    parser.add_argument('--dry-run', action='store_true', help='Preview without making changes')
    parser.add_argument('--year', type=int, choices=[2024, 2025], help='Only backfill specific year')
    args = parser.parse_args()

    print("="*80)
    print("QBR Manual Metrics Backfill - From Historical Spreadsheet")
    print("="*80)
    print(f"Source: /opt/es-inventory-hub/docs/qbr/QBR_layout.png")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print(f"API: {API_BASE}")
    print("="*80)
    print()

    results = {
        "success": 0,
        "failed": 0,
        "total": 0
    }

    # Backfill 2025 data (Jan-Oct, excluding Nov per user request)
    if args.year is None or args.year == 2025:
        print("Backfilling 2025 Manual Metrics (Jan-Oct)")
        print("-"*80)

        for period in sorted(HISTORICAL_DATA.keys()):
            results["total"] += 1
            print(f"Period {period}:")

            if backfill_period(period, HISTORICAL_DATA[period], args.dry_run):
                results["success"] += 1
            else:
                results["failed"] += 1
            print()

    # Backfill 2024 data (totals only)
    if args.year is None or args.year == 2024:
        print("Backfilling 2024 Totals (Jan-Dec)")
        print("-"*80)

        for period in sorted(HISTORICAL_DATA_2024.keys()):
            results["total"] += 1
            print(f"Period {period}:")

            if backfill_period(period, HISTORICAL_DATA_2024[period], args.dry_run):
                results["success"] += 1
            else:
                results["failed"] += 1
            print()

    # Summary
    print("="*80)
    print("Backfill Complete")
    print("="*80)
    print(f"Total Periods: {results['total']}")
    print(f"Success: {results['success']}")
    print(f"Failed: {results['failed']}")
    print(f"Success Rate: {results['success']/results['total']*100:.1f}%")
    print("="*80)

    return 0 if results['failed'] == 0 else 1


if __name__ == '__main__':
    sys.exit(main())

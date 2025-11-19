#!/usr/bin/env python3
"""
Backfill Endpoints and Seats data from QBR_layout.png
"""

import sys
import requests

# Disable SSL warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

API_BASE = "https://localhost:5400/api/qbr"
ORGANIZATION_ID = 1

# Data extracted from QBR_layout.png
ENDPOINTS_DATA = {
    "2025-01": 597,
    "2025-02": 594,
    "2025-03": 591,
    "2025-04": 613,
    "2025-05": 640,
    "2025-06": 601,
    "2025-07": 597,
    "2025-08": 560,
    "2025-09": 558,
    "2025-10": 575,  # Update from image (was 577 from collector)
    "2025-11": 579,  # Already have from collector
}

SEATS_DATA = {
    "2025-01": 546,
    "2025-02": 543,
    "2025-03": 542,
    "2025-04": 564,
    "2025-05": 585,
    "2025-06": 551,
    "2025-07": 548,
    "2025-08": 511,
    "2025-09": 509,
    # Oct and Nov not visible in image for seats
}

def backfill_metric(period, metric_name, metric_value):
    """Backfill a single metric via API"""
    payload = {
        "period": period,
        "organization_id": ORGANIZATION_ID,
        "metrics": [{
            "metric_name": metric_name,
            "metric_value": float(metric_value),
            "notes": f"From QBR_layout.png spreadsheet"
        }]
    }

    try:
        response = requests.post(
            f"{API_BASE}/metrics/manual",
            json=payload,
            timeout=30,
            verify=False
        )

        if response.status_code == 200:
            return True
        else:
            print(f"    ✗ API Error: {response.status_code}")
            return False
    except Exception as e:
        print(f"    ✗ Error: {e}")
        return False

def main():
    print("="*80)
    print("Backfilling Endpoints and Seats from QBR_layout.png")
    print("="*80)
    print()

    success_count = 0
    total_count = 0

    # Backfill endpoints
    print("Backfilling Endpoints Managed")
    print("-"*80)
    for period, value in sorted(ENDPOINTS_DATA.items()):
        total_count += 1
        print(f"{period}: endpoints_managed = {value}")
        if backfill_metric(period, "endpoints_managed", value):
            print(f"  ✓ Success")
            success_count += 1
        print()

    # Backfill seats
    print("Backfilling Seats Managed")
    print("-"*80)
    for period, value in sorted(SEATS_DATA.items()):
        total_count += 1
        print(f"{period}: seats_managed = {value}")
        if backfill_metric(period, "seats_managed", value):
            print(f"  ✓ Success")
            success_count += 1
        print()

    print("="*80)
    print(f"Backfill Complete: {success_count}/{total_count} successful")
    print("="*80)

    return 0 if success_count == total_count else 1

if __name__ == '__main__':
    sys.exit(main())

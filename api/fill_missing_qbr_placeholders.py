#!/usr/bin/env python3
"""
Fill Missing QBR Metrics with Placeholders

This script identifies missing manual metrics and fills them with a value of 1
so you can easily see what data still needs to be entered.
"""

import sys
import os
import psycopg2
from psycopg2.extras import RealDictCursor

# Expected manual metrics for different periods
MANUAL_METRICS_2025 = [
    # Revenue
    "nrr", "mrr", "orr", "product_sales", "total_revenue",
    # Expenses
    "employee_expense", "owner_comp_taxes", "owner_comp",
    "product_cogs", "other_expenses", "total_expenses",
    # Profit
    "net_profit",
    # Company
    "employees", "technical_employees", "agreements",
    # Sales (optional but good to have)
    "telemarketing_dials", "first_time_appointments", "prospects_to_pbr",
    "new_agreements", "new_mrr", "lost_mrr"
]

MANUAL_METRICS_2024 = [
    # Only these were visible in the spreadsheet for 2024
    "total_expenses", "net_profit"
]

def get_db_connection():
    """Get database connection from environment"""
    db_dsn = os.getenv('DB_DSN', 'postgresql://postgres:mK2D282lRrs6bTpXWe7@localhost:5432/es_inventory_hub')
    return psycopg2.connect(db_dsn)

def get_existing_metrics(conn, period):
    """Get list of existing metric names for a period"""
    query = """
        SELECT DISTINCT metric_name
        FROM qbr_metrics_monthly
        WHERE period = %s
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query, (period,))
        return {row['metric_name'] for row in cur.fetchall()}

def insert_placeholder(conn, period, metric_name):
    """Insert a placeholder metric with value 1"""
    # First check if it exists
    check_query = """
        SELECT 1 FROM qbr_metrics_monthly
        WHERE period = %s
          AND organization_id = 1
          AND vendor_id IS NULL
          AND metric_name = %s
        LIMIT 1
    """

    with conn.cursor() as cur:
        cur.execute(check_query, (period, metric_name))
        if cur.fetchone():
            return  # Already exists, skip

    # Insert the placeholder
    insert_query = """
        INSERT INTO qbr_metrics_monthly
            (period, organization_id, vendor_id, metric_name, metric_value,
             data_source, notes, created_at, updated_at)
        VALUES
            (%s, 1, NULL, %s, 1.0, 'manual',
             'PLACEHOLDER - Replace with real data', NOW(), NOW())
    """
    with conn.cursor() as cur:
        cur.execute(insert_query, (period, metric_name))
    conn.commit()

def main():
    conn = get_db_connection()

    print("="*80)
    print("QBR Missing Metrics - Placeholder Fill")
    print("="*80)
    print("Filling missing metrics with value=1 to highlight what needs real data")
    print()

    # Generate periods
    periods_2024 = [f"2024-{m:02d}" for m in range(1, 13)]
    periods_2025 = [f"2025-{m:02d}" for m in range(1, 12)]  # Jan-Nov

    total_added = 0

    # Fill 2024 periods
    print("Processing 2024 Periods")
    print("-"*80)
    for period in periods_2024:
        existing = get_existing_metrics(conn, period)
        missing = [m for m in MANUAL_METRICS_2024 if m not in existing]

        if missing:
            print(f"{period}: Adding {len(missing)} placeholders - {', '.join(missing)}")
            for metric in missing:
                insert_placeholder(conn, period, metric)
                total_added += 1
        else:
            print(f"{period}: ✓ Complete")

    print()

    # Fill 2025 periods
    print("Processing 2025 Periods")
    print("-"*80)
    for period in periods_2025:
        existing = get_existing_metrics(conn, period)
        missing = [m for m in MANUAL_METRICS_2025 if m not in existing]

        if missing:
            print(f"{period}: Adding {len(missing)} placeholders - {', '.join(missing[:5])}{'...' if len(missing) > 5 else ''}")
            for metric in missing:
                insert_placeholder(conn, period, metric)
                total_added += 1
        else:
            print(f"{period}: ✓ Complete")

    print()
    print("="*80)
    print(f"Total Placeholders Added: {total_added}")
    print("="*80)
    print()
    print("Next Steps:")
    print("  1. Query metrics with value=1 to see what needs real data")
    print("  2. Update placeholders with actual values using the manual metrics API")
    print()

    conn.close()
    return 0

if __name__ == '__main__':
    sys.exit(main())

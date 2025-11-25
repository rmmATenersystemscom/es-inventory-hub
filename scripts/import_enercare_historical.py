#!/usr/bin/env python3
"""
Import historical seat/endpoint data from EnerCare_Export.xlsx into qbr_client_metrics table.

Usage:
    python3 scripts/import_enercare_historical.py [--dry-run]
"""

import os
import sys
import argparse
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

# Excel client name → Ninja organization name mapping
CLIENT_MAPPING = {
    "Alston": "Alston Equipment Co",
    "Averill & Reaney": "Averill & Reaney Attorneys at Law",
    "BFM Corp": "BFM Corp LLC",
    "Case Industies LLC": "Case Industries LLC",
    "CFI": "Certified Finance & Insurance",
    "ChillCo": "ChillCo Inc.",
    "Cornerstone Financial, LLC": "Cornerstone Financial, LLC",
    "Electro-Mechanical Recertifiers": "Electro-Mechanical Recertifiers LLC",
    "Fleur De LA Imports": "Fleur de LA Imports",
    "Garland": "David Garland",
    "GICA": "Gulf Intracoastal Canal Association",
    "Gulf South Engineering": "Gulf South Engineering and Testing Inc.",
    "Harris Investments": "Harris Investments, Ltd.",
    "Insurance Shield": "Insurance Shield",
    "JCPS ": "JOHN CALVIN PRESBYTERIAN PLAYSCHOOL",
    "Jebco / Lowe": "Lowe Engineers",
    "Joshua Allison Law": "Joshua D. Allison, A Prof. Law Corp.",
    "Lakeside Medical Group": "Lakeside Medical Group",
    "LAMCO CONSTRUCTION LLC": "LAMCO CONSTRUCTION LLC",
    "LANCO Construction Inc.": "LANCO Construction Inc.",
    "LTA": "Louisiana Tennis Association",
    "MADCON": "Madcon Corp",
    "NAIA": "North American Insurance Agency of LA",
    "NNW Oil": "NNW Oil",
    "NOCHI": "New Orleans Culinary & Hospitality Instit",
    "NOLTC": "New Orleans Lawn Tennis Club",
    "OMNI": "OMNI Opti-com Manufacturing Network",
    "Parasol Business Services, Inc./Telerecovery": "Parasol Business Services, Inc/Telerecovery",
    "Quality Plumbing": "Quality Plumbing",
    "Rigby": "Rigby Financial Group",
    "RV Masters": "RV Masters",
    "Saucier's Plumbing": "Saucier's Plumbing",
    "Sigma": "Sigma Risk Management Consulting, LLC.",
    "Siteco Construction": "Siteco Construction, LLC",
    "Speedway": "Speedway Printing & Copy Center",
    "SRI": "Southern Retinal Institute, LLC",
    "St Patrick": "St. Patrick",
    "St. Tammany Federation of Teachers and School Employees": "St. Tammany Federation of Teachers & Sch",
    "Summergrove Farm / David H Finnelly Holdings": "Summergrove Farm DHF",
    "TCC": "Tchefuncta Country Club",
    "Treadaway Bollinger, LLC": "Treadaway Bollinger, LLC",
    "Zeigler": "Zeigler Tree & Timber Co.",
}

# Sheet name → period mapping
MONTH_MAP = {
    "Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04",
    "May": "05", "Jun": "06", "Jul": "07", "Aug": "08",
    "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12"
}


def sheet_to_period(sheet_name: str) -> str:
    """Convert sheet name like 'Oct24' to period '2024-10'."""
    month_abbr = sheet_name[:3]
    year_suffix = sheet_name[3:]
    month_num = MONTH_MAP.get(month_abbr)
    if not month_num:
        raise ValueError(f"Unknown month in sheet name: {sheet_name}")
    year = f"20{year_suffix}"
    return f"{year}-{month_num}"


def parse_excel(filepath: str) -> list[dict]:
    """Parse Excel file and return list of records to insert."""
    xlsx = pd.ExcelFile(filepath)
    records = []

    for sheet_name in xlsx.sheet_names:
        period = sheet_to_period(sheet_name)
        df = pd.read_excel(xlsx, sheet_name=sheet_name)

        for _, row in df.iterrows():
            excel_client = row['Client']
            seats = int(row['Invoice # PCs']) if pd.notna(row['Invoice # PCs']) else 0
            endpoints = int(row['Inv# of PC & Servers']) if pd.notna(row['Inv# of PC & Servers']) else 0

            # Skip if no data
            if seats == 0 and endpoints == 0:
                continue

            # Skip if not in mapping
            if excel_client not in CLIENT_MAPPING:
                continue

            ninja_name = CLIENT_MAPPING[excel_client]
            records.append({
                'period': period,
                'client_name': ninja_name,
                'seats': seats,
                'endpoints': endpoints,
                'data_source': 'imported'
            })

    return records


def insert_records(records: list[dict], dry_run: bool = False):
    """Insert records into qbr_client_metrics table."""
    dsn = os.getenv('DB_DSN', 'postgresql://postgres:mK2D282lRrs6bTpXWe7@localhost:5432/es_inventory_hub')

    conn = psycopg2.connect(dsn)
    cur = conn.cursor()

    try:
        # Clear existing imported data
        if not dry_run:
            cur.execute("DELETE FROM qbr_client_metrics WHERE data_source = 'imported'")
            deleted = cur.rowcount
            print(f"Cleared {deleted} existing imported records")

        # Prepare data for bulk insert
        values = [
            (r['period'], r['client_name'], r['seats'], r['endpoints'], r['data_source'])
            for r in records
        ]

        if dry_run:
            print(f"\n[DRY RUN] Would insert {len(values)} records")
            # Show sample
            print("\nSample records:")
            for v in values[:10]:
                print(f"  {v}")
            if len(values) > 10:
                print(f"  ... and {len(values) - 10} more")
        else:
            execute_values(
                cur,
                """
                INSERT INTO qbr_client_metrics (period, client_name, seats, endpoints, data_source)
                VALUES %s
                ON CONFLICT (period, client_name) DO UPDATE SET
                    seats = EXCLUDED.seats,
                    endpoints = EXCLUDED.endpoints,
                    data_source = EXCLUDED.data_source
                """,
                values
            )
            print(f"Inserted {len(values)} records")
            conn.commit()

    finally:
        cur.close()
        conn.close()


def main():
    parser = argparse.ArgumentParser(description='Import EnerCare historical data')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be imported without inserting')
    args = parser.parse_args()

    excel_path = '/opt/es-inventory-hub/docs/qbr/EnerCare_Export.xlsx'

    if not os.path.exists(excel_path):
        print(f"Error: Excel file not found: {excel_path}")
        sys.exit(1)

    print(f"Parsing {excel_path}...")
    records = parse_excel(excel_path)

    # Summary by period
    periods = sorted(set(r['period'] for r in records))
    print(f"\nFound {len(records)} records across {len(periods)} periods:")
    for period in periods:
        count = len([r for r in records if r['period'] == period])
        print(f"  {period}: {count} clients")

    print(f"\nUnique clients: {len(set(r['client_name'] for r in records))}")

    insert_records(records, dry_run=args.dry_run)

    if not args.dry_run:
        print("\nImport complete!")


if __name__ == '__main__':
    main()

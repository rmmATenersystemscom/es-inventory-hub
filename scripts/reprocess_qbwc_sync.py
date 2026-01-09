#!/usr/bin/env python3
"""
Re-process stored QBWC sync data with current account mappings.

This script reads raw_response data from qbwc_sync_history and re-applies
the current account mappings. Useful when new mappings are added after
data has already been synced.

Usage:
    python3 scripts/reprocess_qbwc_sync.py [--period YYYY-MM] [--all]
"""

import sys
import argparse
import logging

sys.path.insert(0, '/opt/es-inventory-hub')

from datetime import datetime
from sqlalchemy import extract

from common.db import session_scope
from storage.schema import QBWCSyncHistory, QBWCAccountMapping
from api.qbwc_service import parse_pl_response, calculate_qbr_metrics, store_qbr_metrics

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def reprocess_period(period: str, organization_id: int = 1):
    """Re-process a specific period's P&L data with current mappings."""

    # Parse period (YYYY-MM) into year and month
    year, month = int(period.split('-')[0]), int(period.split('-')[1])

    with session_scope() as session:
        # Get the sync history record for this period using date extraction
        sync_record = session.query(QBWCSyncHistory).filter_by(
            organization_id=organization_id,
            sync_type='profit_loss'
        ).filter(
            extract('year', QBWCSyncHistory.period_start) == year,
            extract('month', QBWCSyncHistory.period_start) == month
        ).order_by(QBWCSyncHistory.created_at.desc()).first()

        if not sync_record:
            logger.error(f"No sync record found for period {period}")
            return False

        if not sync_record.raw_response:
            logger.error(f"No raw response stored for period {period}")
            return False

        # Get current active mappings
        mappings = session.query(QBWCAccountMapping).filter_by(
            organization_id=organization_id,
            is_active=True
        ).all()

        logger.info(f"Processing period {period} with {len(mappings)} active mappings")

        # Parse the raw response
        parsed_accounts = parse_pl_response(sync_record.raw_response)
        logger.info(f"Parsed {len(parsed_accounts)} accounts from stored response")

        # Show accounts that contain '6999' for debugging
        for name, value in parsed_accounts.items():
            if '6999' in name:
                logger.info(f"Found 6999 account: '{name}' = ${value}")

        # Apply mappings
        metrics = calculate_qbr_metrics(parsed_accounts, mappings)

        # Log what we calculated
        logger.info(f"Calculated metrics:")
        for key, value in sorted(metrics.items()):
            logger.info(f"  {key}: ${value}")

        # Store metrics
        count = store_qbr_metrics(organization_id, period, metrics)
        logger.info(f"Stored {count} metrics for period {period}")

        return True


def main():
    parser = argparse.ArgumentParser(description='Re-process QBWC sync data')
    parser.add_argument('--period', help='Specific period to process (YYYY-MM)')
    parser.add_argument('--all', action='store_true', help='Process all periods')
    args = parser.parse_args()

    if args.period:
        reprocess_period(args.period)
    elif args.all:
        # Get all unique periods from sync history
        with session_scope() as session:
            sync_records = session.query(QBWCSyncHistory).filter_by(
                sync_type='profit_loss'
            ).distinct(QBWCSyncHistory.period_start).all()

            periods = sorted(set(
                r.period_start.strftime('%Y-%m') for r in sync_records
            ))

        logger.info(f"Reprocessing {len(periods)} periods: {periods}")
        for period in periods:
            reprocess_period(period)
    else:
        # Default: process current month
        from datetime import date
        current_period = date.today().strftime('%Y-%m')
        logger.info(f"Processing current period: {current_period}")
        reprocess_period(current_period)


if __name__ == '__main__':
    main()

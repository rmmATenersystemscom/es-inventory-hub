"""NinjaOne QBR collector CLI."""

import argparse
import sys
from datetime import datetime

from common.logging import get_logger
from .ninja_collector import NinjaQBRCollector
from .utils import get_current_period, get_last_n_periods


def main():
    """Main CLI entry point for NinjaOne QBR collector."""
    parser = argparse.ArgumentParser(description='NinjaOne QBR metric collector')
    parser.add_argument(
        '--period',
        type=str,
        help='Period to collect (YYYY-MM format). If not specified, collects current month.'
    )
    parser.add_argument(
        '--last-n-months',
        type=int,
        help='Collect last N months including current month (e.g., 13 for current + 12 prior)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be collected without saving to database'
    )
    parser.add_argument(
        '--organization-id',
        type=int,
        default=1,
        help='Organization ID (default: 1 for Enersystems, LLC)'
    )

    args = parser.parse_args()

    # Set up logging
    logger = get_logger(__name__)

    # Determine periods to collect
    if args.last_n_months:
        periods = get_last_n_periods(args.last_n_months)
        logger.info(f"Collecting last {args.last_n_months} months: {periods}")
    elif args.period:
        periods = [args.period]
        logger.info(f"Collecting single period: {args.period}")
    else:
        periods = [get_current_period()]
        logger.info(f"Collecting current period: {periods[0]}")

    if args.dry_run:
        logger.info("DRY RUN MODE - No data will be saved to database")

    # Initialize collector
    collector = NinjaQBRCollector(organization_id=args.organization_id)

    # Collect metrics for each period
    success_count = 0
    failure_count = 0

    for period in periods:
        try:
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing period: {period}")
            logger.info(f"{'='*60}")

            if args.dry_run:
                # Just collect metrics without saving
                metrics = collector.collect_metrics(period)
                logger.info(f"\nMetrics collected for {period}:")
                for metric in metrics:
                    logger.info(f"  - {metric['metric_name']}: {metric['metric_value']}")
                    if metric.get('notes'):
                        logger.info(f"    Notes: {metric['notes']}")
                success_count += 1
            else:
                # Full collection with database save
                success = collector.collect_period(period)
                if success:
                    success_count += 1
                    logger.info(f"✓ Successfully collected metrics for {period}")
                else:
                    failure_count += 1
                    logger.error(f"✗ Failed to collect metrics for {period}")

        except Exception as e:
            failure_count += 1
            logger.error(f"✗ Error processing period {period}: {e}", exc_info=True)

    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("Collection Summary")
    logger.info(f"{'='*60}")
    logger.info(f"Total periods: {len(periods)}")
    logger.info(f"Successful: {success_count}")
    logger.info(f"Failed: {failure_count}")

    if failure_count > 0:
        sys.exit(1)


if __name__ == '__main__':
    main()

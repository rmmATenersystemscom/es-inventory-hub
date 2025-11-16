#!/usr/bin/env python3
"""
Master QBR collector script - runs all collectors for the current month.

This script is designed to be run by systemd timer daily at 10:30pm Central Time.
It collects metrics from all sources for the current month.
"""

import sys
import argparse
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from common.logging import get_logger
from collectors.qbr.ninja_collector import NinjaQBRCollector
from collectors.qbr.connectwise_collector import ConnectWiseQBRCollector
from collectors.qbr.utils import get_current_period


def main():
    """Main entry point for QBR collection."""
    parser = argparse.ArgumentParser(
        description='Collect QBR metrics from all sources for current month'
    )
    parser.add_argument(
        '--period',
        type=str,
        help='Period to collect (YYYY-MM). Defaults to current month.'
    )
    parser.add_argument(
        '--organization-id',
        type=int,
        default=1,
        help='Organization ID (default: 1 for Enersystems, LLC)'
    )
    parser.add_argument(
        '--skip-ninja',
        action='store_true',
        help='Skip NinjaOne collection'
    )
    parser.add_argument(
        '--skip-connectwise',
        action='store_true',
        help='Skip ConnectWise collection'
    )

    args = parser.parse_args()

    logger = get_logger(__name__)

    # Determine period
    period = args.period or get_current_period()

    logger.info("=" * 80)
    logger.info(f"QBR Collection Run - Period: {period}")
    logger.info(f"Started: {datetime.now().isoformat()}")
    logger.info("=" * 80)

    collectors = []
    results = {}

    # Initialize collectors
    if not args.skip_ninja:
        collectors.append(('NinjaOne', NinjaQBRCollector(organization_id=args.organization_id)))

    if not args.skip_connectwise:
        collectors.append(('ConnectWise', ConnectWiseQBRCollector(organization_id=args.organization_id)))

    if not collectors:
        logger.error("No collectors enabled. Use --skip-ninja or --skip-connectwise to control.")
        return 1

    # Run collectors
    for name, collector in collectors:
        logger.info(f"\n{'=' * 80}")
        logger.info(f"Running {name} collector...")
        logger.info(f"{'=' * 80}")

        try:
            success = collector.collect_period(period)
            results[name] = success

            if success:
                logger.info(f"✓ {name} collection completed successfully")
            else:
                logger.error(f"✗ {name} collection failed")

        except Exception as e:
            logger.error(f"✗ {name} collector raised exception: {e}", exc_info=True)
            results[name] = False

    # Summary
    logger.info(f"\n{'=' * 80}")
    logger.info("Collection Summary")
    logger.info(f"{'=' * 80}")

    success_count = sum(1 for success in results.values() if success)
    failure_count = len(results) - success_count

    for name, success in results.items():
        status = "✓ SUCCESS" if success else "✗ FAILED"
        logger.info(f"{name}: {status}")

    logger.info(f"\nTotal: {len(results)} collectors")
    logger.info(f"Successful: {success_count}")
    logger.info(f"Failed: {failure_count}")
    logger.info(f"Completed: {datetime.now().isoformat()}")
    logger.info("=" * 80)

    # Exit code
    if failure_count > 0:
        logger.error("Collection run completed with failures")
        return 1
    else:
        logger.info("Collection run completed successfully")
        return 0


if __name__ == '__main__':
    sys.exit(main())

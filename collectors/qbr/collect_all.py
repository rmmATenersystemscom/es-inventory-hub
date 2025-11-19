#!/usr/bin/env python3
"""
QBR Master Collector - Runs all QBR collectors

This script orchestrates the collection of all QBR metrics from all sources:
- NinjaOne (endpoints, seats)
- ConnectWise (tickets, time entries)

Designed to be run via systemd timer daily at 10:30 PM Central Time.
"""

import sys
import logging
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from collectors.qbr.ninja_main import main as ninja_main
from collectors.qbr.connectwise_main import main as connectwise_main
from collectors.qbr.utils import get_current_period

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def main():
    """
    Run all QBR collectors for the current period.

    Returns:
        int: Exit code (0 = success, 1 = partial failure, 2 = total failure)
    """
    start_time = datetime.now()
    period = get_current_period()

    logger.info("="*80)
    logger.info("QBR Master Collector - Starting Collection")
    logger.info("="*80)
    logger.info(f"Period: {period}")
    logger.info(f"Start Time: {start_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    logger.info("="*80)

    results = {
        'ninjaone': {'success': False, 'error': None},
        'connectwise': {'success': False, 'error': None}
    }

    # Run NinjaOne collector
    logger.info("\n" + "-"*80)
    logger.info("Running NinjaOne Collector")
    logger.info("-"*80)
    try:
        ninja_main()
        results['ninjaone']['success'] = True
        logger.info("✓ NinjaOne collection completed successfully")
    except Exception as e:
        results['ninjaone']['error'] = str(e)
        logger.error(f"✗ NinjaOne collection failed: {e}", exc_info=True)

    # Run ConnectWise collector
    logger.info("\n" + "-"*80)
    logger.info("Running ConnectWise Collector")
    logger.info("-"*80)
    try:
        connectwise_main()
        results['connectwise']['success'] = True
        logger.info("✓ ConnectWise collection completed successfully")
    except Exception as e:
        results['connectwise']['error'] = str(e)
        logger.error(f"✗ ConnectWise collection failed: {e}", exc_info=True)

    # Summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    logger.info("\n" + "="*80)
    logger.info("QBR Master Collector - Collection Complete")
    logger.info("="*80)
    logger.info(f"Duration: {duration:.1f} seconds")
    logger.info(f"NinjaOne: {'✓ SUCCESS' if results['ninjaone']['success'] else '✗ FAILED'}")
    logger.info(f"ConnectWise: {'✓ SUCCESS' if results['connectwise']['success'] else '✗ FAILED'}")

    # Determine exit code
    successes = sum(1 for r in results.values() if r['success'])

    if successes == 2:
        logger.info("Status: ✓ ALL COLLECTORS SUCCESSFUL")
        logger.info("="*80)
        return 0
    elif successes == 1:
        logger.warning("Status: ⚠ PARTIAL SUCCESS (1/2 collectors failed)")
        logger.info("="*80)
        return 1
    else:
        logger.error("Status: ✗ TOTAL FAILURE (all collectors failed)")
        logger.info("="*80)
        return 2


if __name__ == '__main__':
    sys.exit(main())

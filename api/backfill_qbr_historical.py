#!/usr/bin/env python3
"""
Historical QBR Data Backfill Script

Systematically backfills QBR metrics from January 2024 through November 2025.
Tests both NinjaOne and ConnectWise collectors across all historical periods.
"""

import sys
import subprocess
import time
from pathlib import Path
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os


class BackfillOrchestrator:
    """Orchestrates historical data backfill for QBR system"""

    def __init__(self, start_period: str, end_period: str, dry_run: bool = False):
        """
        Initialize backfill orchestrator

        Args:
            start_period: Starting period in YYYY-MM format (e.g., '2024-01')
            end_period: Ending period in YYYY-MM format (e.g., '2025-11')
            dry_run: If True, run in dry-run mode without saving to database
        """
        self.start_period = start_period
        self.end_period = end_period
        self.dry_run = dry_run

        # Database connection
        self.db_dsn = os.environ.get('DB_DSN',
            'postgresql://postgres:mK2D282lRrs6bTpXWe7@localhost:5432/es_inventory_hub')

        # Generate list of periods to backfill
        self.periods = self._generate_periods()

        print(f"\n{'='*80}")
        print(f"QBR Historical Backfill Orchestrator")
        print(f"{'='*80}")
        print(f"Start Period: {self.start_period}")
        print(f"End Period: {self.end_period}")
        print(f"Total Periods: {len(self.periods)}")
        print(f"Dry Run: {self.dry_run}")
        print(f"{'='*80}\n")

    def _generate_periods(self) -> list:
        """Generate list of YYYY-MM periods between start and end"""
        periods = []

        # Parse start and end dates
        start_year, start_month = map(int, self.start_period.split('-'))
        end_year, end_month = map(int, self.end_period.split('-'))

        start_date = date(start_year, start_month, 1)
        end_date = date(end_year, end_month, 1)

        current_date = start_date
        while current_date <= end_date:
            periods.append(current_date.strftime('%Y-%m'))
            current_date += relativedelta(months=1)

        return periods

    def _run_collector(self, collector: str, period: str) -> dict:
        """
        Run a specific collector for a specific period

        Args:
            collector: 'ninjaone' or 'connectwise'
            period: Period in YYYY-MM format

        Returns:
            dict with success status and any error messages
        """
        print(f"\n{'-'*80}")
        print(f"Running {collector.upper()} collector for {period}")
        print(f"{'-'*80}")

        # Build command
        if collector == 'ninjaone':
            module = 'collectors.qbr.ninja_main'
        elif collector == 'connectwise':
            module = 'collectors.qbr.connectwise_main'
        else:
            return {"success": False, "error": f"Unknown collector: {collector}"}

        cmd = [
            'python3', '-m', module,
            '--period', period
        ]

        if self.dry_run:
            cmd.append('--dry-run')

        # Set environment variables for ConnectWise
        env = os.environ.copy()
        if collector == 'connectwise':
            env.update({
                'CONNECTWISE_SERVER': 'https://helpme.enersystems.com',
                'CONNECTWISE_COMPANY_ID': 'enersystems',
                'CONNECTWISE_CLIENT_ID': '5aa0e7b6-5500-48fb-90a8-8410802df04c',
                'CONNECTWISE_PUBLIC_KEY': 's9QF8u12JFPE22R7',
                'CONNECTWISE_PRIVATE_KEY': 'vgo8s3P0mvpnPXBn'
            })

        try:
            # Run collector
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout per period
            )

            if result.returncode == 0:
                print(f"✓ SUCCESS: {collector} {period}")
                return {"success": True, "stdout": result.stdout, "stderr": result.stderr}
            else:
                print(f"✗ FAILED: {collector} {period}")
                print(f"Return code: {result.returncode}")
                print(f"STDERR: {result.stderr[:500]}")
                return {
                    "success": False,
                    "error": result.stderr,
                    "return_code": result.returncode
                }

        except subprocess.TimeoutExpired:
            print(f"✗ TIMEOUT: {collector} {period}")
            return {"success": False, "error": "Timeout after 10 minutes"}
        except Exception as e:
            print(f"✗ ERROR: {collector} {period}: {str(e)}")
            return {"success": False, "error": str(e)}

    def _check_database_counts(self):
        """Check how many records are in the database"""
        engine = create_engine(self.db_dsn)
        Session = sessionmaker(bind=engine)
        session = Session()

        try:
            # Count total records
            result = session.execute(text("""
                SELECT COUNT(*) as total,
                       COUNT(DISTINCT period) as periods,
                       MIN(period) as earliest,
                       MAX(period) as latest
                FROM qbr_metrics_monthly
            """))
            row = result.fetchone()

            print(f"\n{'='*80}")
            print(f"Database Statistics")
            print(f"{'='*80}")
            print(f"Total Records: {row[0]}")
            print(f"Distinct Periods: {row[1]}")
            print(f"Earliest Period: {row[2]}")
            print(f"Latest Period: {row[3]}")

            # Count by period
            result = session.execute(text("""
                SELECT period, COUNT(*) as count
                FROM qbr_metrics_monthly
                GROUP BY period
                ORDER BY period
            """))

            print(f"\nRecords by Period:")
            for row in result:
                print(f"  {row[0]}: {row[1]} metrics")

            print(f"{'='*80}\n")

        finally:
            session.close()
            engine.dispose()

    def run_backfill(self):
        """Execute the complete backfill process"""
        start_time = time.time()

        results = {
            'ninjaone': {'success': 0, 'failed': 0, 'errors': []},
            'connectwise': {'success': 0, 'failed': 0, 'errors': []}
        }

        # Process each period
        for i, period in enumerate(self.periods, 1):
            print(f"\n{'='*80}")
            print(f"Processing Period {i}/{len(self.periods)}: {period}")
            print(f"{'='*80}")

            # Run NinjaOne collector
            ninja_result = self._run_collector('ninjaone', period)
            if ninja_result['success']:
                results['ninjaone']['success'] += 1
            else:
                results['ninjaone']['failed'] += 1
                results['ninjaone']['errors'].append({
                    'period': period,
                    'error': ninja_result.get('error', 'Unknown error')
                })

            # Small delay between collectors
            time.sleep(2)

            # Run ConnectWise collector
            cw_result = self._run_collector('connectwise', period)
            if cw_result['success']:
                results['connectwise']['success'] += 1
            else:
                results['connectwise']['failed'] += 1
                results['connectwise']['errors'].append({
                    'period': period,
                    'error': cw_result.get('error', 'Unknown error')
                })

            # Small delay before next period
            time.sleep(2)

        # Calculate elapsed time
        elapsed_time = time.time() - start_time

        # Print summary
        print(f"\n{'='*80}")
        print(f"Backfill Complete")
        print(f"{'='*80}")
        print(f"Total Time: {elapsed_time:.1f} seconds ({elapsed_time/60:.1f} minutes)")
        print(f"\nNinjaOne Results:")
        print(f"  Success: {results['ninjaone']['success']}/{len(self.periods)}")
        print(f"  Failed: {results['ninjaone']['failed']}/{len(self.periods)}")

        print(f"\nConnectWise Results:")
        print(f"  Success: {results['connectwise']['success']}/{len(self.periods)}")
        print(f"  Failed: {results['connectwise']['failed']}/{len(self.periods)}")

        # Show errors if any
        if results['ninjaone']['errors']:
            print(f"\nNinjaOne Errors:")
            for err in results['ninjaone']['errors'][:5]:  # Show first 5
                print(f"  {err['period']}: {err['error'][:100]}")

        if results['connectwise']['errors']:
            print(f"\nConnectWise Errors:")
            for err in results['connectwise']['errors'][:5]:  # Show first 5
                print(f"  {err['period']}: {err['error'][:100]}")

        print(f"{'='*80}\n")

        # Check database if not dry-run
        if not self.dry_run:
            self._check_database_counts()

        return results


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Backfill historical QBR data')
    parser.add_argument('--start', default='2024-01',
                       help='Start period in YYYY-MM format (default: 2024-01)')
    parser.add_argument('--end', default='2025-11',
                       help='End period in YYYY-MM format (default: 2025-11)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Run in dry-run mode without saving to database')
    parser.add_argument('--check-db', action='store_true',
                       help='Only check database counts, do not run backfill')

    args = parser.parse_args()

    orchestrator = BackfillOrchestrator(args.start, args.end, args.dry_run)

    if args.check_db:
        orchestrator._check_database_counts()
    else:
        orchestrator.run_backfill()


if __name__ == '__main__':
    main()

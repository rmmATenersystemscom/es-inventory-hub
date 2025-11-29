"""Veeam VSPC collector main CLI."""

import argparse
import sys
from datetime import datetime, date

from common.logging import get_logger
from common.job_logging import log_job_start, log_job_completion, log_job_failure

from .api import VeeamAPI
from .mapping import normalize_veeam_data


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description='Veeam VSPC collector')
    parser.add_argument(
        '--date',
        type=str,
        default=date.today().strftime('%Y-%m-%d'),
        help='Date for snapshot in YYYY-MM-DD format (default: today)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Fetch and normalize data but do not save to database'
    )

    args = parser.parse_args()

    # Set up logging
    logger = get_logger(__name__)

    # Log job start
    job_run_id = None
    if not args.dry_run:
        job_run_id = log_job_start('veeam-collector', f'Starting collection for date: {args.date}')

    try:
        # Parse the date
        snapshot_date = datetime.strptime(args.date, '%Y-%m-%d').date()
        logger.info(f"Starting Veeam collection for date: {snapshot_date}")

        if args.dry_run:
            logger.info("DRY RUN MODE - no data will be saved to database")

        # Initialize Veeam API
        logger.info("Initializing Veeam VSPC API client")
        api = VeeamAPI()

        # Fetch data from VSPC
        logger.info("Fetching data from VSPC...")
        companies = api.get_companies()
        usage_data = api.get_cloud_usage()
        quota_data = api.get_quota_data()

        # Normalize data
        logger.info("Normalizing data...")
        normalized = normalize_veeam_data(companies, usage_data, quota_data)

        # Process results
        if args.dry_run:
            run_dry_run(normalized, logger)
        else:
            run_collection(normalized, snapshot_date, logger)

        logger.info("Veeam collection completed successfully")

        # Log job completion
        if job_run_id:
            log_job_completion(job_run_id, 'completed', 'Collection completed successfully')

    except Exception as e:
        logger.error(f"Veeam collection failed: {e}")

        # Log job failure
        if job_run_id:
            log_job_failure(job_run_id, str(e))

        sys.exit(1)


def run_dry_run(normalized: list, logger) -> None:
    """Run in dry-run mode: display normalized data."""
    logger.info("Dry run - displaying normalized data")

    print("\n" + "=" * 90)
    print("VEEAM CLOUD STORAGE USAGE")
    print("=" * 90)

    # Calculate totals
    total_storage = sum(org['storage_gb'] for org in normalized)
    total_quota = sum(org['quota_gb'] for org in normalized)

    # Print header
    print(f"\n{'Organization':<40} {'Storage (GB)':>14} {'Quota (GB)':>12} {'Usage %':>10}")
    print("-" * 80)

    # Print each organization
    for org in normalized:
        quota_str = f"{org['quota_gb']:.2f}" if org['quota_gb'] > 0 else "N/A"
        pct_str = f"{org['usage_pct']:.1f}%" if org['quota_gb'] > 0 else "N/A"
        print(
            f"{org['organization_name'][:39]:<40} "
            f"{org['storage_gb']:>14.2f} "
            f"{quota_str:>12} "
            f"{pct_str:>10}"
        )

    # Print totals
    print("-" * 80)
    overall_pct = (total_storage / total_quota * 100) if total_quota > 0 else 0
    print(
        f"{'TOTAL':<40} "
        f"{total_storage:>14.2f} "
        f"{total_quota:>12.2f} "
        f"{overall_pct:>9.1f}%"
    )

    print("\n" + "=" * 90)
    print(f"Organizations with data: {len(normalized)}")
    print(f"Total storage: {total_storage:,.2f} GB")
    print(f"Total quota: {total_quota:,.2f} GB")
    print("=" * 90 + "\n")


def run_collection(normalized: list, snapshot_date: date, logger) -> None:
    """Run actual collection: save data to database."""
    logger.info("Starting real collection - saving to database")

    # Import database modules only when needed
    from common.config import get_dsn
    from common.db import session_scope
    from storage.schema import VeeamSnapshot, Vendor
    from sqlalchemy.dialects.postgresql import insert

    # Check database connection
    try:
        dsn = get_dsn()
        logger.info("Database connection configured")
    except Exception as e:
        logger.error(f"Database configuration error: {e}")
        raise

    saved_count = 0
    error_count = 0

    with session_scope() as session:
        # Ensure Veeam vendor exists
        vendor = session.query(Vendor).filter_by(name='Veeam').first()
        if not vendor:
            vendor = Vendor(name='Veeam')
            session.add(vendor)
            session.flush()
            logger.info("Created Veeam vendor record")

        # Delete existing snapshots for this date
        logger.info(f"Deleting existing Veeam snapshots for {snapshot_date}")
        deleted_count = session.query(VeeamSnapshot).filter(
            VeeamSnapshot.snapshot_date == snapshot_date
        ).delete()
        session.commit()
        logger.info(f"Deleted {deleted_count} existing snapshots for {snapshot_date}")

        # Insert new snapshots
        for org in normalized:
            try:
                stmt = insert(VeeamSnapshot).values(
                    snapshot_date=snapshot_date,
                    company_uid=org['company_uid'],
                    organization_name=org['organization_name'],
                    storage_gb=org['storage_gb'],
                    quota_gb=org['quota_gb'],
                    usage_pct=org['usage_pct']
                ).on_conflict_do_update(
                    index_elements=['snapshot_date', 'company_uid'],
                    set_={
                        'organization_name': org['organization_name'],
                        'storage_gb': org['storage_gb'],
                        'quota_gb': org['quota_gb'],
                        'usage_pct': org['usage_pct']
                    }
                )
                session.execute(stmt)
                saved_count += 1

            except Exception as e:
                error_count += 1
                logger.error(f"Error saving {org['organization_name']}: {e}")

        session.commit()

    logger.info(f"Collection completed. Saved: {saved_count}, Errors: {error_count}")

    if error_count > 0:
        logger.warning(f"{error_count} organizations failed to save")


if __name__ == '__main__':
    main()

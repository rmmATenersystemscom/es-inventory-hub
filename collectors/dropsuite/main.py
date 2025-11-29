"""Dropsuite collector main CLI."""

import argparse
import json
import sys
from datetime import datetime, date
from typing import Optional

from common.logging import get_logger
from common.job_logging import log_job_start, log_job_completion, log_job_failure

from .api import DropsuiteAPI
from .mapping import normalize_dropsuite_user


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description='Dropsuite email backup collector')
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
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of organizations to process'
    )

    args = parser.parse_args()

    # Set up logging
    logger = get_logger(__name__)

    # Log job start
    job_run_id = None
    if not args.dry_run:
        job_run_id = log_job_start('dropsuite-collector', f'Starting collection for date: {args.date}')

    try:
        # Parse the date
        snapshot_date = datetime.strptime(args.date, '%Y-%m-%d').date()
        logger.info(f"Starting Dropsuite collection for date: {snapshot_date}")

        if args.dry_run:
            logger.info("DRY RUN MODE - no data will be saved to database")

        if args.limit:
            logger.info(f"Limiting collection to {args.limit} organizations")

        # Initialize Dropsuite API
        logger.info("Initializing Dropsuite API client")
        api = DropsuiteAPI()

        # Process organizations
        if args.dry_run:
            run_dry_run(api, args.limit, logger)
        else:
            run_collection(api, snapshot_date, args.limit, logger)

        logger.info("Dropsuite collection completed successfully")

        # Log job completion
        if job_run_id:
            log_job_completion(job_run_id, 'completed', 'Collection completed successfully')

    except Exception as e:
        logger.error(f"Dropsuite collection failed: {e}")

        # Log job failure
        if job_run_id:
            log_job_failure(job_run_id, str(e))

        sys.exit(1)


def run_dry_run(api: DropsuiteAPI, limit: Optional[int], logger) -> None:
    """Run in dry-run mode: fetch and normalize data, then print it."""
    logger.info("Starting dry run - fetching and normalizing organizations")

    org_count = 0

    for raw_user in api.list_users():
        org_count += 1

        if limit and org_count > limit:
            break

        org_name = raw_user.get('organization_name', f'Org-{org_count}')
        logger.info(f"Processing organization {org_count}: {org_name}")

        # Fetch accounts for this organization
        auth_token = raw_user.get('authentication_token')
        accounts = []
        if auth_token:
            accounts = api.list_accounts(auth_token)
            logger.debug(f"  Retrieved {len(accounts)} accounts")

        # Normalize the data
        normalized = normalize_dropsuite_user(raw_user, accounts)

        # Remove raw data for cleaner output
        normalized_display = {k: v for k, v in normalized.items() if k != 'raw'}

        # Print normalized data
        print(f"\n--- Organization {org_count}: {org_name} ---")
        print(json.dumps(normalized_display, indent=2, default=str))

    logger.info(f"Dry run completed. Processed {org_count} organizations.")


def run_collection(api: DropsuiteAPI, snapshot_date: date, limit: Optional[int], logger) -> None:
    """Run actual collection: fetch, normalize, and save data to database."""
    logger.info("Starting real collection - saving to database")

    # Import database modules only when needed
    from common.config import get_dsn
    from common.db import session_scope
    from storage.schema import DropsuiteSnapshot, Vendor
    from sqlalchemy.dialects.postgresql import insert

    # Check database connection
    try:
        dsn = get_dsn()
        logger.info("Database connection configured")
    except Exception as e:
        logger.error(f"Database configuration error: {e}")
        raise

    org_count = 0
    saved_count = 0
    error_count = 0

    # Process organizations using session scope
    with session_scope() as session:
        # Ensure Dropsuite vendor exists
        vendor = session.query(Vendor).filter_by(name='Dropsuite').first()
        if not vendor:
            vendor = Vendor(name='Dropsuite')
            session.add(vendor)
            session.flush()
            logger.info("Created Dropsuite vendor record")

        # Delete existing snapshots for this date to ensure clean daily data
        logger.info(f"Deleting existing Dropsuite snapshots for {snapshot_date}")
        deleted_count = session.query(DropsuiteSnapshot).filter(
            DropsuiteSnapshot.snapshot_date == snapshot_date
        ).delete()
        session.commit()
        logger.info(f"Deleted {deleted_count} existing snapshots for {snapshot_date}")

        for raw_user in api.list_users():
            org_count += 1

            if limit and org_count > limit:
                break

            try:
                org_name = raw_user.get('organization_name', f'Org-{org_count}')
                logger.info(f"Processing organization {org_count}: {org_name}")

                # Fetch accounts for this organization
                auth_token = raw_user.get('authentication_token')
                accounts = []
                if auth_token:
                    accounts = api.list_accounts(auth_token)
                    logger.debug(f"  Retrieved {len(accounts)} accounts")

                # Normalize the data
                normalized = normalize_dropsuite_user(raw_user, accounts)

                if not normalized['user_id']:
                    logger.warning(f"Skipping organization without ID: {org_name}")
                    continue

                # Use upsert to handle duplicate (snapshot_date, user_id)
                stmt = insert(DropsuiteSnapshot).values(
                    snapshot_date=snapshot_date,
                    user_id=normalized['user_id'],
                    organization_name=normalized['organization_name'],
                    seats_used=normalized['seats_used'],
                    archive_type=normalized['archive_type'],
                    status=normalized['status'],
                    total_emails=normalized['total_emails'],
                    storage_gb=normalized['storage_gb'],
                    last_backup=normalized['last_backup'],
                    compliance=normalized['compliance']
                ).on_conflict_do_update(
                    index_elements=['snapshot_date', 'user_id'],
                    set_={
                        'organization_name': normalized['organization_name'],
                        'seats_used': normalized['seats_used'],
                        'archive_type': normalized['archive_type'],
                        'status': normalized['status'],
                        'total_emails': normalized['total_emails'],
                        'storage_gb': normalized['storage_gb'],
                        'last_backup': normalized['last_backup'],
                        'compliance': normalized['compliance']
                    }
                )
                session.execute(stmt)

                logger.info(f"Inserted snapshot for {normalized['user_id']}: {normalized['organization_name']}")
                saved_count += 1

                # Log progress every 10 organizations
                if org_count % 10 == 0:
                    logger.info(f"Progress: {org_count} organizations processed, {saved_count} saved")

            except Exception as e:
                error_count += 1
                logger.error(f"Error processing organization {org_name}: {e}")

                # Handle SQLAlchemy errors by rolling back
                try:
                    from sqlalchemy.exc import SQLAlchemyError
                    if isinstance(e, SQLAlchemyError):
                        session.rollback()
                        logger.warning(f"Rolled back transaction for {org_name}")
                except ImportError:
                    pass

                # Continue processing other organizations
                continue

        # Commit all changes
        session.commit()

    logger.info(f"Collection completed. Processed: {org_count}, "
                f"Saved: {saved_count}, Errors: {error_count}")

    if error_count > 0:
        logger.warning(f"{error_count} organizations failed to process")


if __name__ == '__main__':
    main()

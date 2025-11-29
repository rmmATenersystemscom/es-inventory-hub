"""Microsoft 365 collector main CLI."""

import argparse
import json
import sys
from datetime import datetime, date
from typing import Optional

from common.logging import get_logger
from common.job_logging import log_job_start, log_job_completion, log_job_failure

from .api import M365API
from .mapping import normalize_m365_tenant


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description='Microsoft 365 collector')
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
        help='Limit number of tenants to process'
    )

    args = parser.parse_args()

    # Set up logging
    logger = get_logger(__name__)

    # Log job start
    job_run_id = None
    if not args.dry_run:
        job_run_id = log_job_start('m365-collector', f'Starting collection for date: {args.date}')

    try:
        # Parse the date
        snapshot_date = datetime.strptime(args.date, '%Y-%m-%d').date()
        logger.info(f"Starting M365 collection for date: {snapshot_date}")

        if args.dry_run:
            logger.info("DRY RUN MODE - no data will be saved to database")

        if args.limit:
            logger.info(f"Limiting collection to {args.limit} tenants")

        # Initialize M365 API
        logger.info("Initializing M365 API client")
        api = M365API()

        # Process tenants
        if args.dry_run:
            run_dry_run(api, args.limit, logger)
        else:
            run_collection(api, snapshot_date, args.limit, logger)

        logger.info("M365 collection completed successfully")

        # Log job completion
        if job_run_id:
            log_job_completion(job_run_id, 'completed', 'Collection completed successfully')

    except Exception as e:
        logger.error(f"M365 collection failed: {e}")

        # Log job failure
        if job_run_id:
            log_job_failure(job_run_id, str(e))

        sys.exit(1)


def run_dry_run(api: M365API, limit: Optional[int], logger) -> None:
    """Run in dry-run mode: fetch and normalize data, then print it."""
    logger.info("Starting dry run - fetching and normalizing tenants")

    tenants = api.list_tenants()
    logger.info(f"Found {len(tenants)} configured tenants")

    tenant_count = 0
    total_users = 0

    for tenant in tenants:
        tenant_count += 1

        if limit and tenant_count > limit:
            break

        tenant_name = tenant['name']
        logger.info(f"Processing tenant {tenant_count}: {tenant_name}")

        try:
            # Fetch users for this tenant
            users = api.get_users(tenant)
            organization = api.get_organization(tenant)

            # Normalize the data
            normalized = normalize_m365_tenant(tenant, users, organization)

            total_users += normalized['user_count']

            # Print normalized data
            print(f"\n--- Tenant {tenant_count}: {tenant_name} ---")
            print(json.dumps(normalized, indent=2, default=str))

        except Exception as e:
            logger.error(f"Error processing tenant {tenant_name}: {e}")
            continue

    print(f"\n=== SUMMARY ===")
    print(f"Tenants processed: {tenant_count}")
    print(f"Total users (filtered): {total_users}")

    logger.info(f"Dry run completed. Processed {tenant_count} tenants, {total_users} total users.")


def run_collection(api: M365API, snapshot_date: date, limit: Optional[int], logger) -> None:
    """Run actual collection: fetch, normalize, and save data to database."""
    logger.info("Starting real collection - saving to database")

    # Import database modules only when needed
    from common.config import get_dsn
    from common.db import session_scope
    from storage.schema import M365Snapshot, M365UserSnapshot, Vendor
    from sqlalchemy.dialects.postgresql import insert

    # Check database connection
    try:
        dsn = get_dsn()
        logger.info("Database connection configured")
    except Exception as e:
        logger.error(f"Database configuration error: {e}")
        raise

    tenants = api.list_tenants()
    logger.info(f"Found {len(tenants)} configured tenants")

    tenant_count = 0
    saved_count = 0
    error_count = 0
    total_users = 0

    # Process tenants using session scope
    with session_scope() as session:
        # Ensure M365 vendor exists
        vendor = session.query(Vendor).filter_by(name='M365').first()
        if not vendor:
            vendor = Vendor(name='M365')
            session.add(vendor)
            session.flush()
            logger.info("Created M365 vendor record")

        # Delete existing snapshots for this date to ensure clean daily data
        logger.info(f"Deleting existing M365 snapshots for {snapshot_date}")
        deleted_count = session.query(M365Snapshot).filter(
            M365Snapshot.snapshot_date == snapshot_date
        ).delete()
        deleted_user_count = session.query(M365UserSnapshot).filter(
            M365UserSnapshot.snapshot_date == snapshot_date
        ).delete()
        session.commit()
        logger.info(f"Deleted {deleted_count} tenant snapshots, {deleted_user_count} user snapshots for {snapshot_date}")

        for tenant in tenants:
            tenant_count += 1

            if limit and tenant_count > limit:
                break

            try:
                tenant_name = tenant['name']
                logger.info(f"Processing tenant {tenant_count}: {tenant_name}")

                # Fetch users for this tenant
                users = api.get_users(tenant)
                organization = api.get_organization(tenant)

                logger.info(f"  Raw users: {len(users)}")

                # Normalize the data
                normalized = normalize_m365_tenant(tenant, users, organization)

                logger.info(f"  Filtered users: {normalized['user_count']}")
                total_users += normalized['user_count']

                # Use upsert to handle duplicate (snapshot_date, tenant_id)
                stmt = insert(M365Snapshot).values(
                    snapshot_date=snapshot_date,
                    tenant_id=normalized['tenant_id'],
                    organization_name=normalized['organization_name'],
                    user_count=normalized['user_count']
                ).on_conflict_do_update(
                    index_elements=['snapshot_date', 'tenant_id'],
                    set_={
                        'organization_name': normalized['organization_name'],
                        'user_count': normalized['user_count']
                    }
                )
                session.execute(stmt)

                # Insert user records
                user_records_saved = 0
                for user_detail in normalized.get('users', []):
                    user_stmt = insert(M365UserSnapshot).values(
                        snapshot_date=snapshot_date,
                        tenant_id=normalized['tenant_id'],
                        organization_name=normalized['organization_name'],
                        username=user_detail['username'],
                        display_name=user_detail['display_name'],
                        licenses=user_detail['licenses']
                    ).on_conflict_do_update(
                        index_elements=['snapshot_date', 'tenant_id', 'username'],
                        set_={
                            'organization_name': normalized['organization_name'],
                            'display_name': user_detail['display_name'],
                            'licenses': user_detail['licenses']
                        }
                    )
                    session.execute(user_stmt)
                    user_records_saved += 1

                logger.info(f"Inserted snapshot for {normalized['tenant_id']}: {normalized['organization_name']} ({user_records_saved} users)")
                saved_count += 1

                # Log progress every 10 tenants
                if tenant_count % 10 == 0:
                    logger.info(f"Progress: {tenant_count} tenants processed, {saved_count} saved")

            except Exception as e:
                error_count += 1
                logger.error(f"Error processing tenant {tenant_name}: {e}")

                # Handle SQLAlchemy errors by rolling back
                try:
                    from sqlalchemy.exc import SQLAlchemyError
                    if isinstance(e, SQLAlchemyError):
                        session.rollback()
                        logger.warning(f"Rolled back transaction for {tenant_name}")
                except ImportError:
                    pass

                # Continue processing other tenants
                continue

        # Commit all changes
        session.commit()

    logger.info(f"Collection completed. Processed: {tenant_count}, "
                f"Saved: {saved_count}, Errors: {error_count}, Total users: {total_users}")

    if error_count > 0:
        logger.warning(f"{error_count} tenants failed to process")


if __name__ == '__main__':
    main()

"""VadeSecure collector main CLI."""

import argparse
import json
import sys
from datetime import datetime, date
from typing import Optional

from common.logging import get_logger
from common.job_logging import log_job_start, log_job_completion, log_job_failure

from .api import VadeSecureAPI
from .mapping import normalize_vadesecure_customer


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description='VadeSecure customer/license collector')
    parser.add_argument(
        '--date',
        type=str,
        default=date.today().strftime('%Y-%m-%d'),
        help='Date for snapshot in YYYY-MM-DD format (default: today)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Fetch and normalize customers but do not save to database'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of customers to process'
    )

    args = parser.parse_args()

    # Set up logging
    logger = get_logger(__name__)

    # Log job start
    job_run_id = None
    if not args.dry_run:
        job_run_id = log_job_start('vadesecure-collector', f'Starting collection for date: {args.date}')

    try:
        # Parse the date
        snapshot_date = datetime.strptime(args.date, '%Y-%m-%d').date()
        logger.info(f"Starting VadeSecure collection for date: {snapshot_date}")

        if args.dry_run:
            logger.info("DRY RUN MODE - no data will be saved to database")

        if args.limit:
            logger.info(f"Limiting collection to {args.limit} customers")

        # Initialize VadeSecure API
        logger.info("Initializing VadeSecure API client")
        api = VadeSecureAPI()

        # Process customers
        if args.dry_run:
            run_dry_run(api, args.limit, logger)
        else:
            run_collection(api, snapshot_date, args.limit, logger)

        logger.info("VadeSecure collection completed successfully")

        # Log job completion
        if job_run_id:
            log_job_completion(job_run_id, 'completed', 'Collection completed successfully')

    except Exception as e:
        logger.error(f"VadeSecure collection failed: {e}")

        # Log job failure
        if job_run_id:
            log_job_failure(job_run_id, str(e))

        sys.exit(1)


def run_dry_run(api: VadeSecureAPI, limit: Optional[int], logger) -> None:
    """Run in dry-run mode: fetch and normalize customers, then print them."""
    logger.info("Starting dry run - fetching and normalizing customers")

    customers = api.list_customers()
    customer_count = 0

    for raw_customer in customers:
        customer_count += 1

        if limit and customer_count > limit:
            break

        logger.info(f"Processing customer {customer_count}: {raw_customer.get('name', 'N/A')}")

        # Normalize the customer
        normalized = normalize_vadesecure_customer(raw_customer)

        # Remove raw data for cleaner output
        normalized_display = {k: v for k, v in normalized.items() if k != 'raw'}

        # Print normalized customer dict
        print(f"\n--- Customer {customer_count} ---")
        print(json.dumps(normalized_display, indent=2, default=str))

    logger.info(f"Dry run completed. Processed {customer_count} customers.")


def run_collection(api: VadeSecureAPI, snapshot_date: date, limit: Optional[int], logger) -> None:
    """Run actual collection: fetch, normalize, and save customers to database."""
    logger.info("Starting real collection - saving to database")

    # Import database modules only when needed
    from common.config import get_dsn
    from common.db import session_scope
    from storage.schema import VadeSecureSnapshot, Vendor
    from sqlalchemy.dialects.postgresql import insert

    # Check database connection
    try:
        dsn = get_dsn()
        logger.info("Database connection configured")
    except Exception as e:
        logger.error(f"Database configuration error: {e}")
        raise

    # Fetch customers
    customers = api.list_customers()
    customer_count = 0
    saved_count = 0
    error_count = 0

    # Process customers in batches using session scope
    with session_scope() as session:
        # Ensure VadeSecure vendor exists
        vendor = session.query(Vendor).filter_by(name='VadeSecure').first()
        if not vendor:
            vendor = Vendor(name='VadeSecure')
            session.add(vendor)
            session.flush()
            logger.info("Created VadeSecure vendor record")

        # Delete existing snapshots for this date to ensure clean daily data
        logger.info(f"Deleting existing VadeSecure snapshots for {snapshot_date}")
        deleted_count = session.query(VadeSecureSnapshot).filter(
            VadeSecureSnapshot.snapshot_date == snapshot_date
        ).delete()
        session.commit()
        logger.info(f"Deleted {deleted_count} existing snapshots for {snapshot_date}")

        for raw_customer in customers:
            customer_count += 1

            if limit and customer_count > limit:
                break

            try:
                customer_name = raw_customer.get('name', f'Customer-{customer_count}')
                logger.info(f"Processing customer {customer_count}: {customer_name}")

                # Normalize the customer
                normalized = normalize_vadesecure_customer(raw_customer)

                if not normalized['customer_id']:
                    logger.warning(f"Skipping customer without ID: {customer_name}")
                    continue

                # Use upsert to handle duplicate (snapshot_date, customer_id)
                stmt = insert(VadeSecureSnapshot).values(
                    snapshot_date=snapshot_date,
                    customer_id=normalized['customer_id'],
                    customer_name=normalized['customer_name'],
                    company_domain=normalized['company_domain'],
                    contact_email=normalized['contact_email'],
                    license_id=normalized['license_id'],
                    product_type=normalized['product_type'],
                    license_status=normalized['license_status'],
                    license_start_date=normalized['license_start_date'],
                    license_end_date=normalized['license_end_date'],
                    tenant_id=normalized['tenant_id'],
                    usage_count=normalized['usage_count'],
                    migrated=normalized['migrated'],
                    created_date=normalized['created_date'],
                    contact_name=normalized['contact_name'],
                    phone=normalized['phone'],
                    address=normalized['address'],
                    city=normalized['city'],
                    state=normalized['state']
                ).on_conflict_do_update(
                    index_elements=['snapshot_date', 'customer_id'],
                    set_={
                        'customer_name': normalized['customer_name'],
                        'company_domain': normalized['company_domain'],
                        'contact_email': normalized['contact_email'],
                        'license_id': normalized['license_id'],
                        'product_type': normalized['product_type'],
                        'license_status': normalized['license_status'],
                        'license_start_date': normalized['license_start_date'],
                        'license_end_date': normalized['license_end_date'],
                        'tenant_id': normalized['tenant_id'],
                        'usage_count': normalized['usage_count'],
                        'migrated': normalized['migrated'],
                        'created_date': normalized['created_date'],
                        'contact_name': normalized['contact_name'],
                        'phone': normalized['phone'],
                        'address': normalized['address'],
                        'city': normalized['city'],
                        'state': normalized['state']
                    }
                )
                session.execute(stmt)

                logger.info(f"Inserted snapshot for customer {normalized['customer_id']}: {normalized['customer_name']}")
                saved_count += 1

                # Log progress every 10 customers
                if customer_count % 10 == 0:
                    logger.info(f"Progress: {customer_count} customers processed, {saved_count} saved")

            except Exception as e:
                error_count += 1
                logger.error(f"Error processing customer {customer_name}: {e}")

                # Handle SQLAlchemy errors by rolling back
                try:
                    from sqlalchemy.exc import SQLAlchemyError
                    if isinstance(e, SQLAlchemyError):
                        session.rollback()
                        logger.warning(f"Rolled back transaction for customer {customer_name}")
                except ImportError:
                    pass

                # Continue processing other customers
                continue

        # Commit all changes
        session.commit()

    logger.info(f"Collection completed. Processed: {customer_count}, "
                f"Saved: {saved_count}, Errors: {error_count}")

    if error_count > 0:
        logger.warning(f"{error_count} customers failed to process")


if __name__ == '__main__':
    main()

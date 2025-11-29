"""Duo MFA collector main CLI."""

import argparse
import json
import sys
from datetime import datetime, date
from typing import Optional

from common.logging import get_logger
from common.job_logging import log_job_start, log_job_completion, log_job_failure

from .api import DuoAPI
from .mapping import normalize_duo_account, normalize_duo_users


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description='Duo MFA collector')
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
        help='Limit number of accounts to process'
    )

    args = parser.parse_args()

    # Set up logging
    logger = get_logger(__name__)

    # Log job start
    job_run_id = None
    if not args.dry_run:
        job_run_id = log_job_start('duo-collector', f'Starting collection for date: {args.date}')

    try:
        # Parse the date
        snapshot_date = datetime.strptime(args.date, '%Y-%m-%d').date()
        logger.info(f"Starting Duo collection for date: {snapshot_date}")

        if args.dry_run:
            logger.info("DRY RUN MODE - no data will be saved to database")

        if args.limit:
            logger.info(f"Limiting collection to {args.limit} accounts")

        # Initialize Duo API
        logger.info("Initializing Duo API client")
        api = DuoAPI()

        # Process accounts
        if args.dry_run:
            run_dry_run(api, args.limit, logger)
        else:
            run_collection(api, snapshot_date, args.limit, logger)

        logger.info("Duo collection completed successfully")

        # Log job completion
        if job_run_id:
            log_job_completion(job_run_id, 'completed', 'Collection completed successfully')

    except Exception as e:
        logger.error(f"Duo collection failed: {e}")

        # Log job failure
        if job_run_id:
            log_job_failure(job_run_id, str(e))

        sys.exit(1)


def run_dry_run(api: DuoAPI, limit: Optional[int], logger) -> None:
    """Run in dry-run mode: fetch and normalize data, then print it."""
    logger.info("Starting dry run - fetching and normalizing accounts")

    # Get list of child accounts
    accounts = api.list_accounts()
    logger.info(f"Found {len(accounts)} child accounts")

    account_count = 0

    for account in accounts:
        account_count += 1

        if limit and account_count > limit:
            break

        account_id = account.get('account_id', '')
        org_name = account.get('name', f'Account-{account_count}')
        logger.info(f"Processing account {account_count}: {org_name}")

        try:
            # Fetch all data for this account
            users = api.get_users(account_id)
            phones = api.get_phones(account_id)
            groups = api.get_groups(account_id)
            integrations = api.get_integrations(account_id)
            webauthn = api.get_webauthn_credentials(account_id)
            settings = api.get_settings(account_id)
            info = api.get_info(account_id)
            auth_logs = api.get_auth_logs(account_id)
            telephony_logs = api.get_telephony_logs(account_id)

            logger.info(f"  Users: {len(users)}, Phones: {len(phones)}, "
                       f"Groups: {len(groups)}, Integrations: {len(integrations)}")

            # Normalize the data
            normalized = normalize_duo_account(
                account, users, phones, groups, integrations,
                webauthn, settings, info, auth_logs, telephony_logs
            )

            # Print normalized data
            print(f"\n--- Account {account_count}: {org_name} ---")
            print(json.dumps(normalized, indent=2, default=str))

        except Exception as e:
            logger.error(f"Error processing account {org_name}: {e}")
            continue

    logger.info(f"Dry run completed. Processed {account_count} accounts.")


def run_collection(api: DuoAPI, snapshot_date: date, limit: Optional[int], logger) -> None:
    """Run actual collection: fetch, normalize, and save data to database."""
    logger.info("Starting real collection - saving to database")

    # Import database modules only when needed
    from common.config import get_dsn
    from common.db import session_scope
    from storage.schema import DuoSnapshot, DuoUserSnapshot, Vendor
    from sqlalchemy.dialects.postgresql import insert

    # Check database connection
    try:
        dsn = get_dsn()
        logger.info("Database connection configured")
    except Exception as e:
        logger.error(f"Database configuration error: {e}")
        raise

    # Get list of child accounts
    accounts = api.list_accounts()
    logger.info(f"Found {len(accounts)} child accounts")

    account_count = 0
    saved_count = 0
    user_saved_count = 0
    error_count = 0

    # Process accounts using session scope
    with session_scope() as session:
        # Ensure Duo vendor exists
        vendor = session.query(Vendor).filter_by(name='Duo').first()
        if not vendor:
            vendor = Vendor(name='Duo')
            session.add(vendor)
            session.flush()
            logger.info("Created Duo vendor record")

        # Delete existing snapshots for this date to ensure clean daily data
        logger.info(f"Deleting existing Duo snapshots for {snapshot_date}")
        deleted_count = session.query(DuoSnapshot).filter(
            DuoSnapshot.snapshot_date == snapshot_date
        ).delete()
        deleted_user_count = session.query(DuoUserSnapshot).filter(
            DuoUserSnapshot.snapshot_date == snapshot_date
        ).delete()
        session.commit()
        logger.info(f"Deleted {deleted_count} account snapshots and {deleted_user_count} user snapshots for {snapshot_date}")

        for account in accounts:
            account_count += 1

            if limit and account_count > limit:
                break

            try:
                account_id = account.get('account_id', '')
                org_name = account.get('name', f'Account-{account_count}')
                logger.info(f"Processing account {account_count}: {org_name}")

                # Fetch all data for this account
                users = api.get_users(account_id)
                phones = api.get_phones(account_id)
                groups = api.get_groups(account_id)
                integrations = api.get_integrations(account_id)
                webauthn = api.get_webauthn_credentials(account_id)
                settings = api.get_settings(account_id)
                info = api.get_info(account_id)
                auth_logs = api.get_auth_logs(account_id)
                telephony_logs = api.get_telephony_logs(account_id)

                logger.info(f"  Users: {len(users)}, Phones: {len(phones)}, "
                           f"Groups: {len(groups)}, Integrations: {len(integrations)}")

                # Normalize the data
                normalized = normalize_duo_account(
                    account, users, phones, groups, integrations,
                    webauthn, settings, info, auth_logs, telephony_logs
                )

                if not normalized['account_id']:
                    logger.warning(f"Skipping account without ID: {org_name}")
                    continue

                # Use upsert to handle duplicate (snapshot_date, account_id)
                stmt = insert(DuoSnapshot).values(
                    snapshot_date=snapshot_date,
                    account_id=normalized['account_id'],
                    organization_name=normalized['organization_name'],
                    user_count=normalized['user_count'],
                    admin_count=normalized['admin_count'],
                    integration_count=normalized['integration_count'],
                    phone_count=normalized['phone_count'],
                    status=normalized['status'],
                    last_activity=normalized['last_activity'],
                    group_count=normalized['group_count'],
                    webauthn_count=normalized['webauthn_count'],
                    last_login=normalized['last_login'],
                    enrollment_pct=normalized['enrollment_pct'],
                    auth_methods=normalized['auth_methods'],
                    directory_sync=normalized['directory_sync'],
                    telephony_credits=normalized['telephony_credits'],
                    auth_volume=normalized['auth_volume'],
                    failed_auth_pct=normalized['failed_auth_pct'],
                    peak_usage=normalized['peak_usage'],
                    account_type=normalized['account_type']
                ).on_conflict_do_update(
                    index_elements=['snapshot_date', 'account_id'],
                    set_={
                        'organization_name': normalized['organization_name'],
                        'user_count': normalized['user_count'],
                        'admin_count': normalized['admin_count'],
                        'integration_count': normalized['integration_count'],
                        'phone_count': normalized['phone_count'],
                        'status': normalized['status'],
                        'last_activity': normalized['last_activity'],
                        'group_count': normalized['group_count'],
                        'webauthn_count': normalized['webauthn_count'],
                        'last_login': normalized['last_login'],
                        'enrollment_pct': normalized['enrollment_pct'],
                        'auth_methods': normalized['auth_methods'],
                        'directory_sync': normalized['directory_sync'],
                        'telephony_credits': normalized['telephony_credits'],
                        'auth_volume': normalized['auth_volume'],
                        'failed_auth_pct': normalized['failed_auth_pct'],
                        'peak_usage': normalized['peak_usage'],
                        'account_type': normalized['account_type']
                    }
                )
                session.execute(stmt)

                logger.info(f"Inserted snapshot for {normalized['account_id']}: {normalized['organization_name']}")
                saved_count += 1

                # Save user-level data
                user_records = normalize_duo_users(account_id, org_name, users, phones)
                for user_record in user_records:
                    user_stmt = insert(DuoUserSnapshot).values(
                        snapshot_date=snapshot_date,
                        account_id=user_record['account_id'],
                        organization_name=user_record['organization_name'],
                        user_id=user_record['user_id'],
                        username=user_record['username'],
                        full_name=user_record['full_name'],
                        email=user_record['email'],
                        status=user_record['status'],
                        last_login=user_record['last_login'],
                        phone=user_record['phone'],
                        is_enrolled=user_record['is_enrolled']
                    ).on_conflict_do_update(
                        index_elements=['snapshot_date', 'account_id', 'user_id'],
                        set_={
                            'organization_name': user_record['organization_name'],
                            'username': user_record['username'],
                            'full_name': user_record['full_name'],
                            'email': user_record['email'],
                            'status': user_record['status'],
                            'last_login': user_record['last_login'],
                            'phone': user_record['phone'],
                            'is_enrolled': user_record['is_enrolled']
                        }
                    )
                    session.execute(user_stmt)
                    user_saved_count += 1

                logger.info(f"  Saved {len(user_records)} users for {org_name}")

                # Log progress every 10 accounts
                if account_count % 10 == 0:
                    logger.info(f"Progress: {account_count} accounts processed, {saved_count} saved, {user_saved_count} users")

            except Exception as e:
                error_count += 1
                logger.error(f"Error processing account {org_name}: {e}")

                # Handle SQLAlchemy errors by rolling back
                try:
                    from sqlalchemy.exc import SQLAlchemyError
                    if isinstance(e, SQLAlchemyError):
                        session.rollback()
                        logger.warning(f"Rolled back transaction for {org_name}")
                except ImportError:
                    pass

                # Continue processing other accounts
                continue

        # Commit all changes
        session.commit()

    logger.info(f"Collection completed. Processed: {account_count}, "
                f"Saved: {saved_count} accounts, {user_saved_count} users, Errors: {error_count}")

    if error_count > 0:
        logger.warning(f"{error_count} accounts failed to process")


if __name__ == '__main__':
    main()

"""Ninja collector main CLI."""

import argparse
import json
import sys
from datetime import datetime, date
from typing import Optional

from common.logging import get_logger
from common.util import utcnow, sha256_json, upsert_device_identity, insert_snapshot

from .api import NinjaAPI
from .mapping import normalize_ninja_device


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description='Ninja device collector')
    parser.add_argument(
        '--date', 
        type=str, 
        default=date.today().strftime('%Y-%m-%d'),
        help='Date for snapshot in YYYY-MM-DD format (default: today)'
    )
    parser.add_argument(
        '--dry-run', 
        action='store_true',
        help='Fetch and normalize devices but do not save to database'
    )
    parser.add_argument(
        '--limit', 
        type=int,
        help='Limit number of devices to process'
    )
    
    args = parser.parse_args()
    
    # Set up logging
    logger = get_logger(__name__)
    
    try:
        # Parse the date
        snapshot_date = datetime.strptime(args.date, '%Y-%m-%d').date()
        logger.info(f"Starting Ninja collection for date: {snapshot_date}")
        
        if args.dry_run:
            logger.info("DRY RUN MODE - no data will be saved to database")
        
        if args.limit:
            logger.info(f"Limiting collection to {args.limit} devices")
        
        # Initialize Ninja API
        logger.info("Initializing Ninja API client")
        ninja_api = NinjaAPI()
        
        # Process devices
        if args.dry_run:
            run_dry_run(ninja_api, args.limit, logger)
        else:
            run_collection(ninja_api, snapshot_date, args.limit, logger)
            
        logger.info("Ninja collection completed successfully")
        
    except Exception as e:
        logger.error(f"Ninja collection failed: {e}")
        sys.exit(1)


def run_dry_run(ninja_api: NinjaAPI, limit: Optional[int], logger) -> None:
    """Run in dry-run mode: fetch and normalize devices, then print them."""
    logger.info("Starting dry run - fetching and normalizing devices")
    
    device_count = 0
    
    for raw_device in ninja_api.list_devices(limit=limit):
        device_count += 1
        logger.info(f"Processing device {device_count}: {raw_device.get('systemName', 'N/A')}")
        
        # Normalize the device
        normalized = normalize_ninja_device(raw_device)
        
        # Print normalized device dict
        print(f"\n--- Device {device_count} ---")
        print(json.dumps(normalized, indent=2, default=str))
    
    logger.info(f"Dry run completed. Processed {device_count} devices.")


def run_collection(ninja_api: NinjaAPI, snapshot_date: date, limit: Optional[int], logger) -> None:
    """Run actual collection: fetch, normalize, and save devices to database."""
    logger.info("Starting real collection - saving to database")
    
    # Import database modules only when needed
    from common.config import get_dsn
    from common.db import session_scope
    
    # Check database connection
    try:
        dsn = get_dsn()
        logger.info("Database connection configured")
    except Exception as e:
        logger.error(f"Database configuration error: {e}")
        raise
    
    device_count = 0
    saved_count = 0
    error_count = 0
    
    # Process devices in batches using session scope
    with session_scope() as session:
        # Import here to avoid circular imports
        from storage.schema import Vendor
        
        # Get or create Ninja vendor
        vendor = session.query(Vendor).filter_by(name='Ninja').first()
        if not vendor:
            vendor = Vendor(name='Ninja')
            session.add(vendor)
            session.flush()  # Get the ID
            logger.info("Created Ninja vendor record")
        
        vendor_id = vendor.id
        logger.info(f"Using vendor ID: {vendor_id}")
        
        # Ensure required reference data exists
        _ensure_reference_data(session, logger)
        
        for raw_device in ninja_api.list_devices(limit=limit):
            device_count += 1
            device_name = raw_device.get('systemName', f'Device-{device_count}')
            
            try:
                logger.info(f"Processing device {device_count}: {device_name}")
                
                # Normalize the device
                normalized = normalize_ninja_device(raw_device)
                
                # Upsert device identity
                device_identity_id = upsert_device_identity(
                    session=session,
                    vendor_id=vendor_id,
                    vendor_device_key=normalized['vendor_device_key'],
                    first_seen_date=snapshot_date
                )
                logger.debug(f"Upserted device identity ID: {device_identity_id}")
                
                # Insert snapshot
                insert_snapshot(
                    session=session,
                    snapshot_date=snapshot_date,
                    vendor_id=vendor_id,
                    device_identity_id=device_identity_id,
                    normalized=normalized
                )
                
                logger.info(f"Inserted snapshot for device {normalized['vendor_device_key']} "
                           f"with type: {normalized['device_type']}, billing: {normalized['billing_status']}")
                
                saved_count += 1
                
                # Log progress every 50 devices
                if device_count % 50 == 0:
                    logger.info(f"Progress: {device_count} devices processed, {saved_count} saved")
                
            except Exception as e:
                error_count += 1
                logger.error(f"Error processing device {device_name}: {e}")
                
                # Handle SQLAlchemy errors by rolling back
                try:
                    from sqlalchemy.exc import SQLAlchemyError
                    if isinstance(e, SQLAlchemyError):
                        session.rollback()
                        logger.warning(f"Rolled back transaction for device {device_name}")
                except ImportError:
                    pass
                
                # Continue processing other devices
                continue
    
    logger.info(f"Collection completed. Processed: {device_count}, "
               f"Saved: {saved_count}, Errors: {error_count}")
    
    if error_count > 0:
        logger.warning(f"{error_count} devices failed to process")


def _ensure_reference_data(session, logger) -> None:
    """Ensure required reference data exists in the database."""
    from storage.schema import DeviceType, BillingStatus
    
    # Device types
    device_types = ['server', 'workstation', 'unknown']
    for device_type_code in device_types:
        if not session.query(DeviceType).filter_by(code=device_type_code).first():
            device_type = DeviceType(code=device_type_code)
            session.add(device_type)
            logger.info(f"Created device type: {device_type_code}")
    
    # Billing statuses
    billing_statuses = ['billable', 'spare', 'unknown']
    for billing_status_code in billing_statuses:
        if not session.query(BillingStatus).filter_by(code=billing_status_code).first():
            billing_status = BillingStatus(code=billing_status_code)
            session.add(billing_status)
            logger.info(f"Created billing status: {billing_status_code}")
    
    # Flush to ensure they're available for lookups
    session.flush()


if __name__ == '__main__':
    main()

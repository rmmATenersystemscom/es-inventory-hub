"""ThreatLocker collector main CLI."""

import argparse
import sys
from typing import Optional, Dict, Any

from .log import get_logger
from .api import fetch_devices
from .normalize import build_row


def get_session():
    """
    Get database session using the same pattern as Ninja collector.
    
    Returns:
        Session: SQLAlchemy session
    """
    from common.db import session_scope
    return session_scope()


def get_id_maps(session: Any) -> Dict[str, Dict[str, int]]:
    """
    Get ID mappings for vendors, billing statuses, and device types.
    
    Args:
        session: Database session
        
    Returns:
        dict: Dictionary containing ID mappings for all lookup tables
    """
    from storage.schema import Vendor, DeviceType
    
    # Get vendor IDs
    vendors = session.query(Vendor).all()
    vendor_map = {v.name.lower(): v.id for v in vendors}
    
    # Get device type IDs
    device_types = session.query(DeviceType).all()
    device_type_map = {dt.code: dt.id for dt in device_types}
    
    return {
        "vendor": vendor_map,
        "device_type": device_type_map
    }


def write_rows(session: Any, rows: list) -> Dict[str, int]:
    """
    Write normalized rows to device_snapshot with daily idempotency.
    
    For each row, check if a record exists with the same (snapshot_date, vendor_id=4, hostname_base).
    If exists → skip; else → INSERT into device_snapshot.
    
    Args:
        session: Database session
        rows: List of normalized device rows
        
    Returns:
        dict: Counts of {"processed": N, "inserted": X, "skipped": Y}
    """
    from storage.schema import DeviceSnapshot, DeviceIdentity, Vendor
    from common.util import upsert_device_identity
    
    processed = 0
    inserted = 0
    skipped = 0
    
    # Get ThreatLocker vendor ID
    vendor = session.query(Vendor).filter_by(name='ThreatLocker').first()
    if not vendor:
        vendor = Vendor(name='ThreatLocker')
        session.add(vendor)
        session.flush()
    
    vendor_id = vendor.id
    
    for row in rows:
        processed += 1
        
        # Create device identity for this device
        device_identity_id = upsert_device_identity(
            session=session,
            vendor_id=vendor_id,
            vendor_device_key=row['hostname_base'],  # Use hostname_base as device key
            first_seen_date=row['snapshot_date']
        )
        
        # TODO: The current schema uses device_identity_id for unique constraint,
        # but the requirement asks for hostname_base. This would need a migration
        # to add a unique constraint on (snapshot_date, vendor_id, hostname_base).
        # For now, we use the existing constraint with device_identity_id.
        
        # Check if snapshot already exists for this date/vendor/device
        existing = session.query(DeviceSnapshot).filter_by(
            snapshot_date=row['snapshot_date'],
            vendor_id=vendor_id,
            device_identity_id=device_identity_id
        ).first()
        
        if existing:
            skipped += 1
            continue
        
        # Insert new snapshot
        try:
            snapshot = DeviceSnapshot(
                snapshot_date=row['snapshot_date'],
                vendor_id=vendor_id,
                device_identity_id=device_identity_id,
                device_type_id=row['device_type_id'],
                hostname=row['hostname'],
                raw=row['raw']
            )
            
            session.add(snapshot)
            session.flush()  # Flush to check for constraint violations
            inserted += 1
        except Exception as e:
            # Handle unique constraint violations gracefully
            if "uq_device_snapshot_date_vendor_device" in str(e):
                session.rollback()
                skipped += 1
                continue
            else:
                raise
    
    return {
        "processed": processed,
        "inserted": inserted,
        "skipped": skipped
    }


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description='ThreatLocker device collector')
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
    parser.add_argument(
        '--since', 
        type=str,
        help='Date string to filter devices since (format: YYYY-MM-DD)'
    )
    
    args = parser.parse_args()
    
    # Set up logging
    logger = get_logger(__name__)
    
    try:
        logger.info("Starting ThreatLocker collection")
        
        if args.dry_run:
            logger.info("DRY RUN MODE - no data will be saved to database")
        
        if args.limit:
            logger.info(f"Limiting collection to {args.limit} devices")
        
        if args.since:
            logger.info(f"Filtering devices since: {args.since}")
        
        # Get database session and ID mappings
        logger.info("Loading ID mappings")
        with get_session() as session:
            ids = get_id_maps(session)
            logger.info("ID mappings loaded")
            
            # Fetch devices from ThreatLocker API
            logger.info("Fetching devices from ThreatLocker API")
            devices = fetch_devices(limit=args.limit, since=args.since)
            logger.info(f"Fetched {len(devices)} devices")
            
            # Normalize each device using pre-resolved IDs
            logger.info("Normalizing device data")
            rows = [build_row(tl, ids) for tl in devices]
            
            logger.info(f"Normalized {len(rows)} devices")
            
            # Write normalized devices to device_snapshot table
            if not args.dry_run:
                logger.info("Writing normalized devices to database")
                counts = write_rows(session, rows)
                logger.info(f"Database write completed: {counts['processed']} processed, "
                           f"{counts['inserted']} inserted, {counts['skipped']} skipped")
                
                # Run cross-vendor consistency checks
                logger.info("Running cross-vendor consistency checks")
                from collectors.checks.cross_vendor import run_cross_vendor_checks
                exception_counts = run_cross_vendor_checks(session)
                
                # Log exception counts
                total_exceptions = sum(exception_counts.values())
                if total_exceptions > 0:
                    logger.info(f"Cross-vendor checks completed: {total_exceptions} exceptions found")
                    for exception_type, count in exception_counts.items():
                        if count > 0:
                            logger.info(f"  {exception_type}: {count} exceptions")
                else:
                    logger.info("Cross-vendor checks completed: no exceptions found")
            else:
                logger.info("DRY RUN: Skipping database write and cross-vendor checks")
        
        logger.info("ThreatLocker collection completed successfully")
        
        # Exit with 0 on dry-run as specified
        if args.dry_run:
            sys.exit(0)
        
    except Exception as e:
        logger.error(f"ThreatLocker collection failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

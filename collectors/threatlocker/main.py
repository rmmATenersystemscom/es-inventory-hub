"""ThreatLocker collector main CLI."""

import argparse
import sys
from typing import Optional, Dict, Any

from .log import get_logger
from .api import fetch_devices
from .mapping import normalize_threatlocker_device
from common.util import insert_snapshot, upsert_device_identity
from datetime import date


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


def run_collection(session: Any, devices: list, snapshot_date: date) -> Dict[str, int]:
    """
    Run ThreatLocker collection using the new mapping approach.
    
    Args:
        session: Database session
        devices: List of raw device data from ThreatLocker API
        snapshot_date: Date for the snapshot
        
    Returns:
        dict: Counts of {"processed": N, "inserted": X, "skipped": Y}
    """
    from storage.schema import Vendor
    
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
    
    for device in devices:
        processed += 1
        
        try:
            # Normalize the device data
            normalized = normalize_threatlocker_device(device)
            
            # Create device identity for this device
            device_identity_id = upsert_device_identity(
                session=session,
                vendor_id=vendor_id,
                vendor_device_key=normalized['vendor_device_key'],
                first_seen_date=snapshot_date
            )
            
            # Insert the snapshot using the updated function
            insert_snapshot(
                session=session,
                snapshot_date=snapshot_date,
                vendor_id=vendor_id,
                device_identity_id=device_identity_id,
                normalized=normalized
            )
            
            inserted += 1
            
        except Exception as e:
            # Handle unique constraint violations gracefully
            if "uq_device_snapshot_date_vendor_device" in str(e):
                # Don't rollback the entire session, just skip this device
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
        
        # Get database session
        logger.info("Connecting to database")
        with get_session() as session:
            # Fetch devices from ThreatLocker API
            logger.info("Fetching devices from ThreatLocker API")
            devices = fetch_devices(limit=args.limit, since=args.since)
            logger.info(f"Fetched {len(devices)} devices")
            
            # Set snapshot date to today
            snapshot_date = date.today()
            
            if not args.dry_run:
                logger.info("Processing and inserting devices to database")
                counts = run_collection(session, devices, snapshot_date)
                logger.info(f"Database write completed: {counts['processed']} processed, "
                           f"{counts['inserted']} inserted, {counts['skipped']} skipped")
                
                # Skip cross-vendor consistency checks for now (raw column removed)
                logger.info("Skipping cross-vendor consistency checks (raw column removed from schema)")
            else:
                logger.info("DRY RUN: Normalizing device data without saving")
                for device in devices:
                    normalized = normalize_threatlocker_device(device)
                    logger.info(f"Normalized device: {normalized.get('hostname', 'Unknown')}")
                logger.info(f"DRY RUN: Processed {len(devices)} devices")
        
        logger.info("ThreatLocker collection completed successfully")
        
        # Exit with 0 on dry-run as specified
        if args.dry_run:
            sys.exit(0)
        
    except Exception as e:
        logger.error(f"ThreatLocker collection failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

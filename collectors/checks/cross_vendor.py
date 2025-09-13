"""Cross-vendor consistency checks between Ninja and ThreatLocker."""

import json
from datetime import date
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from storage.schema import DeviceSnapshot, Vendor, Exceptions


def to_base(hostname: str) -> str:
    """
    Convert hostname to base form (lowercase, first part before dot).
    Handle None safely by returning empty string.
    
    Args:
        hostname: Original hostname (can be None)
        
    Returns:
        str: Base hostname
    """
    if not hostname:
        return ''
    return hostname.lower().split('.')[0]


def get_vendor_ids(session: Session) -> Dict[str, int]:
    """
    Get vendor IDs for Ninja and ThreatLocker.
    
    Args:
        session: Database session
        
    Returns:
        dict: Mapping of vendor names to IDs
    """
    vendors = session.query(Vendor).filter(
        Vendor.name.in_(['Ninja', 'ThreatLocker'])
    ).all()
    
    return {v.name: v.id for v in vendors}


def clear_todays_exceptions(session: Session, snapshot_date: date) -> None:
    """
    Clear all exceptions for the given date to ensure idempotency.
    
    Args:
        session: Database session
        snapshot_date: Date to clear exceptions for
    """
    session.query(Exceptions).filter(
        Exceptions.date_found == snapshot_date
    ).delete()


def insert_exception(
    session: Session,
    exception_type: str,
    hostname: str,
    details: Dict[str, Any],
    snapshot_date: date
) -> bool:
    """
    Insert an exception record.
    
    Args:
        session: Database session
        exception_type: Type of exception (MISSING_NINJA, DUPLICATE_TL, etc.)
        hostname: Hostname for the exception
        details: JSON details about the exception
        snapshot_date: Date of the snapshot
        
    Returns:
        bool: True if exception was inserted
    """
    # Insert new exception
    exception = Exceptions(
        date_found=snapshot_date,
        type=exception_type,
        hostname=hostname,
        details=details,
        resolved=False
    )
    
    session.add(exception)
    return True


def check_missing_ninja(session: Session, vendor_ids: Dict[str, int], snapshot_date: date) -> int:
    """
    Check for ThreatLocker hosts that have no matching Ninja host using robust anchors.
    
    Uses canonical TL key: LOWER(LEFT(SPLIT_PART(hostname,'.',1),15))
    Uses canonical Ninja keys (ANY match true):
    1) LOWER(LEFT(SPLIT_PART(ds.hostname,'.',1),15))
    2) LOWER(LEFT(SPLIT_PART(COALESCE(ds.display_name,''),'.',1),15))
    
    Args:
        session: Database session
        vendor_ids: Mapping of vendor names to IDs
        snapshot_date: Date to check
        
    Returns:
        int: Number of exceptions inserted
    """
    if 'ThreatLocker' not in vendor_ids or 'Ninja' not in vendor_ids:
        return 0
    
    from sqlalchemy import text
    
    # First, delete today's rows for type='MISSING_NINJA' to ensure idempotency
    session.query(Exceptions).filter(
        and_(
            Exceptions.date_found == snapshot_date,
            Exceptions.type == 'MISSING_NINJA'
        )
    ).delete()
    
    # Use SQL to find ThreatLocker hosts with no matching Ninja host using robust anchors
    # Canonical TL key: LOWER(LEFT(SPLIT_PART(hostname,'.',1),15))
    # Canonical Ninja keys (ANY match true):
    # 1) LOWER(LEFT(SPLIT_PART(ds.hostname,'.',1),15))
    # 2) LOWER(LEFT(SPLIT_PART(COALESCE(ds.display_name,''),'.',1),15))
    
    # Add safeguard log line to confirm correct table name
    print("Cross-vendor checks running against table device_snapshot")
    
    query = text("""
        WITH tl_canonical AS (
            SELECT 
                ds.id,
                ds.hostname,
                LOWER(LEFT(SPLIT_PART(ds.hostname,'.',1),15)) as canonical_key
            FROM device_snapshot ds
            WHERE ds.snapshot_date = :snapshot_date
              AND ds.vendor_id = :tl_vendor_id
              AND ds.hostname IS NOT NULL
        ),
        ninja_canonical AS (
            SELECT DISTINCT
                LOWER(LEFT(SPLIT_PART(ds.hostname,'.',1),15)) as canonical_key
            FROM device_snapshot ds
            WHERE ds.snapshot_date = :snapshot_date
              AND ds.vendor_id = :ninja_vendor_id
              AND ds.hostname IS NOT NULL
            
            UNION
            
            SELECT DISTINCT
                LOWER(LEFT(SPLIT_PART(COALESCE(ds.display_name,''),'.',1),15)) as canonical_key
            FROM device_snapshot ds
            WHERE ds.snapshot_date = :snapshot_date
              AND ds.vendor_id = :ninja_vendor_id
              AND ds.display_name IS NOT NULL
              AND ds.display_name != ''
        )
        SELECT 
            tl.id,
            tl.hostname,
            tl.canonical_key
        FROM tl_canonical tl
        LEFT JOIN ninja_canonical nc ON tl.canonical_key = nc.canonical_key
        WHERE nc.canonical_key IS NULL
    """)
    
    result = session.execute(query, {
        'snapshot_date': snapshot_date,
        'tl_vendor_id': vendor_ids['ThreatLocker'],
        'ninja_vendor_id': vendor_ids['Ninja']
    })
    
    exceptions_inserted = 0
    
    for row in result:
        # Get site information
        tl_site_name = None
        tl_org_name = None
        
        # Get site name and org name from device snapshot
        tl_device = session.query(DeviceSnapshot).filter(DeviceSnapshot.id == row.id).first()
        if tl_device:
            if tl_device.site:
                tl_site_name = tl_device.site.name
            tl_org_name = tl_device.organization_name
        
        details = {
            'tl_hostname': row.hostname,
            'tl_canonical_key': row.canonical_key,
            'tl_site_name': tl_site_name,
            'tl_org_name': tl_org_name
        }
        
        if insert_exception(session, 'MISSING_NINJA', row.hostname, details, snapshot_date):
            exceptions_inserted += 1
    
    # Log the inserted count
    print(f"MISSING_NINJA: Inserted {exceptions_inserted} exceptions for {snapshot_date}")
    
    return exceptions_inserted


def check_duplicate_tl(session: Session, vendor_ids: Dict[str, int], snapshot_date: date) -> int:
    """
    Check for duplicate ThreatLocker hosts (same hostname_base count > 1).
    
    Args:
        session: Database session
        vendor_ids: Mapping of vendor names to IDs
        snapshot_date: Date to check
        
    Returns:
        int: Number of exceptions inserted
    """
    if 'ThreatLocker' not in vendor_ids:
        return 0
    
    # Query for duplicate hostname_base values in ThreatLocker data
    # Use LEFT(LOWER(SPLIT_PART(hostname, '.', 1)), 15) normalization
    duplicates = session.query(
        func.left(
            func.lower(func.split_part(DeviceSnapshot.hostname, '.', 1)), 15
        ).label('hostname_base'),
        func.count().label('count')
    ).filter(
        and_(
            DeviceSnapshot.snapshot_date == snapshot_date,
            DeviceSnapshot.vendor_id == vendor_ids['ThreatLocker'],
            DeviceSnapshot.hostname.isnot(None)
        )
    ).group_by(
        func.left(
            func.lower(func.split_part(DeviceSnapshot.hostname, '.', 1)), 15
        )
    ).having(
        func.count() > 1
    ).all()
    
    exceptions_inserted = 0
    
    for duplicate in duplicates:
        hostname_base = duplicate.hostname_base
        
        # Get all ThreatLocker hosts with this hostname_base
        tl_hosts = session.query(DeviceSnapshot).filter(
            and_(
                DeviceSnapshot.snapshot_date == snapshot_date,
                DeviceSnapshot.vendor_id == vendor_ids['ThreatLocker'],
                func.left(
                    func.lower(func.split_part(DeviceSnapshot.hostname, '.', 1)), 15
                ) == hostname_base
            )
        ).all()
        
        # Create details with all duplicate hostnames
        hostnames = [host.hostname for host in tl_hosts if host.hostname]
        details = {
            'hostname_base': hostname_base,
            'count': duplicate.count,
            'duplicate_hostnames': hostnames,
            'sites': [host.site.name if host.site else None for host in tl_hosts]
        }
        
        # Insert exception for the first hostname (representative)
        if hostnames and insert_exception(session, 'DUPLICATE_TL', hostnames[0], details, snapshot_date):
            exceptions_inserted += 1
    
    return exceptions_inserted


def check_site_mismatch(session: Session, vendor_ids: Dict[str, int], snapshot_date: date) -> int:
    """
    Check for site/org mismatch between matching Ninja and ThreatLocker hosts.
    
    Args:
        session: Database session
        vendor_ids: Mapping of vendor names to IDs
        snapshot_date: Date to check
        
    Returns:
        int: Number of exceptions inserted
    """
    if 'ThreatLocker' not in vendor_ids or 'Ninja' not in vendor_ids:
        return 0
    
    # Get all ThreatLocker hosts for the snapshot date
    tl_hosts = session.query(DeviceSnapshot).filter(
        and_(
            DeviceSnapshot.snapshot_date == snapshot_date,
            DeviceSnapshot.vendor_id == vendor_ids['ThreatLocker']
        )
    ).all()
    
    # Get all Ninja hosts for the snapshot date
    ninja_hosts = session.query(DeviceSnapshot).filter(
        and_(
            DeviceSnapshot.snapshot_date == snapshot_date,
            DeviceSnapshot.vendor_id == vendor_ids['Ninja']
        )
    ).all()
    
    # Create mapping of normalized hostname to Ninja host using SQL normalization
    ninja_by_base = {}
    for ninja_host in ninja_hosts:
        if ninja_host.hostname:
            # Use SQL normalization: LEFT(LOWER(SPLIT_PART(hostname, '.', 1)), 15)
            normalized_hostname = session.query(
                func.left(
                    func.lower(func.split_part(DeviceSnapshot.hostname, '.', 1)), 15
                )
            ).filter(DeviceSnapshot.id == ninja_host.id).scalar()
            ninja_by_base[normalized_hostname] = ninja_host
    
    exceptions_inserted = 0
    
    # Check each ThreatLocker host
    for tl_host in tl_hosts:
        if not tl_host.hostname:
            continue
            
        # Use SQL normalization: LEFT(LOWER(SPLIT_PART(hostname, '.', 1)), 15)
        tl_normalized = session.query(
            func.left(
                func.lower(func.split_part(DeviceSnapshot.hostname, '.', 1)), 15
            )
        ).filter(DeviceSnapshot.id == tl_host.id).scalar()
        
        # If matching Ninja host found
        if tl_normalized in ninja_by_base:
            ninja_host = ninja_by_base[tl_normalized]
            
            # Get site names
            tl_site = tl_host.site.name if tl_host.site else None
            ninja_site = ninja_host.site.name if ninja_host.site else None
            
            # Check for site mismatch
            if tl_site != ninja_site:
                details = {
                    'hostname_base': tl_normalized,
                    'tl_hostname': tl_host.hostname,
                    'ninja_hostname': ninja_host.hostname,
                    'tl_site': tl_site,
                    'ninja_site': ninja_site,
                    'tl_org': tl_host.organization_name,
                    'ninja_org': ninja_host.organization_name
                }
                
                if insert_exception(session, 'SITE_MISMATCH', tl_host.hostname, details, snapshot_date):
                    exceptions_inserted += 1
    
    return exceptions_inserted


def check_spare_mismatch(session: Session, vendor_ids: Dict[str, int], snapshot_date: date) -> int:
    """
    Check for spare mismatch: ThreatLocker present but Ninja marks as spare.
    
    Since only Ninja determines billing status, this check identifies devices that:
    - Exist in both ThreatLocker and Ninja
    - Are marked as 'spare' in Ninja (meaning they shouldn't be billed)
    - Are still present in ThreatLocker (which may indicate they need cleanup)
    
    Args:
        session: Database session
        vendor_ids: Mapping of vendor names to IDs
        snapshot_date: Date to check
        
    Returns:
        int: Number of exceptions inserted
    """
    if 'ThreatLocker' not in vendor_ids or 'Ninja' not in vendor_ids:
        return 0
    
    # Get all ThreatLocker hosts for the snapshot date
    tl_hosts = session.query(DeviceSnapshot).filter(
        and_(
            DeviceSnapshot.snapshot_date == snapshot_date,
            DeviceSnapshot.vendor_id == vendor_ids['ThreatLocker']
        )
    ).all()
    
    # Get all Ninja hosts for the snapshot date
    ninja_hosts = session.query(DeviceSnapshot).filter(
        and_(
            DeviceSnapshot.snapshot_date == snapshot_date,
            DeviceSnapshot.vendor_id == vendor_ids['Ninja']
        )
    ).all()
    
    # Create mapping of normalized hostname to Ninja host using SQL normalization
    ninja_by_base = {}
    for ninja_host in ninja_hosts:
        if ninja_host.hostname:
            # Use SQL normalization: LEFT(LOWER(SPLIT_PART(hostname, '.', 1)), 15)
            normalized_hostname = session.query(
                func.left(
                    func.lower(func.split_part(DeviceSnapshot.hostname, '.', 1)), 15
                )
            ).filter(DeviceSnapshot.id == ninja_host.id).scalar()
            ninja_by_base[normalized_hostname] = ninja_host
    
    exceptions_inserted = 0
    
    # Check each ThreatLocker host
    for tl_host in tl_hosts:
        if not tl_host.hostname:
            continue
            
        # Use SQL normalization: LEFT(LOWER(SPLIT_PART(hostname, '.', 1)), 15)
        tl_normalized = session.query(
            func.left(
                func.lower(func.split_part(DeviceSnapshot.hostname, '.', 1)), 15
            )
        ).filter(DeviceSnapshot.id == tl_host.id).scalar()
        
        # If matching Ninja host found
        if tl_normalized in ninja_by_base:
            ninja_host = ninja_by_base[tl_normalized]
            
            # Check if Ninja marks this as spare
            is_ninja_spare = False
            if ninja_host.billing_status and ninja_host.billing_status.code == 'spare':
                is_ninja_spare = True
            
            # If Ninja marks as spare, this may indicate a cleanup opportunity
            if is_ninja_spare:
                details = {
                    'hostname_base': tl_normalized,
                    'tl_hostname': tl_host.hostname,
                    'ninja_hostname': ninja_host.hostname,
                    'ninja_billing_status': ninja_host.billing_status.code if ninja_host.billing_status else None,
                    'tl_site': tl_host.site.name if tl_host.site else None,
                    'ninja_site': ninja_host.site.name if ninja_host.site else None,
                    'note': 'Device marked as spare in Ninja - consider if ThreatLocker cleanup needed'
                }
                
                if insert_exception(session, 'SPARE_MISMATCH', tl_host.hostname, details, snapshot_date):
                    exceptions_inserted += 1
    
    return exceptions_inserted


def run_cross_vendor_checks(session: Session, snapshot_date: Optional[date] = None) -> Dict[str, int]:
    """
    Run all cross-vendor consistency checks between Ninja and ThreatLocker.
    
    Args:
        session: Database session
        snapshot_date: Date to check (defaults to today)
        
    Returns:
        dict: Count of exceptions inserted by type
    """
    if snapshot_date is None:
        snapshot_date = date.today()
    
    # Get vendor IDs
    vendor_ids = get_vendor_ids(session)
    
    # Clear today's exceptions for idempotency
    clear_todays_exceptions(session, snapshot_date)
    
    # Run all checks
    results = {}
    
    results['MISSING_NINJA'] = check_missing_ninja(session, vendor_ids, snapshot_date)
    results['DUPLICATE_TL'] = check_duplicate_tl(session, vendor_ids, snapshot_date)
    results['SITE_MISMATCH'] = check_site_mismatch(session, vendor_ids, snapshot_date)
    results['SPARE_MISMATCH'] = check_spare_mismatch(session, vendor_ids, snapshot_date)
    
    return results

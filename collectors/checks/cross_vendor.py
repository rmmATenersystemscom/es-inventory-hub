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


def validate_data_quality(session: Session, vendor_ids: Dict[str, int], snapshot_date: date) -> Dict[str, int]:
    """
    Validate data quality by checking for field mapping violations.
    
    This function detects when wrong fields are being used:
    - ThreatLocker: pipe symbols in hostname indicate computerName field usage
    - Ninja: missing systemName field indicates wrong field mapping
    
    Args:
        session: Database session
        vendor_ids: Mapping of vendor names to IDs
        snapshot_date: Date to check
        
    Returns:
        dict: Count of data quality issues found by vendor
    """
    from sqlalchemy import text
    
    issues_found = {'ThreatLocker': 0, 'Ninja': 0}
    
    # Check ThreatLocker data quality
    if 'ThreatLocker' in vendor_ids:
        tl_query = text("""
            SELECT COUNT(*) as count
            FROM device_snapshot ds
            WHERE ds.snapshot_date = :snapshot_date
              AND ds.vendor_id = :tl_vendor_id
              AND ds.hostname IS NOT NULL
              AND ds.hostname LIKE '%|%'
        """)
        
        result = session.execute(tl_query, {
            'snapshot_date': snapshot_date,
            'tl_vendor_id': vendor_ids['ThreatLocker']
        })
        
        tl_issues = result.scalar()
        issues_found['ThreatLocker'] = tl_issues
        
        if tl_issues > 0:
            print(f"WARNING: Found {tl_issues} ThreatLocker devices with pipe symbols in hostname")
            print("  This indicates computerName field was used instead of hostname field")
            print("  These devices need to be re-collected with correct field mapping")
    
    # Check Ninja data quality
    if 'Ninja' in vendor_ids:
        ninja_query = text("""
            SELECT COUNT(*) as count
            FROM device_snapshot ds
            WHERE ds.snapshot_date = :snapshot_date
              AND ds.vendor_id = :ninja_vendor_id
              AND (ds.hostname IS NULL OR ds.hostname = '')
        """)
        
        result = session.execute(ninja_query, {
            'snapshot_date': snapshot_date,
            'ninja_vendor_id': vendor_ids['Ninja']
        })
        
        ninja_issues = result.scalar()
        issues_found['Ninja'] = ninja_issues
        
        if ninja_issues > 0:
            print(f"WARNING: Found {ninja_issues} Ninja devices with missing hostname")
            print("  This indicates systemName field was not properly mapped")
            print("  These devices need to be re-collected with correct field mapping")
    
    return issues_found


def extract_clean_hostname(stored_hostname: str, canonical_key: str) -> str:
    """
    Extract clean hostname from stored data, handling data quality issues.
    
    Args:
        stored_hostname: Hostname as stored in database (may contain pipe symbols)
        canonical_key: Clean canonical key from SQL normalization (already cleaned)
        
    Returns:
        str: Clean hostname for display
    """
    # The canonical_key is already clean (extracted from SQL with pipe symbol handling)
    # Use it as the clean hostname for display
    return canonical_key


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
    # Canonical Ninja key: LOWER(LEFT(SPLIT_PART(ds.hostname,'.',1),15))
    # Note: display_name is never used as anchor for device matching
    
    # Add safeguard log line to confirm correct table name
    print("Cross-vendor checks running against table device_snapshot")
    
    query = text("""
        WITH tl_canonical AS (
            SELECT 
                ds.id,
                ds.hostname,
                -- Extract clean hostname: take first part before pipe symbol, then first part before dot, then first 15 chars
                LOWER(LEFT(SPLIT_PART(SPLIT_PART(ds.hostname,'|',1),'.',1),15)) as canonical_key
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
        # Extract clean hostname from canonical key to avoid pipe symbols
        # The canonical_key is the clean hostname (e.g., "chi-1p397h2")
        clean_hostname = row.canonical_key
        
        # Validate data quality - check if stored hostname contains pipe symbols
        # This indicates the wrong field (computerName) was used instead of hostname
        data_quality_issue = False
        if row.hostname and '|' in row.hostname:
            data_quality_issue = True
            print(f"WARNING: Data quality issue detected - ThreatLocker device {row.id} has pipe symbols in hostname: '{row.hostname}'")
            print(f"  This indicates computerName field was used instead of hostname field")
            print(f"  Using clean hostname from canonical key: '{clean_hostname}'")
        
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
            'tl_hostname': clean_hostname,  # Use clean hostname instead of potentially corrupted row.hostname
            'tl_canonical_key': row.canonical_key,
            'tl_site_name': tl_site_name,
            'tl_org_name': tl_org_name,
            'data_quality_issue': data_quality_issue,
            'original_stored_hostname': row.hostname if data_quality_issue else None
        }
        
        if insert_exception(session, 'MISSING_NINJA', clean_hostname, details, snapshot_date):
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
        
        # Create details with all duplicate hostnames (use clean hostnames)
        clean_hostnames = []
        organizations = []
        for host in tl_hosts:
            if host.hostname:
                # Extract clean hostname, handling data quality issues
                clean_hostname = extract_clean_hostname(host.hostname, hostname_base)
                clean_hostnames.append(clean_hostname)
                # Collect organization information
                if host.organization_name:
                    organizations.append(host.organization_name)
        
        # Get the most common organization (or first one if all different)
        primary_org = organizations[0] if organizations else None
        
        details = {
            'hostname_base': hostname_base,
            'count': duplicate.count,
            'duplicate_hostnames': clean_hostnames,
            'sites': [host.site.name if host.site else None for host in tl_hosts],
            'organizations': organizations,
            'tl_org_name': primary_org  # Primary organization for API compatibility
        }
        
        # Insert exception for the first clean hostname (representative)
        if clean_hostnames and insert_exception(session, 'DUPLICATE_TL', clean_hostnames[0], details, snapshot_date):
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
                # Extract clean hostnames for display
                tl_clean_hostname = extract_clean_hostname(tl_host.hostname, tl_normalized)
                ninja_clean_hostname = extract_clean_hostname(ninja_host.hostname, tl_normalized)
                
                details = {
                    'hostname_base': tl_normalized,
                    'tl_hostname': tl_clean_hostname,
                    'ninja_hostname': ninja_clean_hostname,
                    'tl_site': tl_site,
                    'ninja_site': ninja_site,
                    'tl_org': tl_host.organization_name,
                    'ninja_org': ninja_host.organization_name
                }
                
                if insert_exception(session, 'SITE_MISMATCH', tl_clean_hostname, details, snapshot_date):
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
                # Extract clean hostnames for display
                tl_clean_hostname = extract_clean_hostname(tl_host.hostname, tl_normalized)
                ninja_clean_hostname = extract_clean_hostname(ninja_host.hostname, tl_normalized)
                
                details = {
                    'hostname_base': tl_normalized,
                    'tl_hostname': tl_clean_hostname,
                    'ninja_hostname': ninja_clean_hostname,
                    'ninja_billing_status': ninja_host.billing_status.code if ninja_host.billing_status else None,
                    'tl_site': tl_host.site.name if tl_host.site else None,
                    'ninja_site': ninja_host.site.name if ninja_host.site else None,
                    'tl_org_name': tl_host.organization_name,
                    'ninja_org_name': ninja_host.organization_name,
                    'note': 'Device marked as spare in Ninja - consider if ThreatLocker cleanup needed'
                }
                
                if insert_exception(session, 'SPARE_MISMATCH', tl_clean_hostname, details, snapshot_date):
                    exceptions_inserted += 1
    
    return exceptions_inserted


def check_display_name_mismatch(session: Session, vendor_ids: Dict[str, int], snapshot_date: date) -> int:
    """
    Check for devices that exist in both Ninja and ThreatLocker with the same hostname 
    but different display names.
    
    SPECIAL CASE EXCLUSION: Devices where Ninja display_name is empty/blank AND 
    ThreatLocker display_name matches the hostname are NOT flagged as mismatches.
    This is because ThreatLocker's default behavior is to use hostname as display_name
    when no custom display name is set.
    
    Example: chi-veeam01
    - Ninja: display_name="", hostname="CHI-VEEAM01" 
    - ThreatLocker: display_name="CHI-VEEAM01", hostname="CHI-VEEAM01"
    - Result: NOT flagged as mismatch (special case)
    
    Args:
        session: Database session
        vendor_ids: Mapping of vendor names to IDs
        snapshot_date: Date to check
        
    Returns:
        int: Number of display name mismatch exceptions inserted
    """
    from sqlalchemy import text
    
    exceptions_inserted = 0
    
    # Get vendor IDs
    ninja_id = vendor_ids.get('Ninja')
    tl_id = vendor_ids.get('ThreatLocker')
    
    if not ninja_id or not tl_id:
        print("Warning: Missing vendor IDs for display name mismatch check")
        return 0
    
    # Query to find devices with matching hostnames but different display names
    # SPECIAL CASE: Exclude cases where Ninja display_name is empty/blank AND 
    # ThreatLocker display_name matches the hostname (default behavior)
    query = text("""
        WITH matched_devices AS (
            SELECT 
                LOWER(LEFT(SPLIT_PART(SPLIT_PART(tl.hostname,'|',1),'.',1),15)) as clean_tl_hostname,
                LOWER(LEFT(SPLIT_PART(ninja.hostname,'.',1),15)) as clean_ninja_hostname,
                tl.hostname as tl_hostname,
                ninja.hostname as ninja_hostname,
                tl.display_name as tl_display_name,
                ninja.display_name as ninja_display_name,
                tl.organization_name as tl_org_name,
                ninja.organization_name as ninja_org_name
            FROM device_snapshot tl
            JOIN device_snapshot ninja ON (
                LOWER(LEFT(SPLIT_PART(SPLIT_PART(tl.hostname,'|',1),'.',1),15)) = 
                LOWER(LEFT(SPLIT_PART(ninja.hostname,'.',1),15))
                AND ninja.vendor_id = :ninja_id
                AND ninja.snapshot_date = :snapshot_date
            )
            WHERE tl.vendor_id = :tl_id
            AND tl.snapshot_date = :snapshot_date
            AND tl.display_name IS NOT NULL
            AND ninja.display_name IS NOT NULL
            AND tl.display_name != ninja.display_name
            AND LOWER(TRIM(tl.display_name)) != LOWER(TRIM(ninja.display_name))
            -- SPECIAL CASE EXCLUSION: Don't flag when Ninja display_name is empty/blank 
            -- AND ThreatLocker display_name matches hostname (default behavior)
            AND NOT (
                (TRIM(COALESCE(ninja.display_name, '')) = '' OR ninja.display_name IS NULL)
                AND LOWER(TRIM(tl.display_name)) = LOWER(TRIM(tl.hostname))
            )
        )
        SELECT 
            clean_tl_hostname,
            tl_hostname,
            ninja_hostname,
            tl_display_name,
            ninja_display_name,
            tl_org_name,
            ninja_org_name
        FROM matched_devices
        ORDER BY clean_tl_hostname
    """)
    
    results = session.execute(query, {
        'ninja_id': ninja_id,
        'tl_id': tl_id,
        'snapshot_date': snapshot_date
    }).fetchall()
    
    for row in results:
        clean_hostname, tl_hostname, ninja_hostname, tl_display_name, ninja_display_name, tl_org_name, ninja_org_name = row
        
        # Create exception details
        details = {
            'tl_hostname': tl_hostname,
            'ninja_hostname': ninja_hostname,
            'tl_display_name': tl_display_name,
            'ninja_display_name': ninja_display_name,
            'tl_org_name': tl_org_name,
            'ninja_org_name': ninja_org_name,
            'hostname_base': clean_hostname,
            'note': 'Device exists in both systems with same hostname but different display names - consider standardizing display names'
        }
        
        # Insert exception
        exception = Exceptions(
            date_found=snapshot_date,
            type='DISPLAY_NAME_MISMATCH',
            hostname=clean_hostname,
            details=details,
            resolved=False
        )
        
        session.add(exception)
        exceptions_inserted += 1
    
    if exceptions_inserted > 0:
        session.commit()
        print(f"DISPLAY_NAME_MISMATCH: Inserted {exceptions_inserted} exceptions for {snapshot_date}")
    
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
    
    # Validate data quality first
    print("Validating data quality...")
    data_quality_issues = validate_data_quality(session, vendor_ids, snapshot_date)
    
    if data_quality_issues['ThreatLocker'] > 0 or data_quality_issues['Ninja'] > 0:
        print(f"Data quality issues found: {data_quality_issues}")
        print("Consider re-running data collection to fix field mapping issues")
    
    # Clear today's exceptions for idempotency
    clear_todays_exceptions(session, snapshot_date)
    
    # Run all checks
    results = {}
    
    results['MISSING_NINJA'] = check_missing_ninja(session, vendor_ids, snapshot_date)
    results['DUPLICATE_TL'] = check_duplicate_tl(session, vendor_ids, snapshot_date)
    results['SITE_MISMATCH'] = check_site_mismatch(session, vendor_ids, snapshot_date)
    results['SPARE_MISMATCH'] = check_spare_mismatch(session, vendor_ids, snapshot_date)
    results['DISPLAY_NAME_MISMATCH'] = check_display_name_mismatch(session, vendor_ids, snapshot_date)
    
    # Add data quality summary to results
    results['DATA_QUALITY_ISSUES'] = data_quality_issues
    
    return results

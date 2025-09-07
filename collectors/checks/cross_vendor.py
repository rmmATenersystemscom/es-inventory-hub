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


def insert_exception(
    session: Session,
    exception_type: str,
    hostname: str,
    details: Dict[str, Any],
    snapshot_date: date
) -> bool:
    """
    Insert an exception record if it doesn't already exist.
    
    Args:
        session: Database session
        exception_type: Type of exception (MISSING_NINJA, DUPLICATE_TL, etc.)
        hostname: Hostname for the exception
        details: JSON details about the exception
        snapshot_date: Date of the snapshot
        
    Returns:
        bool: True if exception was inserted, False if it already existed
    """
    # Check if exception already exists for this date, type, and hostname
    existing = session.query(Exceptions).filter(
        and_(
            Exceptions.date_found == snapshot_date,
            Exceptions.type == exception_type,
            Exceptions.hostname == hostname
        )
    ).first()
    
    if existing:
        return False
    
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
    Check for ThreatLocker hosts that have no matching Ninja host.
    
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
    
    # Create set of Ninja hostname_base values for fast lookup
    ninja_hostname_bases = set()
    for ninja_host in ninja_hosts:
        if ninja_host.hostname:
            ninja_hostname_bases.add(to_base(ninja_host.hostname))
    
    exceptions_inserted = 0
    
    # Check each ThreatLocker host
    for tl_host in tl_hosts:
        if not tl_host.hostname:
            continue
            
        tl_hostname_base = to_base(tl_host.hostname)
        
        # If no matching Ninja host found
        if tl_hostname_base not in ninja_hostname_bases:
            details = {
                'tl_hostname': tl_host.hostname,
                'tl_hostname_base': tl_hostname_base,
                'tl_site_name': tl_host.site.name if tl_host.site else None,
                'tl_org_name': tl_host.raw.get('rootOrganization') if isinstance(tl_host.raw, dict) else None
            }
            
            if insert_exception(session, 'MISSING_NINJA', tl_host.hostname, details, snapshot_date):
                exceptions_inserted += 1
    
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
    duplicates = session.query(
        func.lower(func.split_part(DeviceSnapshot.hostname, '.', 1)).label('hostname_base'),
        func.count().label('count')
    ).filter(
        and_(
            DeviceSnapshot.snapshot_date == snapshot_date,
            DeviceSnapshot.vendor_id == vendor_ids['ThreatLocker'],
            DeviceSnapshot.hostname.isnot(None)
        )
    ).group_by(
        func.lower(func.split_part(DeviceSnapshot.hostname, '.', 1))
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
                func.lower(func.split_part(DeviceSnapshot.hostname, '.', 1)) == hostname_base
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
    
    # Create mapping of hostname_base to Ninja host
    ninja_by_base = {}
    for ninja_host in ninja_hosts:
        if ninja_host.hostname:
            hostname_base = to_base(ninja_host.hostname)
            ninja_by_base[hostname_base] = ninja_host
    
    exceptions_inserted = 0
    
    # Check each ThreatLocker host
    for tl_host in tl_hosts:
        if not tl_host.hostname:
            continue
            
        tl_hostname_base = to_base(tl_host.hostname)
        
        # If matching Ninja host found
        if tl_hostname_base in ninja_by_base:
            ninja_host = ninja_by_base[tl_hostname_base]
            
            # Get site names
            tl_site = tl_host.site.name if tl_host.site else None
            ninja_site = ninja_host.site.name if ninja_host.site else None
            
            # Check for site mismatch
            if tl_site != ninja_site:
                details = {
                    'hostname_base': tl_hostname_base,
                    'tl_hostname': tl_host.hostname,
                    'ninja_hostname': ninja_host.hostname,
                    'tl_site': tl_site,
                    'ninja_site': ninja_site,
                    'tl_org': tl_host.raw.get('rootOrganization') if isinstance(tl_host.raw, dict) else None,
                    'ninja_org': ninja_host.raw.get('organization') if isinstance(ninja_host.raw, dict) else None
                }
                
                if insert_exception(session, 'SITE_MISMATCH', tl_host.hostname, details, snapshot_date):
                    exceptions_inserted += 1
    
    return exceptions_inserted


def check_spare_mismatch(session: Session, vendor_ids: Dict[str, int], snapshot_date: date) -> int:
    """
    Check for spare mismatch: ThreatLocker present but Ninja marks as spare.
    
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
    
    # Create mapping of hostname_base to Ninja host
    ninja_by_base = {}
    for ninja_host in ninja_hosts:
        if ninja_host.hostname:
            hostname_base = to_base(ninja_host.hostname)
            ninja_by_base[hostname_base] = ninja_host
    
    exceptions_inserted = 0
    
    # Check each ThreatLocker host
    for tl_host in tl_hosts:
        if not tl_host.hostname:
            continue
            
        tl_hostname_base = to_base(tl_host.hostname)
        
        # If matching Ninja host found
        if tl_hostname_base in ninja_by_base:
            ninja_host = ninja_by_base[tl_hostname_base]
            
            # Check if Ninja marks this as spare
            is_ninja_spare = False
            if ninja_host.billing_status and ninja_host.billing_status.code == 'spare':
                is_ninja_spare = True
            
            # If Ninja marks as spare but ThreatLocker has it as active
            if is_ninja_spare:
                details = {
                    'hostname_base': tl_hostname_base,
                    'tl_hostname': tl_host.hostname,
                    'ninja_hostname': ninja_host.hostname,
                    'ninja_billing_status': ninja_host.billing_status.code if ninja_host.billing_status else None,
                    'tl_site': tl_host.site.name if tl_host.site else None,
                    'ninja_site': ninja_host.site.name if ninja_host.site else None
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
    
    # Run all checks
    results = {}
    
    results['MISSING_NINJA'] = check_missing_ninja(session, vendor_ids, snapshot_date)
    results['DUPLICATE_TL'] = check_duplicate_tl(session, vendor_ids, snapshot_date)
    results['SITE_MISMATCH'] = check_site_mismatch(session, vendor_ids, snapshot_date)
    results['SPARE_MISMATCH'] = check_spare_mismatch(session, vendor_ids, snapshot_date)
    
    return results

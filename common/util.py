"""Utility functions for es-inventory-hub."""

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy import func
from storage.schema import DeviceSnapshot


def sha256_json(obj: Any) -> str:
    """
    Generate a deterministic SHA256 hash of a JSON-serializable object.
    
    Args:
        obj: Any JSON-serializable object
        
    Returns:
        str: Hexadecimal SHA256 hash string
    """
    # Use separators and sort_keys for deterministic JSON
    json_str = json.dumps(obj, separators=(',', ':'), sort_keys=True)
    return hashlib.sha256(json_str.encode('utf-8')).hexdigest()


def utcnow() -> datetime:
    """
    Get current UTC time with timezone awareness.
    
    Returns:
        datetime: Current UTC time with timezone info
    """
    return datetime.now(timezone.utc)


def upsert_device_identity(
    session: Session, 
    vendor_id: int, 
    vendor_device_key: str, 
    first_seen_date: datetime
) -> int:
    """
    Upsert a device identity record.
    
    Args:
        session: SQLAlchemy session
        vendor_id: ID of the vendor
        vendor_device_key: Vendor-specific device key
        first_seen_date: Date when device was first seen
        
    Returns:
        int: Device identity ID
    """
    from storage.schema import DeviceIdentity
    
    # Convert datetime to date if needed
    if isinstance(first_seen_date, datetime):
        first_seen_date = first_seen_date.date()
    
    # Query for existing device identity
    device_identity = session.query(DeviceIdentity).filter_by(
        vendor_id=vendor_id,
        vendor_device_key=vendor_device_key
    ).first()
    
    if device_identity:
        # Update last_seen_date if this date is newer
        if first_seen_date > device_identity.last_seen_date:
            device_identity.last_seen_date = first_seen_date
        return device_identity.id
    else:
        # Create new device identity record
        device_identity = DeviceIdentity(
            vendor_id=vendor_id,
            vendor_device_key=vendor_device_key,
            first_seen_date=first_seen_date,
            last_seen_date=first_seen_date
        )
        session.add(device_identity)
        session.flush()  # Get the ID
        return device_identity.id


def insert_snapshot(
    session: Session,
    snapshot_date: datetime,
    vendor_id: int,
    device_identity_id: int,
    normalized: dict
) -> None:
    """
    Upsert a device snapshot record using PostgreSQL ON CONFLICT.
    
    Args:
        session: SQLAlchemy session
        snapshot_date: Date of the snapshot
        vendor_id: ID of the vendor
        device_identity_id: ID of the device identity
        normalized: Normalized device data
    """
    from storage.schema import Site, DeviceType, BillingStatus
    
    # Convert datetime to date if needed
    if isinstance(snapshot_date, datetime):
        snapshot_date = snapshot_date.date()
    
    # Look up foreign key IDs
    site_id = None
    if normalized.get('site_name'):
        # First try to find by name
        site = session.query(Site).filter_by(
            vendor_id=vendor_id,
            name=normalized['site_name']
        ).first()
        
        # If not found, create a new site with the site name as both key and name
        if not site:
            site = Site(
                vendor_id=vendor_id,
                vendor_site_key=normalized['site_name'],
                name=normalized['site_name']
            )
            session.add(site)
            session.flush()  # Get the ID
        
        site_id = site.id
    
    device_type_id = None
    if normalized.get('device_type'):
        device_type = session.query(DeviceType).filter_by(
            code=normalized['device_type']
        ).first()
        if device_type:
            device_type_id = device_type.id
    
    billing_status_id = None
    if normalized.get('billing_status'):
        billing_status = session.query(BillingStatus).filter_by(
            code=normalized['billing_status']
        ).first()
        if billing_status:
            billing_status_id = billing_status.id
    
    # Prepare data for upsert with current schema fields
    values = {
        'snapshot_date': snapshot_date,
        'vendor_id': vendor_id,
        'device_identity_id': device_identity_id,
        'site_id': site_id,
        'device_type_id': device_type_id,
        'billing_status_id': billing_status_id,
        'hostname': normalized.get('hostname'),
        'os_name': normalized.get('os_name'),
        'created_at': utcnow(),
        
        # Core Device Information
        'organization_name': normalized.get('organization_name'),
        'display_name': normalized.get('display_name'),
        'device_status': normalized.get('device_status'),
        
        # Timestamps
        'last_online': normalized.get('last_online'),
        'agent_install_timestamp': normalized.get('agent_install_timestamp'),
        
        # ThreatLocker-specific fields
        'organization_id': normalized.get('organization_id'),
        'computer_group': normalized.get('computer_group'),
        'security_mode': normalized.get('security_mode'),
        'deny_count_1d': normalized.get('deny_count_1d'),
        'deny_count_3d': normalized.get('deny_count_3d'),
        'deny_count_7d': normalized.get('deny_count_7d'),
        'install_date': normalized.get('install_date'),
        'is_locked_out': normalized.get('is_locked_out'),
        'is_isolated': normalized.get('is_isolated'),
        'agent_version': normalized.get('agent_version'),
        'has_checked_in': normalized.get('has_checked_in'),
        
        # TPM and SecureBoot fields (Ninja-specific)
        'has_tpm': normalized.get('has_tpm'),
        'tpm_enabled': normalized.get('tpm_enabled'),
        'tpm_version': normalized.get('tpm_version'),
        'secure_boot_available': normalized.get('secure_boot_available'),
        'secure_boot_enabled': normalized.get('secure_boot_enabled'),
    }
    
    # Perform PostgreSQL upsert
    stmt = pg_insert(DeviceSnapshot.__table__).values(values)
    
    # Define update values for conflicts (exclude the unique key fields)
    update_values = {
        'site_id': stmt.excluded.site_id,
        'device_type_id': stmt.excluded.device_type_id,
        'billing_status_id': stmt.excluded.billing_status_id,
        'hostname': stmt.excluded.hostname,
        'os_name': stmt.excluded.os_name,
        'created_at': func.now(),
        
        # Core Device Information
        'organization_name': stmt.excluded.organization_name,
        'display_name': stmt.excluded.display_name,
        'device_status': stmt.excluded.device_status,
        
        # Timestamps
        'last_online': stmt.excluded.last_online,
        'agent_install_timestamp': stmt.excluded.agent_install_timestamp,
        
        # ThreatLocker-specific fields
        'organization_id': stmt.excluded.organization_id,
        'computer_group': stmt.excluded.computer_group,
        'security_mode': stmt.excluded.security_mode,
        'deny_count_1d': stmt.excluded.deny_count_1d,
        'deny_count_3d': stmt.excluded.deny_count_3d,
        'deny_count_7d': stmt.excluded.deny_count_7d,
        'install_date': stmt.excluded.install_date,
        'is_locked_out': stmt.excluded.is_locked_out,
        'is_isolated': stmt.excluded.is_isolated,
        'agent_version': stmt.excluded.agent_version,
        'has_checked_in': stmt.excluded.has_checked_in,
        
        # TPM and SecureBoot fields (Ninja-specific)
        'has_tpm': stmt.excluded.has_tpm,
        'tpm_enabled': stmt.excluded.tpm_enabled,
        'tpm_version': stmt.excluded.tpm_version,
        'secure_boot_available': stmt.excluded.secure_boot_available,
        'secure_boot_enabled': stmt.excluded.secure_boot_enabled,
    }
    
    # Add ON CONFLICT clause for the unique constraint
    stmt = stmt.on_conflict_do_update(
        constraint='uq_device_snapshot_date_vendor_device',
        set_=update_values
    )
    
    # Execute the upsert
    session.execute(stmt)
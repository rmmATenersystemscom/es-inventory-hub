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
    
    # Calculate content hash
    content_hash = sha256_json(normalized)
    
    # Prepare data for upsert
    values = {
        'snapshot_date': snapshot_date,
        'vendor_id': vendor_id,
        'device_identity_id': device_identity_id,
        'site_id': site_id,
        'device_type_id': device_type_id,
        'billing_status_id': billing_status_id,
        'hostname': normalized.get('hostname'),
        'serial_number': normalized.get('serial_number'),
        'os_name': normalized.get('os_name'),
        'tpm_status': normalized.get('tpm_status'),
        'raw': normalized.get('raw'),
        'attrs': None,  # Could be populated with additional attributes
        'content_hash': content_hash,
        'created_at': utcnow()
    }
    
    # Perform PostgreSQL upsert
    stmt = pg_insert(DeviceSnapshot.__table__).values(values)
    
    # Define update values for conflicts (exclude the unique key fields)
    update_values = {
        'site_id': stmt.excluded.site_id,
        'device_type_id': stmt.excluded.device_type_id,
        'billing_status_id': stmt.excluded.billing_status_id,
        'hostname': stmt.excluded.hostname,
        'serial_number': stmt.excluded.serial_number,
        'os_name': stmt.excluded.os_name,
        'tpm_status': stmt.excluded.tpm_status,
        'raw': stmt.excluded.raw,
        'attrs': stmt.excluded.attrs,
        'content_hash': stmt.excluded.content_hash,
        'created_at': func.now()
    }
    
    # Add ON CONFLICT clause for the unique constraint
    stmt = stmt.on_conflict_do_update(
        constraint='uq_device_snapshot_date_vendor_device',
        set_=update_values
    )
    
    # Execute the upsert
    session.execute(stmt)
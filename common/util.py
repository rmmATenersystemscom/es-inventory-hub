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
    
    # Prepare data for upsert with all new fields
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
        'created_at': utcnow(),
        
        # Core Device Information
        'organization_name': normalized.get('organization_name'),
        'location_name': normalized.get('location_name'),
        'system_name': normalized.get('system_name'),
        'display_name': normalized.get('display_name'),
        'device_status': normalized.get('device_status'),
        'last_logged_in_user': normalized.get('last_logged_in_user'),
        
        # OS Information
        'os_release_id': normalized.get('os_release_id'),
        'os_build': normalized.get('os_build'),
        'os_architecture': normalized.get('os_architecture'),
        'os_manufacturer': normalized.get('os_manufacturer'),
        'device_timezone': normalized.get('device_timezone'),
        
        # Network Information
        'ip_addresses': normalized.get('ip_addresses'),
        'ipv4_addresses': normalized.get('ipv4_addresses'),
        'ipv6_addresses': normalized.get('ipv6_addresses'),
        'mac_addresses': normalized.get('mac_addresses'),
        'public_ip': normalized.get('public_ip'),
        
        # Hardware Information
        'system_manufacturer': normalized.get('system_manufacturer'),
        'system_model': normalized.get('system_model'),
        'cpu_model': normalized.get('cpu_model'),
        'cpu_cores': normalized.get('cpu_cores'),
        'cpu_threads': normalized.get('cpu_threads'),
        'cpu_speed_mhz': normalized.get('cpu_speed_mhz'),
        'memory_gib': normalized.get('memory_gib'),
        'memory_bytes': normalized.get('memory_bytes'),
        'volumes': normalized.get('volumes'),
        'bios_serial': normalized.get('bios_serial'),
        
        # Timestamps
        'last_online': normalized.get('last_online'),
        'last_update': normalized.get('last_update'),
        'last_boot_time': normalized.get('last_boot_time'),
        'agent_install_timestamp': normalized.get('agent_install_timestamp'),
        
        # Security Information
        'has_tpm': normalized.get('has_tpm'),
        'tpm_enabled': normalized.get('tpm_enabled'),
        'tpm_version': normalized.get('tpm_version'),
        'secure_boot_available': normalized.get('secure_boot_available'),
        'secure_boot_enabled': normalized.get('secure_boot_enabled'),
        
        # Monitoring and Health
        'health_state': normalized.get('health_state'),
        'antivirus_status': normalized.get('antivirus_status'),
        
        # Metadata
        'tags': normalized.get('tags'),
        'notes': normalized.get('notes'),
        'approval_status': normalized.get('approval_status'),
        'node_class': normalized.get('node_class'),
        'system_domain': normalized.get('system_domain'),
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
        'created_at': func.now(),
        
        # Core Device Information
        'organization_name': stmt.excluded.organization_name,
        'location_name': stmt.excluded.location_name,
        'system_name': stmt.excluded.system_name,
        'display_name': stmt.excluded.display_name,
        'device_status': stmt.excluded.device_status,
        'last_logged_in_user': stmt.excluded.last_logged_in_user,
        
        # OS Information
        'os_release_id': stmt.excluded.os_release_id,
        'os_build': stmt.excluded.os_build,
        'os_architecture': stmt.excluded.os_architecture,
        'os_manufacturer': stmt.excluded.os_manufacturer,
        'device_timezone': stmt.excluded.device_timezone,
        
        # Network Information
        'ip_addresses': stmt.excluded.ip_addresses,
        'ipv4_addresses': stmt.excluded.ipv4_addresses,
        'ipv6_addresses': stmt.excluded.ipv6_addresses,
        'mac_addresses': stmt.excluded.mac_addresses,
        'public_ip': stmt.excluded.public_ip,
        
        # Hardware Information
        'system_manufacturer': stmt.excluded.system_manufacturer,
        'system_model': stmt.excluded.system_model,
        'cpu_model': stmt.excluded.cpu_model,
        'cpu_cores': stmt.excluded.cpu_cores,
        'cpu_threads': stmt.excluded.cpu_threads,
        'cpu_speed_mhz': stmt.excluded.cpu_speed_mhz,
        'memory_gib': stmt.excluded.memory_gib,
        'memory_bytes': stmt.excluded.memory_bytes,
        'volumes': stmt.excluded.volumes,
        'bios_serial': stmt.excluded.bios_serial,
        
        # Timestamps
        'last_online': stmt.excluded.last_online,
        'last_update': stmt.excluded.last_update,
        'last_boot_time': stmt.excluded.last_boot_time,
        'agent_install_timestamp': stmt.excluded.agent_install_timestamp,
        
        # Security Information
        'has_tpm': stmt.excluded.has_tpm,
        'tpm_enabled': stmt.excluded.tpm_enabled,
        'tpm_version': stmt.excluded.tpm_version,
        'secure_boot_available': stmt.excluded.secure_boot_available,
        'secure_boot_enabled': stmt.excluded.secure_boot_enabled,
        
        # Monitoring and Health
        'health_state': stmt.excluded.health_state,
        'antivirus_status': stmt.excluded.antivirus_status,
        
        # Metadata
        'tags': stmt.excluded.tags,
        'notes': stmt.excluded.notes,
        'approval_status': stmt.excluded.approval_status,
        'node_class': stmt.excluded.node_class,
        'system_domain': stmt.excluded.system_domain,
    }
    
    # Add ON CONFLICT clause for the unique constraint
    stmt = stmt.on_conflict_do_update(
        constraint='uq_device_snapshot_date_vendor_device',
        set_=update_values
    )
    
    # Execute the upsert
    session.execute(stmt)
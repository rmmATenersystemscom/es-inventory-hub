"""Utility functions for es-inventory-hub."""

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session


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
        
    TODO: Implement device identity upsert logic
    """
    # TODO: Implement the following logic:
    # 1. Query for existing device identity by vendor_id and vendor_device_key
    # 2. If found, update last_seen_date if necessary and return ID
    # 3. If not found, create new device identity record
    # 4. Return the device identity ID
    raise NotImplementedError("upsert_device_identity logic to be implemented")


def insert_snapshot(
    session: Session,
    snapshot_date: datetime,
    vendor_id: int,
    device_identity_id: int,
    normalized: dict
) -> int:
    """
    Insert a device snapshot record.
    
    Args:
        session: SQLAlchemy session
        snapshot_date: Date of the snapshot
        vendor_id: ID of the vendor
        device_identity_id: ID of the device identity
        normalized: Normalized device data
        
    Returns:
        int: Snapshot ID
        
    TODO: Implement snapshot insertion logic
    """
    # TODO: Implement the following logic:
    # 1. Create DeviceSnapshot record with provided data
    # 2. Map normalized data to appropriate fields (site, device_type, billing_status, etc.)
    # 3. Calculate content_hash using sha256_json
    # 4. Handle any foreign key lookups (site_id, device_type_id, billing_status_id)
    # 5. Insert the record and return the ID
    raise NotImplementedError("insert_snapshot logic to be implemented")

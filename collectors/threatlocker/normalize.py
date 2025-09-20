"""ThreatLocker device data normalization and mapping."""

import json
from datetime import date
from typing import Dict, Any


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


def map_device_type_name(tl: Dict[str, Any]) -> str:
    """
    Map ThreatLocker device data to device type name.
    
    Args:
        tl: Raw ThreatLocker device data
        
    Returns:
        str: Device type name: 'server', 'workstation', or 'unknown'
    """
    # Get category/type information
    category_type = (tl.get("category") or tl.get("type") or "").lower()
    
    # Check for server indicators
    if "server" in category_type:
        return "server"
    
    # Check for workstation indicators
    workstation_indicators = ["workstation", "desktop", "laptop", "notebook", "pc"]
    if any(x in category_type for x in workstation_indicators):
        return "workstation"
    
    # Default to unknown
    return "unknown"


def build_row(tl: Dict[str, Any], ids: Dict[str, Dict[str, int]]) -> Dict[str, Any]:
    """
    Build a normalized row from ThreatLocker device data using pre-resolved IDs.
    
    Args:
        tl: Raw device dictionary from ThreatLocker API
        ids: Dictionary containing pre-resolved ID mappings
        
    Returns:
        dict: Normalized device data ready for DB insert
    """
    # Extract hostname (hostname field is required - no fallbacks)
    # Note: computerName contains pipe symbols like "CHI-4YHKJL3 | Keith Oneil" so it's not used
    hostname = (tl.get("hostname") or "").strip()
    
    # Validate that hostname is present - this is critical for device matching
    if not hostname:
        computer_id = tl.get("computerId", "Unknown")
        raise ValueError(f"ThreatLocker device {computer_id} is missing hostname field - cannot continue without hostname for device matching")
    
    # Get base hostname
    hostname_base = to_base(hostname)
    
    # Extract site and organization names
    site_name = tl.get("organization") or tl.get("siteName") or ""
    org_name = tl.get("rootOrganization") or tl.get("tenantName") or ""
    
    # Map device type and get ID
    device_type_name = map_device_type_name(tl)
    device_type_id = ids["device_type"][device_type_name]
    
    # Get vendor ID (billing status not applicable for ThreatLocker)
    vendor_id = ids["vendor"]["threatlocker"]
    
    # Set snapshot date to today
    snapshot_date = date.today()
    
    # Prepare raw data as JSON string
    raw = json.dumps(tl, ensure_ascii=False)
    
    return {
        'hostname': hostname,
        'hostname_base': hostname_base,
        'site_name': site_name,
        'org_name': org_name,
        'device_type_id': device_type_id,
        'vendor_id': vendor_id,
        'snapshot_date': snapshot_date,
        'raw': raw
    }

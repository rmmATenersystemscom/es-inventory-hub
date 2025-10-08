"""ThreatLocker device data normalization and mapping."""

from typing import Dict, Any, Optional


def normalize_threatlocker_device(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a raw ThreatLocker device record into standardized format.
    
    Args:
        raw: Raw device dictionary from ThreatLocker API
        
    Returns:
        dict: Normalized device data ready for DB insert
    """
    # Get hostname (hostname field is required - no fallbacks)
    # Note: computerName contains user-friendly names like "CHI-4YHKJL3 | Keith Oneil" and is used for display_name
    hostname = raw.get('hostname', '')
    
    # Get vendor device key (use computerId as unique identifier for ThreatLocker)
    # This ensures the same physical device always gets the same vendor_device_key
    # computerId is ThreatLocker's internal unique identifier (UUID format)
    vendor_device_key = raw.get('computerId', '')
    
    # Validate that computerId is present - this is critical for unique device identification
    if not vendor_device_key or not vendor_device_key.strip():
        raise ValueError(f"ThreatLocker device is missing computerId field - cannot continue without computerId for unique device identification")
    
    # Validate that hostname is present - this is critical for device matching
    if not hostname or not hostname.strip():
        computer_id = raw.get('computerId', 'Unknown')
        raise ValueError(f"ThreatLocker device {computer_id} is missing hostname field - cannot continue without hostname for device matching")
    
    # Get OS name
    os_name = raw.get('operatingSystem', '') or raw.get('osName', '')
    
    # Get organization name
    organization_name = raw.get('organizationName', '') or raw.get('organization', '')
    
    # Get display name (use computerName field which contains user-friendly name)
    display_name = raw.get('computerName', '') or hostname
    
    # Get device status
    device_status = _get_device_status(raw)
    
    # Get last online timestamp
    last_online = _parse_timestamp(raw.get('lastCheckin'))
    
    # Get agent install timestamp
    agent_install_timestamp = _parse_timestamp(raw.get('installDate'))
    
    # ThreatLocker-specific fields
    organization_id = str(raw.get('organizationId', '')) if raw.get('organizationId') else None
    computer_group = raw.get('group', '') or None
    security_mode = raw.get('mode', '') or None
    deny_count_1d = _safe_int(raw.get('denyCountOneDay'))
    deny_count_3d = _safe_int(raw.get('denyCountThreeDays'))
    deny_count_7d = _safe_int(raw.get('denyCountSevenDays'))
    install_date = _parse_timestamp(raw.get('installDate'))
    is_locked_out = _safe_bool(raw.get('isLockedOut'))
    is_isolated = _safe_bool(raw.get('isIsolated'))
    agent_version = raw.get('threatLockerVersion', '') or None
    has_checked_in = _safe_bool(raw.get('hasAtLeastOneCheckin'))
    
    return {
        'vendor_device_key': vendor_device_key,
        'hostname': hostname,
        'os_name': os_name,
        'organization_name': organization_name,
        'display_name': display_name,
        'device_status': device_status,
        'last_online': last_online,
        'agent_install_timestamp': agent_install_timestamp,
        'organization_id': organization_id,
        'computer_group': computer_group,
        'security_mode': security_mode,
        'deny_count_1d': deny_count_1d,
        'deny_count_3d': deny_count_3d,
        'deny_count_7d': deny_count_7d,
        'install_date': install_date,
        'is_locked_out': is_locked_out,
        'is_isolated': is_isolated,
        'agent_version': agent_version,
        'has_checked_in': has_checked_in
    }


def _get_device_status(device: Dict[str, Any]) -> str:
    """Extract device status from ThreatLocker data."""
    # Check for various status fields
    status = device.get('status', '') or device.get('deviceStatus', '')
    
    if status:
        status_lower = status.lower()
        if any(active_status in status_lower for active_status in ['active', 'online', 'connected']):
            return 'active'
        elif any(inactive_status in status_lower for inactive_status in ['inactive', 'offline', 'disconnected']):
            return 'inactive'
        else:
            return status
    
    # Default to active if no status found
    return 'active'


def _parse_timestamp(timestamp_str: Any) -> Optional[str]:
    """Parse timestamp string to ISO format."""
    if not timestamp_str:
        return None
    
    try:
        from datetime import datetime
        import dateutil.parser
        
        # Try to parse the timestamp
        if isinstance(timestamp_str, str):
            dt = dateutil.parser.parse(timestamp_str)
            return dt.isoformat()
        elif isinstance(timestamp_str, (int, float)):
            # Handle Unix timestamp
            dt = datetime.fromtimestamp(timestamp_str)
            return dt.isoformat()
        else:
            return None
    except Exception:
        return None


def _safe_int(value: Any) -> Optional[int]:
    """Safely convert value to integer."""
    if value is None or value == '':
        return None
    
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _safe_bool(value: Any) -> Optional[bool]:
    """Safely convert value to boolean."""
    if value is None or value == '':
        return None
    
    if isinstance(value, bool):
        return value
    
    if isinstance(value, str):
        value_lower = value.lower()
        if value_lower in ['true', 'yes', '1', 'enabled', 'active']:
            return True
        elif value_lower in ['false', 'no', '0', 'disabled', 'inactive']:
            return False
    
    if isinstance(value, (int, float)):
        return bool(value)
    
    return None

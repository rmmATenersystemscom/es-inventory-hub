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
    # Get vendor device key (use computer ID as unique identifier)
    vendor_device_key = str(raw.get('computerId', ''))
    
    # Get hostname (try multiple fields)
    hostname = (
        raw.get('computerName') or 
        raw.get('hostname') or 
        raw.get('name') or 
        ''
    )
    
    # Get serial number (ThreatLocker doesn't provide serial numbers in the API)
    serial_number = ''
    
    # Get OS name
    os_name = raw.get('operatingSystem', '') or raw.get('osName', '')
    
    # Get TPM status
    tpm_status = _get_tpm_status(raw)
    
    # Resolve site information
    site_name = _get_site_name(raw)
    
    # Classify device type
    device_type = _classify_device_type(raw)
    
    # Prepare raw data for JSONB storage (ensure it's JSON serializable)
    raw_jsonb = _prepare_raw_for_jsonb(raw)
    
    return {
        'vendor_device_key': vendor_device_key,
        'hostname': hostname,
        'serial_number': serial_number,
        'os_name': os_name,
        'tpm_status': tpm_status,
        'site_name': site_name,
        'device_type': device_type,
        'raw': raw_jsonb
    }


def _get_tpm_status(device: Dict[str, Any]) -> str:
    """Extract TPM status from device data."""
    # Check for TPM-related fields in ThreatLocker data
    tpm_status = device.get('tpmStatus', '')
    
    if not tpm_status:
        # Try alternative field names
        tpm_status = device.get('tpm', '') or device.get('trustedPlatformModule', '')
    
    # Normalize TPM status values
    if tpm_status:
        tpm_lower = tpm_status.lower()
        if any(status in tpm_lower for status in ['enabled', 'active', 'true', 'yes']):
            return 'enabled'
        elif any(status in tpm_lower for status in ['disabled', 'inactive', 'false', 'no']):
            return 'disabled'
        else:
            return tpm_status
    
    return ''


def _get_site_name(device: Dict[str, Any]) -> Optional[str]:
    """Extract site name from device data."""
    # Check for organization/location fields
    site_name = device.get('group') or device.get('organizationName') or device.get('locationName')
    
    if site_name:
        return site_name
    
    # Check if organization is embedded (object)
    if isinstance(device.get("organization"), dict):
        site_name = device.get("organization", {}).get("name")
        if site_name:
            return site_name
    
    # If we still don't have a site name, return None (will be resolved later)
    return None


def _classify_device_type(device: Dict[str, Any]) -> str:
    """
    Classify device as server, workstation, or unknown.
    
    Based on the logic from the dashboard project and ThreatLocker-specific fields.
    """
    try:
        # Get device information
        computer_name = (device.get('computerName') or '').lower()
        os_name = (device.get('operatingSystem') or '').lower()
        group = (device.get('group') or '').lower()
        
        # Check for virtualization devices first
        if 'vm' in group or 'virtual' in group:
            return 'unknown'  # VM Guests are not classified as servers/workstations
        
        # Define specific device types
        server_types = [
            'windows server', 'linux server', 'virtual server',
            'server', 'srv', 'dc', 'domain controller', 'sql', 'web', 'app'
        ]
        
        workstation_types = [
            'windows desktop', 'windows laptop', 'macos desktop', 'macos laptop',
            'desktop', 'laptop', 'workstation', 'pc', 'windows 10', 'windows 11'
        ]
        
        # Check OS information first (most reliable)
        if any(server_os in os_name for server_os in ['windows server', 'linux server', 'server']):
            return 'server'
        elif any(workstation_os in os_name for workstation_os in ['windows', 'macos', 'linux desktop']):
            return 'workstation'
        
        # Check group field
        if any(server_type in group for server_type in server_types):
            return 'server'
        elif any(workstation_type in group for workstation_type in workstation_types):
            return 'workstation'
        
        # Check computer name patterns as fallback
        if any(server_pattern in computer_name for server_pattern in ['server', 'srv', 'dc', 'sql', 'web', 'app']):
            return 'server'
        elif any(workstation_pattern in computer_name for workstation_pattern in ['pc', 'laptop', 'desktop', 'workstation', 'ws']):
            return 'workstation'
        
        # If we can't classify it, return 'unknown'
        return 'unknown'
        
    except Exception:
        return 'unknown'  # Safe default


def _prepare_raw_for_jsonb(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prepare raw device data for JSONB storage.
    
    Ensures the data is JSON serializable by handling any problematic types.
    """
    import json
    
    try:
        # Try to serialize and deserialize to ensure it's JSON-safe
        json_str = json.dumps(raw, default=str)  # Convert non-serializable to string
        return json.loads(json_str)
    except Exception:
        # If there are still issues, return a minimal safe version
        return {
            'computerId': raw.get('computerId'),
            'computerName': raw.get('computerName'),
            'operatingSystem': raw.get('operatingSystem'),
            'organizationName': raw.get('organizationName'),
            'error': 'Failed to serialize raw data'
        }

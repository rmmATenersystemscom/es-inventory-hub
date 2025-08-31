"""Ninja device data normalization and mapping."""

from typing import Dict, Any, Optional


def normalize_ninja_device(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a raw Ninja device record into standardized format.
    
    Args:
        raw: Raw device dictionary from Ninja API
        
    Returns:
        dict: Normalized device data ready for DB insert
    """
    # Extract nested objects
    os_obj = raw.get("os") or {}
    sys_obj = raw.get("system") or {}
    
    # Get vendor device key (use device ID as unique identifier)
    vendor_device_key = str(raw.get('id', ''))
    
    # Get hostname (try multiple fields)
    hostname = (
        raw.get('systemName') or 
        raw.get('hostname') or 
        raw.get('deviceName') or 
        raw.get('dnsName') or 
        ''
    )
    
    # Get serial number
    serial_number = sys_obj.get('serialNumber', '') or sys_obj.get('biosSerialNumber', '')
    
    # Get OS name
    os_name = os_obj.get('name', '')
    
    # Get TPM status (not typically available in Ninja API, set to empty)
    tmp_status = ''
    
    # Resolve site information
    site_name = _get_site_name(raw)
    
    # Classify device type
    device_type = _classify_device_type(raw)
    
    # Classify billing status using the spare rule
    billing_status = _classify_billing_status(raw)
    
    # Prepare raw data for JSONB storage (ensure it's JSON serializable)
    raw_jsonb = _prepare_raw_for_jsonb(raw)
    
    return {
        'vendor_device_key': vendor_device_key,
        'hostname': hostname,
        'serial_number': serial_number,
        'os_name': os_name,
        'tmp_status': tmp_status,
        'site_name': site_name,
        'device_type': device_type,
        'billing_status': billing_status,
        'raw': raw_jsonb
    }


def _get_site_name(device: Dict[str, Any]) -> Optional[str]:
    """Extract site name from device data."""
    # Check if location is embedded (object)
    if isinstance(device.get("location"), dict):
        site_name = device.get("location", {}).get("name")
        if site_name:
            return site_name
    
    # If not found, check locationId reference (would need location lookup)
    # For now, we'll use what's available in the device record
    
    # Fallback to locationName field
    site_name = device.get("locationName")
    if site_name:
        return site_name
    
    # If we still don't have a site name, return None (will be resolved later)
    return None


def _classify_device_type(device: Dict[str, Any]) -> str:
    """
    Classify device as server, workstation, or unknown.
    
    Based on the logic from the dashboard project.
    """
    try:
        # Get device information
        platform = device.get('platform', '').lower()
        os_obj = device.get('os') or {}
        os_name = os_obj.get('name', '').lower()
        os_version = os_obj.get('version', '').lower()
        system_name = (
            device.get('hostname') or 
            device.get('deviceName') or 
            device.get('systemName', '')
        ).lower()
        
        # Check for virtualization devices first
        device_type = device.get('deviceType', '').lower()
        node_class = device.get('nodeClass', '').lower()
        
        if device_type == 'vmguest' or node_class == 'vmware_vm_guest':
            return 'unknown'  # VM Guests are not classified as servers/workstations
        elif device_type == 'vmhost':
            return 'server'  # VM Hosts are servers
        
        # Define specific device types
        server_types = [
            'windows server', 'linux server', 'virtual server',
            'server', 'srv', 'dc', 'domain controller'
        ]
        
        workstation_types = [
            'windows desktop', 'windows laptop', 'macos desktop', 'macos laptop',
            'desktop', 'laptop', 'workstation', 'pc'
        ]
        
        # Check platform field first (most reliable)
        if any(server_type in platform for server_type in server_types):
            return 'server'
        elif any(workstation_type in platform for workstation_type in workstation_types):
            return 'workstation'
        
        # Check OS information
        if any(server_os in os_name for server_os in ['windows server', 'linux server', 'server']):
            return 'server'
        elif any(workstation_os in os_name for workstation_os in ['windows', 'macos', 'linux desktop']):
            return 'workstation'
        
        # Check system name patterns as fallback
        if any(server_pattern in system_name for server_pattern in ['server', 'srv', 'dc', 'sql', 'web', 'app']):
            return 'server'
        elif any(workstation_pattern in system_name for workstation_pattern in ['pc', 'laptop', 'desktop', 'workstation', 'ws']):
            return 'workstation'
        
        # If we can't classify it, return 'unknown'
        return 'unknown'
        
    except Exception:
        return 'unknown'  # Safe default


def _classify_billing_status(device: Dict[str, Any]) -> str:
    """
    Classify device billing status using the spare rule.
    
    A device is "spare" if:
    - Display Name contains "spare" (case-insensitive), OR
    - Location contains "spare" (case-insensitive), OR  
    - Node Class == VMWARE_VM_GUEST
    
    Otherwise, it's "billable".
    """
    try:
        # Check Node Class first
        node_class = device.get('nodeClass', '').upper()
        if node_class == 'VMWARE_VM_GUEST':
            return 'spare'
        
        # Get Display Name and Location for spare checking
        display_name = device.get('displayName', '').lower()
        
        # Get location name (try multiple sources)
        location_name = ''
        if isinstance(device.get('location'), dict):
            location_name = device.get('location', {}).get('name', '').lower()
        else:
            location_name = (device.get('location') or '').lower()
        
        if not location_name:
            location_name = device.get('locationName', '').lower()
        
        # Check for spare indicators
        if 'spare' in display_name or 'spare' in location_name:
            return 'spare'
        
        # Default to billable
        return 'billable'
        
    except Exception:
        return 'billable'  # Safe default


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
            'id': raw.get('id'),
            'systemName': raw.get('systemName'),
            'displayName': raw.get('displayName'),
            'organizationId': raw.get('organizationId'),
            'error': 'Failed to serialize raw data'
        }

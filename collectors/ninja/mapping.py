"""Ninja device data normalization and mapping."""

from typing import Dict, Any, Optional


def _resolve_organization_name(raw: Dict[str, Any], org_map: Dict[str, str] = None) -> str:
    """Resolve organization name from device data."""
    if not org_map:
        return raw.get('organizationName', '')
    
    # Try to get organization ID from device
    org_id = raw.get('organizationId')
    if org_id and org_id in org_map:
        return org_map[org_id]
    
    # Fallback to organizationName field
    return raw.get('organizationName', '')


def _resolve_location_name(raw: Dict[str, Any], loc_map: Dict[str, str] = None, fallback: str = '') -> str:
    """Resolve location name from device data."""
    if not loc_map:
        return fallback
    
    # Try to get location ID from device
    loc_id = raw.get('locationId')
    if loc_id and loc_id in loc_map:
        return loc_map[loc_id]
    
    # Try location object
    location_obj = raw.get('location')
    if isinstance(location_obj, dict):
        loc_id = location_obj.get('id')
        if loc_id and loc_id in loc_map:
            return loc_map[loc_id]
        return location_obj.get('name', fallback)
    
    # Fallback to provided fallback value
    return fallback


def normalize_ninja_device(raw: Dict[str, Any], ninja_api=None, org_map: Dict[str, str] = None, loc_map: Dict[str, str] = None) -> Dict[str, Any]:
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
    network_obj = raw.get("network") or {}
    hardware_obj = raw.get("hardware") or {}
    
    # Get hostname (use dnsName for full hostname - systemName is truncated to 15 chars)
    # Note: displayName should never be used as anchor for device matching
    # dnsName provides the full DNS hostname, avoiding truncation issues and collisions
    hostname = raw.get('dnsName', '') or raw.get('systemName', '')

    # Get vendor device key (use hostname as unique identifier)
    # This ensures the same physical device always gets the same vendor_device_key
    vendor_device_key = hostname

    # Validate that hostname is present - this is critical for device matching
    if not hostname or not hostname.strip():
        device_id = raw.get('id', 'Unknown')
        raise ValueError(f"Ninja device {device_id} is missing dnsName/systemName field - cannot continue without hostname for device matching")
    
    # Get serial number
    serial_number = sys_obj.get('serialNumber', '') or sys_obj.get('biosSerialNumber', '')
    
    # Get OS name
    os_name = os_obj.get('name', '')
    
    # Resolve site information
    site_name = _get_site_name(raw)
    
    # Classify device type
    device_type = _classify_device_type(raw)
    
    # Classify billing status using the spare rule
    billing_status = _classify_billing_status(raw)
    
    # Extract all the new fields to match the Ninja modal
    return {
        'vendor_device_key': vendor_device_key,
        'hostname': hostname,
        'serial_number': serial_number,
        'os_name': os_name,
        'site_name': site_name,
        'device_type': device_type,
        'billing_status': billing_status,
        
        # Core Device Information (using correct API paths from documentation)
        'organization_name': _resolve_organization_name(raw, org_map),
        'location_name': _resolve_location_name(raw, loc_map, site_name),
        'system_name': raw.get('systemName', ''),
        'display_name': raw.get('displayName', ''),
        'device_status': raw.get('status', ''),
        'last_logged_in_user': raw.get('user', ''),  # Correct API path from documentation
        
        # NinjaRMM Modal Fields (for Windows 11 24H2 API)
        'device_type_name': device_type,
        'billable_status_name': billing_status,
        
        # OS Information
        'os_release_id': os_obj.get('releaseId', ''),
        'os_build': os_obj.get('buildNumber', '') or os_obj.get('build', ''),
        'os_architecture': os_obj.get('architecture', ''),
        'os_manufacturer': os_obj.get('manufacturer', ''),
        'device_timezone': raw.get('timezone', ''),
        
        # Network Information
        'ip_addresses': _format_network_addresses(network_obj.get('addresses', [])),
        'ipv4_addresses': _format_ipv4_addresses(network_obj.get('addresses', [])),
        'ipv6_addresses': _format_ipv6_addresses(network_obj.get('addresses', [])),
        'mac_addresses': _format_mac_addresses(network_obj.get('macAddresses', [])),
        'public_ip': raw.get('publicIp', ''),
        
        # Hardware Information - using correct API paths from documentation
        'system_manufacturer': sys_obj.get('manufacturer', ''),
        'system_model': sys_obj.get('model', ''),
        'cpu_model': _get_cpu_model(raw.get('processors', [])),
        'cpu_cores': _get_cpu_cores(raw.get('processors', [])),
        'cpu_threads': _get_cpu_threads(raw.get('processors', [])),
        'cpu_speed_mhz': _get_cpu_speed(raw.get('processors', [])),
        'memory_gib': _convert_memory_to_gib(raw.get('memory', {}).get('capacity', 0)),
        'memory_bytes': raw.get('memory', {}).get('capacity', 0),
        'volumes': _format_volumes(raw.get('volumes', [])),
        'bios_serial': sys_obj.get('biosSerialNumber', ''),
        
        # Timestamps
        'last_online': _parse_timestamp(raw.get('lastContact')),
        'last_update': _parse_timestamp(raw.get('lastUpdate')),
        'last_boot_time': _parse_timestamp(raw.get('lastBootTime')),
        'agent_install_timestamp': _parse_timestamp(raw.get('agentInstallTimestamp')),
        
        # Security Information - fetch from custom fields
        **_get_security_fields(raw, ninja_api),
        
        # Monitoring and Health
        'health_state': raw.get('healthState', ''),
        'antivirus_status': _format_antivirus_status(raw.get('antivirus', {})),
        
        # Metadata
        'tags': _format_tags(raw.get('tags', [])),
        'notes': raw.get('notes', ''),
        'approval_status': raw.get('approvalStatus', ''),
        'node_class': raw.get('nodeClass', ''),
        'system_domain': raw.get('domain', ''),
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
    Classify device billing status using simplified spare rules.
    
    A device is "spare" if:
    - Device Type is 'vmguest' (VM guests are not billable), OR
    - Display Name contains "spare" (case-insensitive), OR
    - Location contains "spare" (case-insensitive)
    
    Note: VM Hosts (VMWARE_VM_HOST, HYPERV_VMM_GUEST) remain billable as they are physical infrastructure.
    
    Otherwise, it's "billable".
    """
    try:
        # Rule 1: Check device type for VM guests (only guests are non-billable)
        device_type = device.get('deviceType', '').lower()
        if device_type == 'vmguest':
            return 'spare'  # VM guests are not billable
        
        # Rule 2: Check for "spare" in name or location
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


def _format_network_addresses(addresses: list) -> str:
    """Format network addresses as comma-separated string."""
    if not addresses:
        return ''
    return ', '.join(str(addr) for addr in addresses if addr)


def _format_ipv4_addresses(addresses: list) -> str:
    """Format IPv4 addresses as comma-separated string."""
    if not addresses:
        return ''
    import ipaddress
    ipv4_addrs = []
    for addr in addresses:
        try:
            ip = ipaddress.ip_address(str(addr))
            if isinstance(ip, ipaddress.IPv4Address):
                ipv4_addrs.append(str(ip))
        except ValueError:
            continue
    return ', '.join(ipv4_addrs)


def _format_ipv6_addresses(addresses: list) -> str:
    """Format IPv6 addresses as comma-separated string."""
    if not addresses:
        return ''
    import ipaddress
    ipv6_addrs = []
    for addr in addresses:
        try:
            ip = ipaddress.ip_address(str(addr))
            if isinstance(ip, ipaddress.IPv6Address):
                ipv6_addrs.append(str(ip))
        except ValueError:
            continue
    return ', '.join(ipv6_addrs)


def _format_mac_addresses(mac_addresses: list) -> str:
    """Format MAC addresses as comma-separated string."""
    if not mac_addresses:
        return ''
    return ', '.join(str(mac) for mac in mac_addresses if mac)


def _convert_memory_to_gib(memory_bytes: Optional[int]) -> Optional[float]:
    """Convert memory bytes to GiB."""
    if memory_bytes is None:
        return None
    try:
        return round(memory_bytes / (1024 ** 3), 2)
    except (TypeError, ValueError):
        return None


def _format_volumes(volumes: list) -> str:
    """Format volume information as comma-separated string with capacity."""
    if not volumes:
        return ''
    volume_info = []
    for vol in volumes:
        if isinstance(vol, dict):
            name = vol.get('name', '')
            capacity = vol.get('capacity', 0)
            if name and capacity:
                # Convert bytes to GB
                capacity_gb = capacity / (1024**3)
                volume_info.append(f"{name}: {capacity_gb:.1f}GB")
            elif name:
                volume_info.append(name)
        else:
            volume_info.append(str(vol))
    return ', '.join(volume_info)


def _parse_timestamp(timestamp: Any) -> Optional[str]:
    """Parse timestamp to ISO format string."""
    if not timestamp:
        return None
    try:
        if isinstance(timestamp, (int, float)):
            # Unix timestamp
            from datetime import datetime
            return datetime.fromtimestamp(timestamp).isoformat()
        elif isinstance(timestamp, str):
            # Already a string, return as-is
            return timestamp
        else:
            # Try to convert to string
            return str(timestamp)
    except (ValueError, TypeError, OSError):
        return None


def _format_antivirus_status(antivirus: dict) -> str:
    """Format antivirus status information."""
    if not antivirus:
        return ''
    
    products = antivirus.get('products', [])
    state = antivirus.get('state', '')
    
    if products and state:
        return f"{', '.join(products)} - {state}"
    elif products:
        return ', '.join(products)
    elif state:
        return state
    else:
        return ''


def _format_tags(tags: list) -> str:
    """Format tags as comma-separated string."""
    if not tags:
        return ''
    return ', '.join(str(tag) for tag in tags if tag)


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


def _get_security_fields(raw: Dict[str, Any], ninja_api=None) -> Dict[str, Any]:
    """Get security-related fields from custom fields API."""
    security_fields = {
        'has_tpm': None,
        'tpm_enabled': None,
        'tpm_version': '',
        'secure_boot_available': None,
        'secure_boot_enabled': None,
    }
    
    # If no API client provided, return defaults
    if not ninja_api:
        return security_fields
    
    try:
        device_id = raw.get('id')
        if not device_id:
            return security_fields
        
        # Fetch custom fields for this device
        custom_fields = ninja_api.get_device_custom_fields(device_id)
        
        # Map custom field values to our security fields
        # Custom field names are lowercase in Ninja API
        security_fields['has_tpm'] = _interpret_boolean_field(custom_fields.get('hastpm'))
        security_fields['tpm_enabled'] = _interpret_boolean_field(custom_fields.get('tpmenabled'))
        security_fields['tpm_version'] = _interpret_tpm_version(custom_fields.get('tpmversion', ''))
        security_fields['secure_boot_available'] = _interpret_boolean_field(custom_fields.get('securebootavailable'))
        security_fields['secure_boot_enabled'] = _interpret_boolean_field(custom_fields.get('securebootenabled'))
        
    except Exception as e:
        # If there's an error fetching custom fields, return defaults
        pass
    
    return security_fields


def _interpret_boolean_field(value: str) -> Optional[bool]:
    """Interpret boolean custom field values according to new specifications."""
    if not value or value == '':
        return None  # Not checked (PowerShell script not run)
    
    value_lower = value.lower()
    if value_lower == 'true':
        return True
    elif value_lower == 'false':
        return False
    else:
        return None  # Unknown value


def _interpret_tpm_version(value: str) -> str:
    """Interpret TPM version custom field values according to new specifications."""
    if not value or value == '':
        return ''  # Not checked (PowerShell script not run)
    
    if value == '0.0':
        return 'No TPM'
    else:
        return value  # Return version string as-is (e.g., "2.0, 0, 1.38")


def _get_cpu_model(processors: list) -> str:
    """Extract CPU model from processors array."""
    if not processors or len(processors) == 0:
        return ''
    
    # Get the first processor (primary CPU)
    first_processor = processors[0]
    return first_processor.get('name', '')


def _get_cpu_cores(processors: list) -> Optional[int]:
    """Extract CPU cores from processors array."""
    if not processors or len(processors) == 0:
        return None
    
    # Get the first processor (primary CPU)
    first_processor = processors[0]
    return first_processor.get('numCores')


def _get_cpu_threads(processors: list) -> Optional[int]:
    """Extract CPU threads from processors array."""
    if not processors or len(processors) == 0:
        return None
    
    # Get the first processor (primary CPU)
    first_processor = processors[0]
    return first_processor.get('numLogicalCores')


def _get_cpu_speed(processors: list) -> Optional[int]:
    """Extract CPU speed from processors array."""
    if not processors or len(processors) == 0:
        return None
    
    # Get the first processor (primary CPU)
    first_processor = processors[0]
    return first_processor.get('maxClockSpeed')

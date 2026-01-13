"""NinjaRMM API client for enhanced device data collection."""

import requests
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

from collectors.ninja.token_manager import get_access_token, get_credentials


class NinjaRMMAPI:
    """Enhanced NinjaRMM API client for device data collection with organization/location mapping."""

    def __init__(self):
        """
        Initialize the API client.

        ALL credentials (base_url, client_id, client_secret, refresh_token) are read
        from the JSON file: /opt/es-inventory-hub/data/ninja_refresh_token.json

        This is necessary because DbAI has separate Ninja client credentials from
        Dashboard AI, and the shared secrets file contains Dashboard AI's credentials.
        """
        # Get credentials from JSON file (NOT from environment)
        creds = get_credentials()
        if not creds:
            raise ValueError(
                "Missing NinjaRMM credentials. Check "
                "/opt/es-inventory-hub/data/ninja_refresh_token.json"
            )

        self.base_url = creds['base_url']

        # Initialize session
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    def _get_access_token(self) -> str:
        """Get OAuth access token using refresh token flow with automatic rotation handling."""
        # Token manager reads ALL credentials from JSON file and handles rotation
        access_token = get_access_token()

        if not access_token:
            raise Exception(
                'Failed to obtain NinjaRMM access token. '
                'Check /opt/es-inventory-hub/data/ninja_refresh_token.json'
            )

        return access_token
    
    def _get_api_headers(self) -> Dict[str, str]:
        """Get headers with authentication token."""
        access_token = self._get_access_token()
        return {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
    
    def get_organizations(self) -> List[Dict[str, Any]]:
        """Get all organizations from NinjaRMM API."""
        try:
            orgs_url = f"{self.base_url}/api/v2/organizations"
            headers = self._get_api_headers()
            
            response = self.session.get(orgs_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            print(f"Error fetching organizations: {e}")
            return []
    
    def get_locations(self) -> List[Dict[str, Any]]:
        """Get all locations from NinjaRMM API."""
        try:
            locs_url = f"{self.base_url}/api/v2/locations"
            headers = self._get_api_headers()
            
            response = self.session.get(locs_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            print(f"Error fetching locations: {e}")
            return []
    
    def get_devices(self) -> List[Dict[str, Any]]:
        """Get all devices from NinjaRMM API."""
        try:
            devices_url = f"{self.base_url}/api/v2/devices-detailed"
            headers = self._get_api_headers()
            
            response = self.session.get(devices_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            print(f"Error fetching devices: {e}")
            return []
    
    def _classify_device_type(self, device: Dict[str, Any]) -> str:
        """Classify device as server, workstation, or unknown based on documentation."""
        try:
            # Get device information
            platform = device.get('platform', '').lower()
            os_obj = device.get('os') or {}
            os_name = os_obj.get('name', '').lower()
            device_type = device.get('deviceType', '').lower()
            node_class = device.get('nodeClass', '').lower()
            
            # Check for virtualization devices first
            if device_type == 'vmguest' or node_class == 'vmware_vm_guest':
                return 'virtualization'  # VM Guests are not billable
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
            system_name = (
                device.get('hostname') or 
                device.get('deviceName') or 
                device.get('systemName', '')
            ).lower()
            
            if any(server_name in system_name for server_name in ['server', 'srv', 'dc']):
                return 'server'
            elif any(workstation_name in system_name for workstation_name in ['desktop', 'laptop', 'pc', 'workstation']):
                return 'workstation'
            
            return 'unknown'  # Safe default
            
        except Exception:
            return 'unknown'  # Safe default
    
    def _classify_billable_status(self, device: Dict[str, Any]) -> str:
        """Classify device billing status using simplified spare rules."""
        try:
            # Rule 1: Check device type for VM guests (only guests are non-billable)
            device_type = device.get('deviceType', '').lower()
            if device_type == 'vmguest':
                return 'virtualization'  # VM guests are not billable
            
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

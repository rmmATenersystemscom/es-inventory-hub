"""NinjaRMM API client for enhanced device data collection."""

import os
import requests
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from shared secrets and project .env
load_dotenv('/opt/shared-secrets/api-secrets.env')
load_dotenv('/opt/es-inventory-hub/.env')


class NinjaRMMAPI:
    """Enhanced NinjaRMM API client for device data collection with organization/location mapping."""
    
    def __init__(self):
        """Initialize the API client with credentials from environment."""
        self.base_url = os.getenv('NINJA_BASE_URL', 'https://app.ninjarmm.com').rstrip('/')
        self.client_id = os.getenv('NINJA_CLIENT_ID')
        self.client_secret = os.getenv('NINJA_CLIENT_SECRET')
        self.refresh_token = os.getenv('NINJA_REFRESH_TOKEN')
        
        # Check for required credentials
        if not self.client_id or not self.client_secret:
            raise ValueError(
                "Missing required NinjaRMM environment variables: "
                "NINJA_CLIENT_ID and NINJA_CLIENT_SECRET"
            )
        
        # Initialize session
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
    
    def _get_access_token(self) -> str:
        """Get OAuth access token using refresh token flow."""
        token_url = f"{self.base_url}/oauth/token"
        
        if self.refresh_token:
            # Use refresh token flow (preferred)
            data = {
                'grant_type': 'refresh_token',
                'refresh_token': self.refresh_token,
                'client_id': self.client_id,
                'client_secret': self.client_secret,
            }
        else:
            # Fallback to client credentials flow
            data = {
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'scope': 'monitoring'
            }
        
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        
        response = self.session.post(token_url, data=data, headers=headers, timeout=30)
        response.raise_for_status()
        
        token_data = response.json()
        access_token = token_data.get('access_token')
        
        if not access_token:
            raise Exception('Failed to obtain NinjaRMM access token')
        
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

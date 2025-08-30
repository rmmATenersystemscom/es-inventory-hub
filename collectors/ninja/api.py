#!/usr/bin/env python3
"""
NinjaRMM API Client for ES Inventory Hub Collectors
Refactored from existing dashboard API integration
"""

import requests
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from common.logging import get_logger

logger = get_logger(__name__)


class NinjaRMMAPI:
    """NinjaRMM API client for device data collection - refactored from existing dashboard"""
    
    def __init__(self):
        """Initialize the API client with credentials from environment"""
        # Use the same environment variable pattern as existing dashboard
        self.base_url = os.getenv('NINJA_BASE_URL', 'https://app.ninjarmm.com').rstrip('/')
        self.client_id = os.getenv('NINJA_CLIENT_ID')
        self.client_secret = os.getenv('NINJA_CLIENT_SECRET')
        self.refresh_token = os.getenv('NINJA_REFRESH_TOKEN')
        
        # Check for required credentials
        if not self.client_id or not self.client_secret:
            raise ValueError("Missing required NinjaRMM environment variables: NINJA_CLIENT_ID, NINJA_CLIENT_SECRET")
        
        # Initialize session with retry logic
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set base headers (same as existing dashboard)
        self.session.headers.update({"Accept": "application/json"})
    
    def _get_access_token(self):
        """Get OAuth access token using refresh token flow (reused from existing dashboard)"""
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
        
        try:
            response = self.session.post(token_url, data=data, headers=headers, timeout=30)
            response.raise_for_status()
            
            token_data = response.json()
            access_token = token_data.get('access_token')
            
            if not access_token:
                raise Exception('Failed to obtain NinjaRMM access token')
            
            logger.debug("Successfully obtained NinjaRMM access token")
            return access_token
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get access token: {e}")
            raise
    
    def _get_api_headers(self):
        """Get headers with authentication token (reused from existing dashboard)"""
        access_token = self._get_access_token()
        return {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
    
    def _to_gib(self, val_bytes):
        """Convert bytes to GiB (reused from existing dashboard)"""
        try:
            return round(float(val_bytes) / (1024**3), 2)
        except Exception:
            return None
    
    def _join_list(self, xs):
        """Join list items with commas (reused from existing dashboard)"""
        return ", ".join([str(x) for x in xs]) if xs else ""
    
    def _format_iso(self, dt_val):
        """Format datetime values (reused from existing dashboard)"""
        if not dt_val:
            return ""
        
        # Handle Unix timestamps (float/int)
        if isinstance(dt_val, (int, float)):
            try:
                return datetime.fromtimestamp(dt_val).strftime('%Y-%m-%d %H:%M:%S')
            except:
                return str(dt_val)
        
        return str(dt_val)
    
    def _get_location_name(self, device, location_map):
        """Get location name from device data (reused from existing dashboard)"""
        loc_name = ""
        
        # Check if location is embedded (object)
        if isinstance(device.get("location"), dict):
            loc_name = device.get("location", {}).get("name") or ""
        
        # If not found, check locationId reference
        if not loc_name:
            loc_id = device.get("locationId")
            if loc_id:
                loc_obj = location_map.get(loc_id)
                if isinstance(loc_obj, dict):
                    loc_name = loc_obj.get("name") or ""
        
        # Fallback to locationName field
        if not loc_name:
            loc_name = device.get("locationName") or ""
        
        return loc_name
    
    def _get_location_address(self, device, location_map):
        """Get location address from device data (reused from existing dashboard)"""
        loc_address = ""
        
        # Check if location is embedded (object)
        if isinstance(device.get("location"), dict):
            loc_address = device.get("location", {}).get("address") or ""
        
        # If not found, check locationId reference
        if not loc_address:
            loc_id = device.get("locationId")
            if loc_id:
                loc_obj = location_map.get(loc_id)
                if isinstance(loc_obj, dict):
                    loc_address = loc_obj.get("address") or ""
        
        return loc_address
    
    def _get_location_description(self, device, location_map):
        """Get location description from device data (reused from existing dashboard)"""
        loc_description = ""
        
        # Check if location is embedded (object)
        if isinstance(device.get("location"), dict):
            loc_description = device.get("location", {}).get("description") or ""
        
        # If not found, check locationId reference
        if not loc_description:
            loc_id = device.get("locationId")
            if loc_id:
                loc_obj = location_map.get(loc_id)
                if isinstance(loc_obj, dict):
                    loc_description = loc_obj.get("description") or ""
        
        return loc_description
    
    def _format_volumes(self, volumes):
        """Format volumes like: C: 476.9 GB (Free: 120.3 GB, Used: 356.6 GB) (reused from existing dashboard)"""
        vol_parts = []
        for v in volumes:
            name = v.get("name") or "Volume"
            cap = self._to_gib(v.get("capacity") or 0)
            free = self._to_gib(v.get("freeSpace") or 0)
            used = None if cap is None or free is None else round(cap - free, 2)
            
            if cap is None:
                vol_parts.append(f'{name}')
            else:
                if free is None:
                    vol_parts.append(f'{name}: {cap} GB')
                else:
                    vol_parts.append(f'{name}: {cap} GB (Free: {free} GB, Used: {used} GB)')
        
        return "; ".join(vol_parts)
    
    def _classify_device_type(self, device):
        """Classify device type (reused from existing dashboard)"""
        # This is a simplified version - the dashboard has more complex logic
        device_type = device.get("deviceType", "").lower()
        if "server" in device_type or "vmhost" in device_type:
            return "Server"
        elif "workstation" in device_type or "desktop" in device_type:
            return "Workstation"
        else:
            return "Other"
    
    def _classify_billable_status(self, device):
        """Classify billable status (reused from existing dashboard)"""
        # This is a simplified version - the dashboard has more complex logic
        return "Billable"  # Default assumption
    
    def get_organizations(self) -> List[Dict[str, Any]]:
        """Get list of all organizations from NinjaRMM (reused from existing dashboard)"""
        try:
            headers = self._get_api_headers()
            organizations_url = f"{self.base_url}/api/v2/organizations"
            response = self.session.get(organizations_url, headers=headers, timeout=30)
            response.raise_for_status()
            organizations = response.json()
            
            # Process organizations for our format (same as existing dashboard)
            processed_organizations = []
            for org in organizations:
                processed_org = {
                    'id': org.get('id', 'N/A'),
                    'name': org.get('name', 'N/A'),
                    'status': org.get('status', 'N/A'),
                    'address': org.get('address', {}).get('address1', 'N/A'),
                    'city': org.get('address', {}).get('city', 'N/A'),
                    'state': org.get('address', {}).get('state', 'N/A'),
                    'zip': org.get('address', {}).get('zip', 'N/A'),
                    'phone': org.get('phone', 'N/A'),
                    'email': org.get('email', 'N/A')
                }
                processed_organizations.append(processed_org)
            
            logger.info(f"Retrieved {len(processed_organizations)} organizations")
            return processed_organizations
            
        except Exception as e:
            logger.error(f"Failed to get organizations: {e}")
            raise
    
    def get_locations(self) -> Dict[str, Any]:
        """Get list of all locations from NinjaRMM (reused from existing dashboard)"""
        try:
            headers = self._get_api_headers()
            locations_url = f"{self.base_url}/api/v2/locations"
            response = self.session.get(locations_url, headers=headers, timeout=30)
            response.raise_for_status()
            locations = response.json()
            
            # Create a map of location ID to location object (same as existing dashboard)
            location_map = {}
            for loc in locations:
                location_map[loc.get('id')] = loc
            
            logger.info(f"Retrieved {len(location_map)} locations")
            return location_map
            
        except Exception as e:
            logger.error(f"Failed to get locations: {e}")
            return {}
    
    def get_devices(self, organization_id: str) -> List[Dict[str, Any]]:
        """Get devices for a specific organization (reused from existing dashboard with full field coverage)"""
        try:
            headers = self._get_api_headers()
            devices_url = f"{self.base_url}/api/v2/devices-detailed"
            
            # Get all devices with pagination support (same as existing dashboard)
            all_devices = []
            params = {"limit": 250}
            
            while True:
                response = self.session.get(devices_url, headers=headers, params=params, timeout=60)
                response.raise_for_status()
                data = response.json()
                
                # Handle both list and paginated responses (same as existing dashboard)
                if isinstance(data, list):
                    all_devices.extend(data)
                    break
                else:
                    items = data.get("items", [])
                    all_devices.extend(items)
                    
                    # Check for pagination
                    next_link = data.get("next") or data.get("_links", {}).get("next", {}).get("href")
                    if not next_link:
                        break
                    devices_url = next_link
                    params = {}  # next link already contains query parameters
            
            # Get locations for mapping
            location_map = self.get_locations()
            
            # Create organization map
            org_map = {org['id']: org['name'] for org in self.get_organizations()}
            
            # Process and classify devices (same field coverage as existing dashboard)
            processed_devices = []
            for device in all_devices:
                device_type = self._classify_device_type(device)
                billable_status = self._classify_billable_status(device)
                
                # Core/nested helpers (same as existing dashboard)
                os_obj = device.get("os") or {}
                sys_obj = device.get("system") or {}
                mem_obj = device.get("memory") or {}
                procs = device.get("processors") or []
                vols = device.get("volumes") or []
                
                # Get organization and location names
                org_name = org_map.get(device.get("organizationId")) or device.get("organizationName") or ""
                loc_name = self._get_location_name(device, location_map)
                
                # IPs
                ips = device.get("ipAddresses") or []
                ipv4 = [ip for ip in ips if ":" not in ip]
                ipv6 = [ip for ip in ips if ":" in ip]
                
                # MACs
                macs = device.get("macAddresses") or []
                
                # Memory
                mem_capacity_bytes = mem_obj.get("capacity")
                mem_capacity_gib = self._to_gib(mem_capacity_bytes)
                mem_capacity_raw = str(mem_capacity_bytes) if mem_capacity_bytes is not None else ""
                
                # Processor details (first CPU)
                cpu_name = procs[0].get("name") if procs else ""
                cpu_mhz = procs[0].get("maxClockSpeed") if procs else None
                cpu_mhz_str = f"{cpu_mhz}" if cpu_mhz is not None else ""
                
                # Volumes
                volumes_str = self._format_volumes(vols)
                
                # Enhanced device data structure to match Ninja CSV export format (same as existing dashboard)
                processed_device = {
                    # Core identification fields
                    'id': device.get('id', 'N/A'),
                    'systemName': device.get('systemName', 'N/A'),
                    'organizationId': device.get('organizationId', 'N/A'),
                    'organizationName': org_name,
                    'deviceType': device_type,
                    'billableStatus': billable_status,
                    'status': 'Online' if not device.get('offline', True) else 'Offline',
                    
                    # Ninja CSV Export Format Fields (matching existing dashboard)
                    'SystemName': device.get('systemName') or device.get('hostname') or device.get('deviceName') or "",
                    'Display Name': device.get('displayName') or "",
                    'Location Name': loc_name,
                    'Location Address': self._get_location_address(device, location_map),
                    'Location Description': self._get_location_description(device, location_map),
                    'Last LoggedIn User': device.get('lastLoggedInUser') or "",
                    'Memory Capacity (GiB)': mem_capacity_gib if mem_capacity_gib is not None else "",
                    'OS Name': os_obj.get('name', ''),
                    'OS ReleaseID': os_obj.get('releaseId', ''),
                    'OS Build Number': os_obj.get('buildNumber', ''),
                    'OS Build': os_obj.get('buildNumber', ''),  # Add this field for modal compatibility
                    'OS Architecture': os_obj.get('architecture', ''),
                    'OS Manufacturer': os_obj.get('manufacturer', ''),
                    'Type': device.get('type') or device.get('deviceType') or '',
                    'Role': device.get('role', ''),
                    'Policy': device.get('policy', ''),
                    'Last Online': self._format_iso(device.get('lastContact')),
                    'Last Update': self._format_iso(device.get('lastUpdate')),
                    
                    # Additional fields for full coverage
                    'nodeClass': device.get('nodeClass', ''),
                    'platform': device.get('platform', ''),
                    'location': device.get('location', ''),
                    'locationId': device.get('locationId', ''),
                    'hostname': device.get('hostname', ''),
                    'deviceName': device.get('deviceName', ''),
                    
                    # Raw data for full payload storage
                    'raw_data': device
                }
                
                processed_devices.append(processed_device)
            
            logger.info(f"Retrieved {len(processed_devices)} devices for organization {organization_id}")
            return processed_devices
            
        except Exception as e:
            logger.error(f"Failed to get devices for organization {organization_id}: {e}")
            raise
    
    def get_device_details(self, device_id: str) -> Dict[str, Any]:
        """Get detailed information for a specific device (reused from existing dashboard)"""
        try:
            headers = self._get_api_headers()
            device_url = f"{self.base_url}/api/v2/devices/{device_id}"
            response = self.session.get(device_url, headers=headers, timeout=30)
            response.raise_for_status()
            device = response.json()
            
            logger.debug(f"Retrieved details for device {device_id}")
            return device
            
        except Exception as e:
            logger.error(f"Failed to get device details for {device_id}: {e}")
            raise
    
    def test_connection(self) -> bool:
        """Test API connection and authentication"""
        try:
            # Try to get organizations as a connection test
            self.get_organizations()
            logger.info("NinjaRMM API connection test successful")
            return True
        except Exception as e:
            logger.error(f"NinjaRMM API connection test failed: {e}")
            return False

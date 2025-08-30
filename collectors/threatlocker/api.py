#!/usr/bin/env python3
"""
ThreatLocker API Client for ES Inventory Hub Collectors
Refactored from existing dashboard API integration
"""

import requests
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import os

from common.logging import get_logger

logger = get_logger(__name__)


class ThreatLockerAPI:
    """ThreatLocker API client for device data collection - refactored from existing dashboard"""
    
    def __init__(self):
        """Initialize the API client with credentials from environment"""
        # Use the same base URL and authentication pattern as existing dashboard
        self.base_url = "https://portalapi.g.threatlocker.com"
        self.api_key = os.getenv("THREATLOCKER_API_KEY", "")
        self.organization_id = os.getenv("THREATLOCKER_ORGANIZATION_ID", "")
        
        # Check for required credentials
        if not self.api_key:
            raise ValueError("Missing required ThreatLocker environment variable: THREATLOCKER_API_KEY")
        
        # Headers for API requests - using exact format from working dashboard code
        self.headers = {
            "authorization": self.api_key,  # Lowercase, no 'Bearer' prefix
            "content-type": "application/json"  # Lowercase
        }
        
        # Add managedorganizationid header if organization ID is provided
        if self.organization_id:
            self.headers["managedorganizationid"] = self.organization_id
        
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
    
    def _get_headers_with_org(self, organization_id: Optional[str] = None) -> Dict[str, str]:
        """Get headers with optional organization ID override (reused from existing dashboard)"""
        headers = self.headers.copy()
        if organization_id:
            headers["managedorganizationid"] = organization_id
        return headers
    
    def _make_request(self, endpoint: str, method: str = 'GET', data: Optional[Dict] = None, 
                     params: Optional[Dict] = None, organization_id: Optional[str] = None) -> Dict[str, Any]:
        """Make API request with error handling (reused from existing dashboard)"""
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers_with_org(organization_id)
        
        try:
            logger.info(f"Making {method} request to {endpoint}", extra={
                'endpoint': endpoint,
                'method': method,
                'params': params,
                'data': data
            })
            
            if method.upper() == 'POST':
                response = self.session.post(url, headers=headers, json=data, params=params, timeout=30)
            else:
                response = self.session.get(url, headers=headers, params=params, timeout=30)
            
            response.raise_for_status()
            
            response_data = response.json() if response.content else None
            logger.info(f"Request successful", extra={
                'endpoint': endpoint,
                'status_code': response.status_code,
                'response_size': len(response.content)
            })
            
            return response_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}", extra={
                'endpoint': endpoint,
                'method': method,
                'error': str(e)
            })
            raise
    
    def get_organizations(self) -> List[Dict[str, Any]]:
        """Get list of all organizations (reused from existing dashboard)"""
        try:
            url = "/portalApi/Organization/OrganizationGetChildOrganizationsByParameters"
            
            # Use POST request with payload as in existing dashboard
            data = {
                "pageSize": 1000,  # Get all organizations
                "pageNumber": 1,
                "includeProductBundles": False
            }
            
            response = self._make_request(url, method='POST', data=data)
            
            # Process organizations for our format (same as existing dashboard)
            organizations = []
            if response and 'data' in response:
                for org in response['data']:
                    processed_org = {
                        'id': org.get('id'),
                        'name': org.get('name', 'Unknown Organization'),
                        'status': org.get('status'),
                        'address': org.get('address'),
                        'city': org.get('city'),
                        'state': org.get('state'),
                        'zip': org.get('zip'),
                        'phone': org.get('phone'),
                        'email': org.get('email')
                    }
                    organizations.append(processed_org)
            
            logger.info(f"Retrieved {len(organizations)} organizations")
            return organizations
            
        except Exception as e:
            logger.error(f"Failed to get organizations: {e}")
            raise
    
    def get_devices(self, organization_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get devices for a specific organization (reused from existing dashboard with full field coverage)"""
        try:
            url = "/portalApi/Computer/ComputerGetByAllParameters"
            
            # Use POST request with payload as in existing dashboard
            data = {
                "pageSize": 1000,  # Get all devices
                "pageNumber": 1,
                "searchText": "",
                "orderBy": "lastcheckin",
                "childOrganizations": True if not organization_id else False,
                "showLastCheckIn": True
            }
            
            response = self._make_request(url, method='POST', data=data, organization_id=organization_id)
            
            # Process devices for our format (same field coverage as existing dashboard)
            devices = []
            if response and 'data' in response:
                for device in response['data']:
                    # Enhanced device data structure to match ThreatLocker dashboard format
                    processed_device = {
                        # Core identification fields
                        'id': device.get('id'),
                        'computerName': device.get('computerName'),
                        'displayName': device.get('displayName'),
                        'location': device.get('location'),
                        'deviceType': device.get('deviceType'),
                        'operatingSystem': device.get('operatingSystem'),
                        'osVersion': device.get('osVersion'),
                        'lastCheckIn': device.get('lastCheckIn'),
                        'status': device.get('status'),
                        'organizationId': device.get('organizationId'),
                        
                        # Additional fields for full coverage (matching existing dashboard)
                        'computerId': device.get('computerId'),
                        'organizationName': device.get('organizationName'),
                        'lastSeen': device.get('lastSeen'),
                        'ipAddress': device.get('ipAddress'),
                        'macAddress': device.get('macAddress'),
                        'domain': device.get('domain'),
                        'description': device.get('description'),
                        'notes': device.get('notes'),
                        'tags': device.get('tags'),
                        'policies': device.get('policies'),
                        'groups': device.get('groups'),
                        'users': device.get('users'),
                        'applications': device.get('applications'),
                        'storage': device.get('storage'),
                        'memory': device.get('memory'),
                        'processor': device.get('processor'),
                        'network': device.get('network'),
                        'security': device.get('security'),
                        'compliance': device.get('compliance'),
                        'backup': device.get('backup'),
                        'monitoring': device.get('monitoring'),
                        
                        # Raw data for full payload storage
                        'raw_data': device
                    }
                    devices.append(processed_device)
            
            logger.info(f"Retrieved {len(devices)} devices for organization {organization_id or 'all'}")
            return devices
            
        except Exception as e:
            logger.error(f"Failed to get devices for organization {organization_id}: {e}")
            raise
    
    def get_device_details(self, device_id: str, organization_id: Optional[str] = None) -> Dict[str, Any]:
        """Get detailed information for a specific device (reused from existing dashboard)"""
        try:
            url = "/portalApi/Computer/ComputerGetById"
            
            data = {
                "id": device_id
            }
            
            response = self._make_request(url, method='POST', data=data, organization_id=organization_id)
            
            logger.debug(f"Retrieved details for device {device_id}")
            return response
            
        except Exception as e:
            logger.error(f"Failed to get device details for {device_id}: {e}")
            raise
    
    def get_policies(self, organization_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get policies for a specific organization (reused from existing dashboard)"""
        try:
            url = "/portalApi/Policy/PolicyGetAll"
            
            data = {
                "pageSize": 1000,
                "pageNumber": 1
            }
            
            response = self._make_request(url, method='POST', data=data, organization_id=organization_id)
            
            logger.info(f"Retrieved policies for organization {organization_id or 'all'}")
            return response.get('data', []) if response else []
            
        except Exception as e:
            logger.error(f"Failed to get policies for organization {organization_id}: {e}")
            raise
    
    def get_all_computers_with_child_organizations(self) -> List[Dict[str, Any]]:
        """Get all computers from all child organizations (reused from existing dashboard)"""
        try:
            # Use the working endpoint from existing dashboard
            url = "/portalApi/Computer/ComputerGetByAllParameters"
            
            # Use default headers (no organization override)
            headers = self.headers
            
            # Payload with childOrganizations set to True to get all child org computers
            data = {
                "pageSize": 500,
                "pageNumber": 1,
                "searchText": "",
                "orderBy": "lastcheckin",
                "childOrganizations": True,
                "showLastCheckIn": True
            }
            
            response = self.session.post(f"{self.base_url}{url}", headers=headers, json=data, timeout=30)
            response.raise_for_status()
            
            computers = response.json()
            if isinstance(computers, list):
                logger.info(f"Retrieved {len(computers)} computers from all child organizations")
                return computers
            else:
                logger.error(f"Unexpected response format: {type(computers)}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting all computers: {e}")
            raise
    
    def test_connection(self) -> bool:
        """Test API connection and authentication (reused from existing dashboard)"""
        try:
            # Test with the working endpoint from existing dashboard
            url = "/portalApi/Organization/OrganizationGetChildOrganizationsByParameters"
            
            # Use POST request with payload as in existing dashboard
            data = {
                "pageSize": 25,
                "pageNumber": 1,
                "includeProductBundles": False
            }
            
            response = self._make_request(url, method='POST', data=data)
            
            if response:
                logger.info("ThreatLocker API connection test successful")
                return True
            else:
                logger.error("ThreatLocker API connection test failed - no response")
                return False
                
        except Exception as e:
            logger.error(f"ThreatLocker API connection test failed: {e}")
            return False

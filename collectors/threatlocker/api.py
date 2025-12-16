"""ThreatLocker API client for device collection."""

import os
import json
import requests
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from .log import get_logger

# Load environment variables from shared secrets and project .env
load_dotenv('/opt/shared-secrets/api-secrets.env')
load_dotenv('/opt/es-inventory-hub/.env')


def fetch_devices(limit: Optional[int] = None, since: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Fetch devices from ThreatLocker API.
    
    Args:
        limit: Optional limit on total number of devices to fetch
        since: Optional date string to filter devices since
        
    Returns:
        list: List of raw device dictionaries from ThreatLocker API
    """
    try:
        api = ThreatLockerAPI()
        return api.fetch_devices(limit=limit, since=since)
    except Exception as e:
        logger = get_logger(__name__)
        logger.error(f"Error fetching devices from ThreatLocker API: {e}")
        return []


class ThreatLockerAPI:
    """ThreatLocker API client for device data collection."""
    
    def __init__(self):
        """Initialize the API client with credentials from environment."""
        self.logger = get_logger(__name__)
        self.api_key = os.getenv('THREATLOCKER_API_KEY')
        self.base_url = os.getenv('THREATLOCKER_API_BASE_URL')
        self.organization_id = os.getenv('THREATLOCKER_ORGANIZATION_ID')
        
        # Check for required credentials
        if not self.api_key:
            raise ValueError(
                "Missing required ThreatLocker environment variable: THREATLOCKER_API_KEY"
            )
        
        if not self.base_url:
            raise ValueError(
                "Missing required ThreatLocker environment variable: THREATLOCKER_API_BASE_URL"
            )
        
        # Initialize session with headers (matching working dashboard)
        self.session = requests.Session()
        self.session.headers.update({
            "authorization": self.api_key,
            "content-type": "application/json",
            "Accept": "application/json"
        })
        
        # Add managedorganizationid header if organization ID is provided (like working dashboard)
        if self.organization_id:
            self.session.headers["managedorganizationid"] = self.organization_id
    
    def fetch_devices(self, limit: Optional[int] = None, since: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch devices from ThreatLocker API with pagination.
        
        Args:
            limit: Optional limit on total number of devices to fetch
            since: Optional date string to filter devices since
            
        Returns:
            list: List of raw device dictionaries from ThreatLocker API
        """
        all_devices = []
        page_number = 1
        page_size = 500  # Use large page size to minimize API calls
        
        try:
            # Use the working endpoint from dashboard implementation
            url = f"{self.base_url}/portalApi/Computer/ComputerGetByAllParameters"
            
            while True:
                # Payload based on working dashboard implementation
                data = {
                    "pageSize": page_size,
                    "pageNumber": page_number,
                    "searchText": "",
                    "orderBy": "lastcheckin",
                    "childOrganizations": True,  # Get computers from all child organizations (full dataset)
                    "showLastCheckIn": True
                }
                
                # Log request details (DEBUG level)
                self.logger.debug(f"Request URL: {url}")
                
                # Log headers without API key for security
                safe_headers = {k: v for k, v in self.session.headers.items() if k.lower() != 'authorization'}
                safe_headers['authorization'] = '[REDACTED]'
                self.logger.debug(f"Request headers: {safe_headers}")
                self.logger.debug(f"Request payload: {data}")
                
                # Make request
                response = self.session.post(url, json=data, timeout=60)
                
                # Log response details (DEBUG level)
                self.logger.debug(f"Response status code: {response.status_code}")
                self.logger.debug(f"Response text (first 200 chars): {response.text[:200]}")
                
                # Check if response is valid JSON
                try:
                    devices = response.json()
                except json.JSONDecodeError as e:
                    raise ValueError(f"Invalid JSON response from ThreatLocker API: {e}. Response: {response.text[:200]}")
                
                # Check if response is empty
                if not devices:
                    raise ValueError("Empty response from ThreatLocker API")
                
                # Handle both list and paginated responses
                if isinstance(devices, list):
                    device_list = devices
                else:
                    device_list = devices.get("items", [])
                
                # Add devices to our collection
                all_devices.extend(device_list)
                
                # Check if we've reached the limit
                if limit is not None and len(all_devices) >= limit:
                    all_devices = all_devices[:limit]  # Trim to exact limit
                    break
                
                # Check if we've reached the end (less than page_size devices returned)
                if len(device_list) < page_size:
                    break
                
                page_number += 1
            
            # Log total devices returned
            self.logger.info(f"ThreatLocker API: Retrieved {len(all_devices)} devices")
            
            return all_devices
            
        except Exception as e:
            self.logger.error(f"Error fetching devices from ThreatLocker API: {e}")
            raise
    
    def update_computer_name(self, computer_id: str, new_name: str) -> Dict[str, Any]:
        """
        Update a ThreatLocker computer name via API.
        
        Args:
            computer_id: ThreatLocker computer ID (UUID)
            new_name: New computer name to set
            
        Returns:
            dict: API response with success status and details
        """
        try:
            # Use the ComputerUpdateForEdit endpoint
            url = f"{self.base_url}/portalApi/Computer/ComputerUpdateForEdit"
            
            # Prepare the update payload
            data = {
                "computerId": computer_id,
                "computerName": new_name
            }
            
            # Log request details (DEBUG level)
            self.logger.debug(f"Update request URL: {url}")
            self.logger.debug(f"Update request payload: {data}")
            
            # Make the update request
            response = self.session.post(url, json=data, timeout=30)
            
            # Log response details
            self.logger.debug(f"Update response status code: {response.status_code}")
            self.logger.debug(f"Update response text: {response.text}")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    self.logger.info(f"Successfully updated ThreatLocker computer {computer_id} name to: {new_name}")
                    return {
                        'success': True,
                        'computer_id': computer_id,
                        'new_name': new_name,
                        'response': result
                    }
                except ValueError:
                    # Response is not JSON, but status is 200
                    self.logger.info(f"Successfully updated ThreatLocker computer {computer_id} name to: {new_name}")
                    return {
                        'success': True,
                        'computer_id': computer_id,
                        'new_name': new_name,
                        'response': response.text
                    }
            else:
                error_msg = f"Failed to update ThreatLocker computer name. Status: {response.status_code}, Response: {response.text}"
                self.logger.error(error_msg)
                return {
                    'success': False,
                    'computer_id': computer_id,
                    'new_name': new_name,
                    'error': error_msg,
                    'status_code': response.status_code
                }
                
        except Exception as e:
            error_msg = f"Exception updating ThreatLocker computer name: {str(e)}"
            self.logger.error(error_msg)
            return {
                'success': False,
                'computer_id': computer_id,
                'new_name': new_name,
                'error': error_msg
            }
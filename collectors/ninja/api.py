"""Ninja API client for device collection."""

import os
import requests
from typing import Generator, Dict, Any, Optional

from collectors.ninja.token_manager import get_access_token as get_rotated_access_token


class NinjaAPI:
    """NinjaRMM API client for device data collection."""

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
        """Get OAuth access token using refresh token flow with automatic rotation handling."""
        # Use token manager for automatic refresh token rotation
        access_token = get_rotated_access_token(
            self.base_url,
            self.client_id,
            self.client_secret,
            self.refresh_token  # Fallback to env variable
        )

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
    
    def list_devices(self, limit: Optional[int] = None) -> Generator[Dict[str, Any], None, None]:
        """
        Generator that pages through Ninja's device API.
        
        Args:
            limit: Optional limit on total number of devices to fetch
            
        Yields:
            dict: Raw device data from Ninja API
        """
        headers = self._get_api_headers()
        devices_url = f"{self.base_url}/api/v2/devices-detailed"
        
        devices_yielded = 0
        params = {"limit": 250}  # Use max page size for efficiency
        
        while True:
            # If we have a limit and we've reached it, stop
            if limit is not None and devices_yielded >= limit:
                break
            
            response = self.session.get(devices_url, headers=headers, params=params, timeout=60)
            response.raise_for_status()
            data = response.json()
            
            # Handle both list and paginated responses
            if isinstance(data, list):
                devices = data
            else:
                devices = data.get("items", [])
            
            # Yield devices up to the limit
            for device in devices:
                if limit is not None and devices_yielded >= limit:
                    return
                yield device
                devices_yielded += 1
            
            # Check for pagination
            if isinstance(data, list):
                # Non-paginated response, we're done
                break
            
            next_link = data.get("next") or data.get("_links", {}).get("next", {}).get("href")
            if not next_link:
                break
            
            # Update URL and reset params for next page
            devices_url = next_link
            params = {}  # next link already contains query parameters
    
    def get_device_custom_fields(self, device_id: int) -> Dict[str, Any]:
        """
        Get custom fields for a specific device.
        
        Args:
            device_id: The device ID to fetch custom fields for
            
        Returns:
            dict: Custom field data from Ninja API
        """
        try:
            headers = self._get_api_headers()
            custom_fields_url = f"{self.base_url}/api/v2/device/{device_id}/custom-fields"
            
            response = self.session.get(custom_fields_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            custom_fields_data = response.json()
            
            # The API returns a dict with field names as keys and values as values
            if isinstance(custom_fields_data, dict):
                return custom_fields_data
            else:
                return {}
                
        except Exception as e:
            # Return empty dict if custom fields can't be fetched
            return {}
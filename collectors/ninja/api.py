"""Ninja API client for device collection."""

import requests
from typing import Generator, Dict, Any, Optional

from collectors.ninja.token_manager import get_access_token, get_credentials


class NinjaAPI:
    """NinjaRMM API client for device data collection."""

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
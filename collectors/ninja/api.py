"""Ninja API client for device collection."""

import os
import requests
from typing import Generator, Dict, Any, Optional


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

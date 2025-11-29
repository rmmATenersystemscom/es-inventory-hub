"""VadeSecure API client for customer/license data collection."""

import os
import requests
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

from common.logging import get_logger

# Load environment variables from .env file
load_dotenv()


class VadeSecureAPI:
    """VadeSecure API client for customer and license data collection."""

    def __init__(self):
        """Initialize the API client with credentials from environment."""
        self.logger = get_logger(__name__)
        self.base_url = os.getenv('VADE_BASE_URL', 'https://api.vadesecure.com').rstrip('/')
        self.token_url = os.getenv('VADE_TOKEN_URL', 'https://api.vadesecure.com/oauth2/v1/token')
        self.client_id = os.getenv('VADE_CLIENT_ID')
        self.client_secret = os.getenv('VADE_CLIENT_SECRET')

        # Also support static token for simpler setups
        self.static_token = os.getenv('VADE_ACCESS_TOKEN')

        # Check for required credentials
        if not self.static_token and (not self.client_id or not self.client_secret):
            raise ValueError(
                "Missing required VadeSecure environment variables: "
                "Either VADE_ACCESS_TOKEN or both VADE_CLIENT_ID and VADE_CLIENT_SECRET"
            )

        # Initialize session
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })

        # Cache for access token
        self._access_token = None

    def _get_access_token(self) -> str:
        """Get OAuth2 access token using client credentials flow."""
        # Use static token if provided
        if self.static_token:
            return self.static_token

        # Use cached token if available
        if self._access_token:
            return self._access_token

        self.logger.info("Obtaining VadeSecure access token via OAuth2")

        try:
            response = requests.post(
                self.token_url,
                data={
                    'grant_type': 'client_credentials',
                    'client_id': self.client_id,
                    'client_secret': self.client_secret,
                },
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=30
            )

            response.raise_for_status()
            token_data = response.json()

            self._access_token = token_data.get('access_token')
            if not self._access_token:
                raise ValueError("No access_token in OAuth2 response")

            self.logger.info("Successfully obtained VadeSecure access token")
            return self._access_token

        except Exception as e:
            self.logger.error(f"Failed to obtain VadeSecure access token: {e}")
            raise

    def _get_auth_headers(self) -> Dict[str, str]:
        """Get headers with authentication token."""
        token = self._get_access_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def list_customers(self) -> List[Dict[str, Any]]:
        """
        Fetch all customers from VadeSecure API.

        Returns:
            list: List of raw customer dictionaries from VadeSecure API
        """
        try:
            url = f"{self.base_url}/customer/v2/customers"
            headers = self._get_auth_headers()

            self.logger.info(f"Fetching customers from VadeSecure API")
            self.logger.debug(f"Request URL: {url}")

            response = self.session.get(url, headers=headers, timeout=60)

            # Log response status
            self.logger.debug(f"Response status code: {response.status_code}")

            response.raise_for_status()

            customers = response.json()

            # Handle different response formats
            if isinstance(customers, dict):
                # If response is wrapped in a data object
                customers = customers.get('data', customers.get('customers', []))

            if not isinstance(customers, list):
                customers = [customers] if customers else []

            self.logger.info(f"VadeSecure API: Retrieved {len(customers)} customers")
            return customers

        except requests.exceptions.HTTPError as e:
            self.logger.error(f"HTTP error fetching VadeSecure customers: {e}")
            raise
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request error fetching VadeSecure customers: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error fetching VadeSecure customers: {e}")
            raise

    def get_customer(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch a specific customer by ID.

        Args:
            customer_id: The VadeSecure customer ID

        Returns:
            dict: Customer data or None if not found
        """
        try:
            url = f"{self.base_url}/customer/v2/customers/{customer_id}"
            headers = self._get_auth_headers()

            self.logger.debug(f"Fetching customer {customer_id}")

            response = self.session.get(url, headers=headers, timeout=30)

            if response.status_code == 404:
                return None

            response.raise_for_status()
            return response.json()

        except Exception as e:
            self.logger.error(f"Error fetching VadeSecure customer {customer_id}: {e}")
            raise

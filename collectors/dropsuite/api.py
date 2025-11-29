"""Dropsuite API client for email backup data collection."""

import os
import time
import requests
from typing import List, Dict, Any, Optional, Generator
from dotenv import load_dotenv

from common.logging import get_logger

# Load environment variables from .env file
load_dotenv()


class DropsuiteAPI:
    """Dropsuite API client for user and account data collection."""

    def __init__(self):
        """Initialize the API client with credentials from environment."""
        self.logger = get_logger(__name__)
        self.base_url = os.getenv('DROPSUITE_API_URL', 'https://dropsuite.us/api').rstrip('/')
        self.reseller_token = os.getenv('DROPSUITE_RESELLER_TOKEN')
        self.admin_token = os.getenv('DROPSUITE_AUTHENTICATION_TOKEN')

        # Check for required credentials
        if not self.reseller_token:
            raise ValueError("Missing required DROPSUITE_RESELLER_TOKEN environment variable")
        if not self.admin_token:
            raise ValueError("Missing required DROPSUITE_AUTHENTICATION_TOKEN environment variable")

        # Initialize session
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Reseller-Token": self.reseller_token
        })

        # Rate limiting
        self._last_request_time = 0
        self._min_request_interval = 0.2  # 200ms between requests

    def _rate_limit(self):
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()

    def _make_request(self, endpoint: str, access_token: Optional[str] = None,
                      params: Optional[Dict] = None) -> Any:
        """
        Make an API request with proper headers and error handling.

        Args:
            endpoint: API endpoint (e.g., '/users')
            access_token: User-specific access token (uses admin token if not provided)
            params: Query parameters

        Returns:
            JSON response data
        """
        self._rate_limit()

        url = f"{self.base_url}{endpoint}"
        headers = {"X-Access-Token": access_token or self.admin_token}

        self.logger.debug(f"Request: GET {url} params={params}")

        try:
            response = self.session.get(url, headers=headers, params=params, timeout=60)

            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 60))
                self.logger.warning(f"Rate limited, waiting {retry_after}s")
                time.sleep(retry_after)
                return self._make_request(endpoint, access_token, params)

            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            self.logger.error(f"HTTP error: {e} - Response: {response.text[:500]}")
            raise
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request error: {e}")
            raise

    def list_users(self, per_page: int = 100) -> Generator[Dict[str, Any], None, None]:
        """
        Fetch all users (organizations) from Dropsuite API with pagination.

        Args:
            per_page: Number of users per page

        Yields:
            dict: User/organization data
        """
        page = 1
        total_fetched = 0

        self.logger.info("Fetching users from Dropsuite API")

        while True:
            params = {"page": page, "per_page": per_page}
            response = self._make_request("/users", params=params)

            if not response:
                break

            # Handle nested result_set structure
            # Response can be: [{"result_set": [users...]}, ...] or just [users...]
            users = []
            if isinstance(response, list):
                for item in response:
                    if isinstance(item, dict) and 'result_set' in item:
                        users.extend(item['result_set'])
                    elif isinstance(item, dict) and 'id' in item:
                        # Direct user object
                        users.append(item)

            if not users:
                break

            for user in users:
                total_fetched += 1
                yield user

            self.logger.debug(f"Fetched page {page}, {len(users)} users (total: {total_fetched})")

            if len(users) < per_page:
                break

            page += 1

        self.logger.info(f"Dropsuite API: Retrieved {total_fetched} users total")

    def list_accounts(self, user_auth_token: str, per_page: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch all accounts for a specific user/organization.

        Args:
            user_auth_token: The user's authentication_token from list_users()
            per_page: Number of accounts per page

        Returns:
            list: All accounts for the user
        """
        all_accounts = []
        page = 1

        while True:
            params = {"page": page, "per_page": per_page}
            response = self._make_request("/accounts", access_token=user_auth_token, params=params)

            if not response:
                break

            # Handle different response structures
            accounts = []
            if isinstance(response, dict) and 'result_set' in response:
                # Single dict with result_set: {"result_set": [accounts...]}
                accounts = response['result_set']
            elif isinstance(response, list):
                # List of items
                for item in response:
                    if isinstance(item, dict) and 'result_set' in item:
                        accounts.extend(item['result_set'])
                    elif isinstance(item, dict) and 'id' in item:
                        accounts.append(item)

            if not accounts:
                break

            all_accounts.extend(accounts)

            if len(accounts) < per_page:
                break

            page += 1

        return all_accounts

    def check_status(self) -> bool:
        """
        Check API health/status.

        Returns:
            bool: True if API is healthy
        """
        try:
            response = self._make_request("/status")
            return True
        except Exception as e:
            self.logger.error(f"API status check failed: {e}")
            return False

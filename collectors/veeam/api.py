"""Veeam VSPC API client with OAuth2 authentication."""

import os
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from common.logging import get_logger

logger = get_logger(__name__)


class VeeamAPI:
    """Client for Veeam Service Provider Console (VSPC) API."""

    def __init__(self):
        """Initialize VSPC API client from environment variables."""
        self.server = os.environ.get('VSPC_SERVER')
        self.port = os.environ.get('VSPC_PORT', '1280')
        self.username = os.environ.get('VSPC_USERNAME')
        self.password = os.environ.get('VSPC_PASSWORD')

        if not all([self.server, self.username, self.password]):
            raise ValueError(
                "Missing VSPC credentials. Required: VSPC_SERVER, VSPC_USERNAME, VSPC_PASSWORD"
            )

        self.base_url = f"https://{self.server}:{self.port}/api/v3"
        self.token_url = f"https://{self.server}:{self.port}/api/v3/token"

        self._token: Optional[str] = None
        self._token_expires: Optional[datetime] = None

        logger.info(f"Initialized VSPC API client for {self.server}:{self.port}")

    def _get_token(self) -> str:
        """Get OAuth2 access token, refreshing if needed."""
        # Check if we have a valid cached token
        if self._token and self._token_expires and datetime.now() < self._token_expires:
            return self._token

        logger.info("Requesting new OAuth2 token from VSPC")

        data = {
            'grant_type': 'password',
            'username': self.username,
            'password': self.password,
        }

        response = requests.post(
            self.token_url,
            data=data,
            verify=True,
            timeout=30
        )
        response.raise_for_status()

        token_data = response.json()
        self._token = token_data['access_token']

        # Set expiry with 5 minute buffer
        expires_in = token_data.get('expires_in', 3600)
        self._token_expires = datetime.now() + timedelta(seconds=expires_in - 300)

        logger.info("Successfully obtained OAuth2 token")
        return self._token

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authorization."""
        return {
            'Authorization': f'Bearer {self._get_token()}',
            'Accept': 'application/json',
        }

    def _api_get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make authenticated GET request to VSPC API."""
        url = f"{self.base_url}{endpoint}"

        response = requests.get(
            url,
            headers=self._get_headers(),
            params=params,
            verify=True,
            timeout=60
        )
        response.raise_for_status()

        return response.json()

    def _api_get_paginated(self, endpoint: str, params: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Get all items from paginated endpoint."""
        all_items = []
        offset = 0
        limit = 500

        if params is None:
            params = {}

        while True:
            params['offset'] = offset
            params['limit'] = limit

            response = self._api_get(endpoint, params)

            # VSPC API returns data in 'data' key
            items = response.get('data', [])
            if not items:
                break

            all_items.extend(items)
            logger.debug(f"Fetched {len(items)} items from {endpoint} (total: {len(all_items)})")

            # Check if we got fewer items than requested (last page)
            if len(items) < limit:
                break

            offset += limit

        return all_items

    def get_companies(self) -> List[Dict[str, Any]]:
        """Get all companies (organizations) from VSPC.

        Returns:
            List of company dicts with instanceUid, name, etc.
        """
        logger.info("Fetching companies from VSPC")
        companies = self._api_get_paginated('/organizations/companies')
        logger.info(f"Found {len(companies)} companies")
        return companies

    def get_cloud_usage(self) -> List[Dict[str, Any]]:
        """Get cloud usage data for all companies.

        Returns:
            List of usage dicts with companyUid and counters array
        """
        logger.info("Fetching cloud usage from VSPC")
        usage = self._api_get_paginated('/organizations/companies/usage')
        logger.info(f"Found {len(usage)} usage records")
        return usage

    def get_quota_data(self) -> List[Dict[str, Any]]:
        """Get storage quota data for all companies.

        Returns:
            List of quota dicts with companyUid, storageQuota, usedStorageQuota
        """
        logger.info("Fetching quota data from VSPC")
        quota = self._api_get_paginated('/organizations/companies/sites/backupResources/usage')
        logger.info(f"Found {len(quota)} quota records")
        return quota

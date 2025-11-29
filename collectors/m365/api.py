"""Microsoft 365 Graph API client."""

import os
import re
import requests
from typing import List, Dict, Any, Optional, Iterator
from datetime import datetime, timedelta

from common.logging import get_logger

logger = get_logger(__name__)


class M365API:
    """Client for Microsoft Graph API with multi-tenant support."""

    TOKEN_URL = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    GRAPH_URL = "https://graph.microsoft.com/v1.0"
    SCOPE = "https://graph.microsoft.com/.default"

    def __init__(self):
        """Initialize by loading all tenant credentials from environment."""
        self.tenants = self._load_tenants_from_env()
        self._token_cache = {}  # tenant_id -> (token, expiry)

        if not self.tenants:
            raise ValueError("No M365 tenant credentials found in environment")

        logger.info(f"Initialized M365 API client with {len(self.tenants)} tenants")

    def _load_tenants_from_env(self) -> List[Dict[str, str]]:
        """Load tenant credentials from environment variables.

        Looks for pattern: M365_{PREFIX}_TENANT_ID, M365_{PREFIX}_CLIENT_ID, M365_{PREFIX}_CLIENT_SECRET
        """
        tenants = []
        seen_prefixes = set()

        # Find all M365_*_TENANT_ID variables
        for key, value in os.environ.items():
            match = re.match(r'^M365_(.+)_TENANT_ID$', key)
            if match:
                prefix = match.group(1)
                if prefix in seen_prefixes:
                    continue
                seen_prefixes.add(prefix)

                tenant_id = value
                client_id = os.environ.get(f'M365_{prefix}_CLIENT_ID')
                client_secret = os.environ.get(f'M365_{prefix}_CLIENT_SECRET')

                if all([tenant_id, client_id, client_secret]):
                    tenants.append({
                        'name': prefix.replace('_', ' ').title(),
                        'prefix': prefix,
                        'tenant_id': tenant_id,
                        'client_id': client_id,
                        'client_secret': client_secret
                    })
                else:
                    logger.warning(f"Incomplete credentials for tenant prefix: {prefix}")

        return tenants

    def _get_access_token(self, tenant: Dict[str, str]) -> str:
        """Get OAuth2 access token for a tenant (with caching).

        Args:
            tenant: Tenant configuration dict

        Returns:
            Access token string
        """
        tenant_id = tenant['tenant_id']

        # Check cache
        if tenant_id in self._token_cache:
            token, expiry = self._token_cache[tenant_id]
            if datetime.now() < expiry:
                return token

        # Request new token
        url = self.TOKEN_URL.format(tenant_id=tenant_id)
        data = {
            'grant_type': 'client_credentials',
            'client_id': tenant['client_id'],
            'client_secret': tenant['client_secret'],
            'scope': self.SCOPE
        }

        try:
            response = requests.post(url, data=data, timeout=30)
            response.raise_for_status()
            result = response.json()

            token = result['access_token']
            # Cache with 5-minute buffer before expiry
            expires_in = result.get('expires_in', 3600)
            expiry = datetime.now() + timedelta(seconds=expires_in - 300)
            self._token_cache[tenant_id] = (token, expiry)

            return token
        except requests.RequestException as e:
            logger.error(f"Failed to get token for tenant {tenant['name']}: {e}")
            raise

    def _graph_get(self, tenant: Dict[str, str], endpoint: str,
                   params: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Make authenticated GET request to Graph API.

        Args:
            tenant: Tenant configuration
            endpoint: API endpoint (e.g., '/users')
            params: Optional query parameters

        Returns:
            JSON response as dict
        """
        token = self._get_access_token(tenant)
        url = f"{self.GRAPH_URL}{endpoint}"
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=60)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Graph API error for {tenant['name']}: {e}")
            raise

    def _graph_get_paginated(self, tenant: Dict[str, str], endpoint: str,
                             params: Optional[Dict[str, str]] = None) -> Iterator[Dict[str, Any]]:
        """Make paginated GET request to Graph API.

        Args:
            tenant: Tenant configuration
            endpoint: API endpoint
            params: Optional query parameters

        Yields:
            Individual items from paginated response
        """
        token = self._get_access_token(tenant)
        url = f"{self.GRAPH_URL}{endpoint}"
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

        while url:
            try:
                response = requests.get(url, headers=headers, params=params, timeout=60)
                response.raise_for_status()
                data = response.json()

                # Yield each item
                for item in data.get('value', []):
                    yield item

                # Get next page URL
                url = data.get('@odata.nextLink')
                params = None  # Next link includes all params
                headers['Authorization'] = f'Bearer {self._get_access_token(tenant)}'

            except requests.RequestException as e:
                logger.error(f"Graph API pagination error for {tenant['name']}: {e}")
                raise

    def list_tenants(self) -> List[Dict[str, str]]:
        """Get list of configured tenants.

        Returns:
            List of tenant configuration dicts
        """
        return self.tenants

    def get_users(self, tenant: Dict[str, str]) -> List[Dict[str, Any]]:
        """Get all users with their assigned licenses for a tenant.

        Args:
            tenant: Tenant configuration

        Returns:
            List of user dicts with displayName, userPrincipalName, assignedLicenses
        """
        logger.debug(f"Fetching users for tenant {tenant['name']}")

        params = {
            '$select': 'displayName,userPrincipalName,assignedLicenses',
            '$top': '999'
        }

        users = list(self._graph_get_paginated(tenant, '/users', params))
        logger.debug(f"Found {len(users)} users for {tenant['name']}")
        return users

    def get_subscribed_skus(self, tenant: Dict[str, str]) -> List[Dict[str, Any]]:
        """Get subscribed SKUs (license information) for a tenant.

        Args:
            tenant: Tenant configuration

        Returns:
            List of SKU dicts with skuId, skuPartNumber, consumedUnits, etc.
        """
        logger.debug(f"Fetching subscribed SKUs for tenant {tenant['name']}")

        try:
            response = self._graph_get(tenant, '/subscribedSkus')
            skus = response.get('value', [])
            logger.debug(f"Found {len(skus)} SKUs for {tenant['name']}")
            return skus
        except Exception as e:
            logger.warning(f"Failed to get SKUs for {tenant['name']}: {e}")
            return []

    def get_organization(self, tenant: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Get organization details for a tenant.

        Args:
            tenant: Tenant configuration

        Returns:
            Organization dict or None
        """
        logger.debug(f"Fetching organization info for tenant {tenant['name']}")

        try:
            response = self._graph_get(tenant, '/organization')
            orgs = response.get('value', [])
            return orgs[0] if orgs else None
        except Exception as e:
            logger.warning(f"Failed to get organization for {tenant['name']}: {e}")
            return None

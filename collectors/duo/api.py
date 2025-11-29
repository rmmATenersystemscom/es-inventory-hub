"""Duo MFA API client."""

import os
import time
from typing import List, Dict, Any, Optional, Iterator
import duo_client

from common.logging import get_logger

logger = get_logger(__name__)


class DuoAPI:
    """Client for Duo Admin API with parent/child account support."""

    def __init__(self):
        """Initialize with credentials from environment."""
        self.ikey = os.environ.get('DUO_IKEY')
        self.skey = os.environ.get('DUO_SKEY')
        self.host = os.environ.get('DUO_HOST')

        if not all([self.ikey, self.skey, self.host]):
            raise ValueError(
                "Missing required environment variables: DUO_IKEY, DUO_SKEY, DUO_HOST"
            )

        # Create admin API client using parent host
        self.admin_api = duo_client.Admin(
            ikey=self.ikey,
            skey=self.skey,
            host=self.host
        )

        # Create accounts API for listing child accounts
        self.accounts_api = duo_client.Accounts(
            ikey=self.ikey,
            skey=self.skey,
            host=self.host
        )

        logger.info(f"Initialized Duo API client for host: {self.host}")

    def list_accounts(self) -> List[Dict[str, Any]]:
        """List all child accounts from parent.

        Returns:
            List of account dictionaries with account_id and name.
        """
        logger.info("Fetching child accounts from parent")

        try:
            # Use the accounts API to list child accounts
            response = self.accounts_api.get_child_accounts()
            accounts = response if isinstance(response, list) else []
            logger.info(f"Found {len(accounts)} child accounts")
            return accounts
        except Exception as e:
            logger.error(f"Failed to list accounts: {e}")
            raise

    def _paginated_get(self, endpoint: str, account_id: str,
                       limit: int = 100) -> Iterator[Dict[str, Any]]:
        """Generic paginated GET for child account endpoints.

        Args:
            endpoint: API endpoint path (e.g., '/admin/v1/users')
            account_id: Child account ID
            limit: Items per page

        Yields:
            Individual items from the response.
        """
        offset = 0

        while True:
            params = {
                'account_id': account_id,
                'limit': str(limit),
                'offset': str(offset)
            }

            try:
                response = self.admin_api.json_api_call('GET', endpoint, params)

                # Response is a list of items
                items = response if isinstance(response, list) else []

                if not items:
                    break

                for item in items:
                    yield item

                # If we got fewer items than limit, we've reached the end
                if len(items) < limit:
                    break

                offset += limit

                # Rate limiting - be gentle with the API
                time.sleep(0.5)

            except Exception as e:
                logger.error(f"Error fetching {endpoint} for account {account_id}: {e}")
                raise

    def get_users(self, account_id: str) -> List[Dict[str, Any]]:
        """Get all users for a child account.

        Args:
            account_id: Child account ID

        Returns:
            List of user dictionaries.
        """
        logger.debug(f"Fetching users for account {account_id}")
        users = list(self._paginated_get('/admin/v1/users', account_id))
        logger.debug(f"Found {len(users)} users")
        return users

    def get_phones(self, account_id: str) -> List[Dict[str, Any]]:
        """Get all phones/devices for a child account.

        Args:
            account_id: Child account ID

        Returns:
            List of phone dictionaries.
        """
        logger.debug(f"Fetching phones for account {account_id}")
        phones = list(self._paginated_get('/admin/v1/phones', account_id))
        logger.debug(f"Found {len(phones)} phones")
        return phones

    def get_groups(self, account_id: str) -> List[Dict[str, Any]]:
        """Get all groups for a child account.

        Args:
            account_id: Child account ID

        Returns:
            List of group dictionaries.
        """
        logger.debug(f"Fetching groups for account {account_id}")
        groups = list(self._paginated_get('/admin/v1/groups', account_id))
        logger.debug(f"Found {len(groups)} groups")
        return groups

    def get_integrations(self, account_id: str) -> List[Dict[str, Any]]:
        """Get all integrations for a child account.

        Args:
            account_id: Child account ID

        Returns:
            List of integration dictionaries.
        """
        logger.debug(f"Fetching integrations for account {account_id}")
        integrations = list(self._paginated_get('/admin/v1/integrations', account_id))
        logger.debug(f"Found {len(integrations)} integrations")
        return integrations

    def get_webauthn_credentials(self, account_id: str) -> List[Dict[str, Any]]:
        """Get all WebAuthn credentials for a child account.

        Args:
            account_id: Child account ID

        Returns:
            List of WebAuthn credential dictionaries.
        """
        logger.debug(f"Fetching WebAuthn credentials for account {account_id}")
        try:
            credentials = list(self._paginated_get('/admin/v1/webauthncredentials', account_id))
            logger.debug(f"Found {len(credentials)} WebAuthn credentials")
            return credentials
        except Exception as e:
            # WebAuthn endpoint may not be available for all accounts
            logger.debug(f"WebAuthn endpoint not available: {e}")
            return []

    def get_settings(self, account_id: str) -> Dict[str, Any]:
        """Get account settings for a child account.

        Args:
            account_id: Child account ID

        Returns:
            Settings dictionary.
        """
        logger.debug(f"Fetching settings for account {account_id}")
        try:
            params = {'account_id': account_id}
            response = self.admin_api.json_api_call('GET', '/admin/v1/settings', params)
            return response if isinstance(response, dict) else {}
        except Exception as e:
            logger.debug(f"Failed to fetch settings: {e}")
            return {}

    def get_info(self, account_id: str) -> Dict[str, Any]:
        """Get account info for a child account.

        Args:
            account_id: Child account ID

        Returns:
            Info dictionary with account metadata.
        """
        logger.debug(f"Fetching info for account {account_id}")
        try:
            params = {'account_id': account_id}
            response = self.admin_api.json_api_call('GET', '/admin/v1/info/summary', params)
            return response if isinstance(response, dict) else {}
        except Exception as e:
            logger.debug(f"Failed to fetch info: {e}")
            return {}

    def get_auth_logs(self, account_id: str, mintime: Optional[int] = None,
                      maxtime: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get authentication logs for a child account.

        Args:
            account_id: Child account ID
            mintime: Minimum timestamp (epoch seconds)
            maxtime: Maximum timestamp (epoch seconds)

        Returns:
            List of auth log entries.
        """
        logger.debug(f"Fetching auth logs for account {account_id}")

        # Default to last 24 hours if not specified
        if maxtime is None:
            maxtime = int(time.time())
        if mintime is None:
            mintime = maxtime - (24 * 60 * 60)  # 24 hours ago

        all_logs = []
        next_offset = None

        while True:
            params = {
                'account_id': account_id,
                'mintime': str(mintime * 1000),  # API expects milliseconds
                'maxtime': str(maxtime * 1000),
                'limit': '1000'
            }

            if next_offset:
                params['next_offset'] = next_offset

            try:
                response = self.admin_api.json_api_call(
                    'GET', '/admin/v2/logs/authentication', params
                )

                # v2 API returns dict with authlogs and metadata
                if isinstance(response, dict):
                    logs = response.get('authlogs', [])
                    metadata = response.get('metadata', {})
                    next_offset = metadata.get('next_offset')
                else:
                    logs = response if isinstance(response, list) else []
                    next_offset = None

                all_logs.extend(logs)

                if not next_offset:
                    break

                time.sleep(0.5)

            except Exception as e:
                logger.debug(f"Failed to fetch auth logs: {e}")
                break

        logger.debug(f"Found {len(all_logs)} auth log entries")
        return all_logs

    def get_telephony_logs(self, account_id: str, mintime: Optional[int] = None,
                           maxtime: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get telephony logs for a child account.

        Args:
            account_id: Child account ID
            mintime: Minimum timestamp (epoch seconds)
            maxtime: Maximum timestamp (epoch seconds)

        Returns:
            List of telephony log entries.
        """
        logger.debug(f"Fetching telephony logs for account {account_id}")

        # Default to last 24 hours if not specified
        if maxtime is None:
            maxtime = int(time.time())
        if mintime is None:
            mintime = maxtime - (24 * 60 * 60)

        try:
            params = {
                'account_id': account_id,
                'mintime': str(mintime),
                'maxtime': str(maxtime)
            }
            response = self.admin_api.json_api_call(
                'GET', '/admin/v1/logs/telephony', params
            )
            logs = response if isinstance(response, list) else []
            logger.debug(f"Found {len(logs)} telephony log entries")
            return logs
        except Exception as e:
            logger.debug(f"Failed to fetch telephony logs: {e}")
            return []

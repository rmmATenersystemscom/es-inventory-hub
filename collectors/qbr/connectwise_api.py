"""ConnectWise Manage API client for QBR collectors."""

import os
import base64
import time
from typing import List, Dict, Any, Optional
import requests

from common.logging import get_logger


class ConnectWiseAPI:
    """
    ConnectWise Manage API client.

    Handles authentication, pagination, and error handling for ConnectWise API calls.
    """

    def __init__(
        self,
        server: Optional[str] = None,
        company_id: Optional[str] = None,
        public_key: Optional[str] = None,
        private_key: Optional[str] = None,
        client_id: Optional[str] = None,
        timeout: int = 120
    ):
        """
        Initialize ConnectWise API client.

        Args:
            server: ConnectWise server URL (from env if not provided)
            company_id: Company ID (from env if not provided)
            public_key: Public API key (from env if not provided)
            private_key: Private API key (from env if not provided)
            client_id: Client ID (from env if not provided)
            timeout: Request timeout in seconds (default: 120)
        """
        self.server = server or os.environ.get('CONNECTWISE_SERVER')
        # Ensure server has https:// scheme
        if self.server and not self.server.startswith(('http://', 'https://')):
            self.server = f'https://{self.server}'
        self.company_id = company_id or os.environ.get('CONNECTWISE_COMPANY_ID')
        self.public_key = public_key or os.environ.get('CONNECTWISE_PUBLIC_KEY')
        self.private_key = private_key or os.environ.get('CONNECTWISE_PRIVATE_KEY')
        self.client_id = client_id or os.environ.get('CONNECTWISE_CLIENT_ID')
        self.timeout = timeout
        self.logger = get_logger(__name__)

        # Validate required credentials
        if not all([self.server, self.company_id, self.public_key, self.private_key, self.client_id]):
            raise ValueError(
                "Missing ConnectWise credentials. Required: "
                "CONNECTWISE_SERVER, CONNECTWISE_COMPANY_ID, CONNECTWISE_PUBLIC_KEY, "
                "CONNECTWISE_PRIVATE_KEY, CONNECTWISE_CLIENT_ID"
            )

        # Create session for connection pooling
        self.session = requests.Session()
        self.session.headers.update(self._get_auth_headers())

    def _get_auth_headers(self) -> Dict[str, str]:
        """
        Get authentication headers for ConnectWise API.

        Returns:
            Dict of headers with authentication
        """
        # Format: company_id+public_key:private_key
        auth_string = f"{self.company_id}+{self.public_key}:{self.private_key}"
        encoded_auth = base64.b64encode(auth_string.encode()).decode()

        return {
            'Authorization': f'Basic {encoded_auth}',
            'Accept': 'application/json',
            'clientId': self.client_id
        }

    def get_tickets(
        self,
        conditions: str,
        fields: Optional[str] = None,
        page_size: int = 250,
        max_retries: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Get service tickets with pagination.

        Args:
            conditions: ConnectWise conditions string (e.g., "board/name='Help Desk'")
            fields: Comma-separated fields to return (optional)
            page_size: Number of records per page (default: 250, max: 250)
            max_retries: Maximum retry attempts (default: 3)

        Returns:
            List of ticket dictionaries
        """
        endpoint = f"{self.server}/v4_6_release/apis/3.0/service/tickets"
        all_tickets = []
        page = 1

        while True:
            params = {
                'conditions': conditions,
                'pageSize': page_size,
                'page': page
            }

            if fields:
                params['fields'] = fields

            # Retry logic
            for attempt in range(1, max_retries + 1):
                try:
                    self.logger.debug(f"Fetching tickets page {page} (attempt {attempt}/{max_retries})")
                    response = self.session.get(endpoint, params=params, timeout=self.timeout)
                    response.raise_for_status()
                    tickets = response.json()

                    if not tickets:
                        # No more pages
                        self.logger.info(f"Retrieved {len(all_tickets)} total tickets")
                        return all_tickets

                    all_tickets.extend(tickets)
                    self.logger.debug(f"Page {page}: {len(tickets)} tickets (total: {len(all_tickets)})")
                    page += 1
                    break  # Success, exit retry loop

                except requests.exceptions.RequestException as e:
                    self.logger.warning(f"Request failed (attempt {attempt}/{max_retries}): {e}")

                    if attempt < max_retries:
                        wait_time = 2 ** attempt
                        self.logger.info(f"Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                    else:
                        raise

        return all_tickets

    def get_time_entries(
        self,
        conditions: str,
        fields: Optional[str] = None,
        page_size: int = 250,
        max_retries: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Get time entries with pagination.

        Args:
            conditions: ConnectWise conditions string
            fields: Comma-separated fields to return (optional)
            page_size: Number of records per page (default: 250, max: 250)
            max_retries: Maximum retry attempts (default: 3)

        Returns:
            List of time entry dictionaries
        """
        endpoint = f"{self.server}/v4_6_release/apis/3.0/time/entries"
        all_entries = []
        page = 1

        while True:
            params = {
                'conditions': conditions,
                'pageSize': page_size,
                'page': page
            }

            if fields:
                params['fields'] = fields

            # Retry logic
            for attempt in range(1, max_retries + 1):
                try:
                    self.logger.debug(f"Fetching time entries page {page} (attempt {attempt}/{max_retries})")
                    response = self.session.get(endpoint, params=params, timeout=self.timeout)
                    response.raise_for_status()
                    entries = response.json()

                    if not entries:
                        # No more pages
                        self.logger.info(f"Retrieved {len(all_entries)} total time entries")
                        return all_entries

                    all_entries.extend(entries)
                    self.logger.debug(f"Page {page}: {len(entries)} entries (total: {len(all_entries)})")
                    page += 1
                    break  # Success, exit retry loop

                except requests.exceptions.RequestException as e:
                    self.logger.warning(f"Request failed (attempt {attempt}/{max_retries}): {e}")

                    if attempt < max_retries:
                        wait_time = 2 ** attempt
                        self.logger.info(f"Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                    else:
                        raise

        return all_entries

    def get_tickets_by_ids(
        self,
        ticket_ids: List[int],
        batch_size: int = 20,
        max_retries: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Get tickets by IDs in batches (to avoid URL length limits).

        Args:
            ticket_ids: List of ticket IDs
            batch_size: Batch size (default: 20 to avoid URL length issues)
            max_retries: Maximum retry attempts (default: 3)

        Returns:
            List of ticket dictionaries
        """
        all_tickets = []

        # Process in batches
        for i in range(0, len(ticket_ids), batch_size):
            batch = ticket_ids[i:i + batch_size]
            id_list = ','.join(str(tid) for tid in batch)
            conditions = f"id IN ({id_list})"

            self.logger.debug(f"Fetching batch {i//batch_size + 1}: {len(batch)} ticket IDs")
            tickets = self.get_tickets(conditions=conditions, max_retries=max_retries)
            all_tickets.extend(tickets)

        return all_tickets

    def close(self):
        """Close the session."""
        if self.session:
            self.session.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

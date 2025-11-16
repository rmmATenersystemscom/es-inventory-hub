"""ConnectWise QBR collector - collects ticket and time entry metrics."""

from typing import List, Dict, Any
from decimal import Decimal

from .base_collector import BaseQBRCollector
from .connectwise_api import ConnectWiseAPI
from .utils import get_period_boundaries, format_iso_date


class ConnectWiseQBRCollector(BaseQBRCollector):
    """
    ConnectWise QBR collector.

    Collects three metrics:
    1. # of Reactive Tickets Created
    2. # of Reactive Tickets Closed
    3. Total Time on Reactive Tickets (hours)

    Uses REACTIVE_TICKETS_FILTERING logic:
    - Board: "Help Desk"
    - Parent tickets only (parentTicketId = null)
    """

    # Help Desk board name
    HELP_DESK_BOARD = "Help Desk"

    # Closed status names
    CLOSED_STATUSES = [">Closed", ">Closed - No response", "Closed"]

    def __init__(self, organization_id: int = 1):
        """
        Initialize ConnectWise QBR collector.

        Args:
            organization_id: Organization ID (default: 1 for Enersystems, LLC)
        """
        super().__init__(vendor_name='ConnectWise', organization_id=organization_id)
        self.api: ConnectWiseAPI = None

    def collect_metrics(self, period: str) -> List[Dict[str, Any]]:
        """
        Collect ConnectWise metrics for the specified period.

        Args:
            period: Period string (YYYY-MM)

        Returns:
            List of metric dictionaries
        """
        metrics = []

        # Get period boundaries
        period_start, period_end = get_period_boundaries(period)
        start_date = format_iso_date(period_start)
        end_date = format_iso_date(period_end)

        self.logger.info(f"Collecting ConnectWise metrics for {period}: {start_date} to {end_date}")

        # Initialize API client
        with ConnectWiseAPI() as self.api:
            # Metric 1: Reactive Tickets Created
            tickets_created = self._count_tickets_created(start_date, end_date)
            metrics.append({
                'metric_name': 'reactive_tickets_created',
                'metric_value': Decimal(str(tickets_created)),
                'data_source': 'collected',
                'notes': f'Help Desk board, parent tickets only, dateEntered {start_date} to {end_date}'
            })
            self.logger.info(f"Reactive Tickets Created: {tickets_created}")

            # Metric 2: Reactive Tickets Closed
            tickets_closed = self._count_tickets_closed(start_date, end_date)
            metrics.append({
                'metric_name': 'reactive_tickets_closed',
                'metric_value': Decimal(str(tickets_closed)),
                'data_source': 'collected',
                'notes': f'Help Desk board, parent tickets only, closedDate {start_date} to {end_date}'
            })
            self.logger.info(f"Reactive Tickets Closed: {tickets_closed}")

            # Metric 3: Total Time on Reactive Tickets
            total_hours = self._sum_reactive_time(start_date, end_date)
            metrics.append({
                'metric_name': 'reactive_time_spent',
                'metric_value': Decimal(str(round(total_hours, 2))),
                'data_source': 'collected',
                'notes': f'Help Desk tickets only, time entries {start_date} to {end_date}'
            })
            self.logger.info(f"Reactive Time Spent: {total_hours:.2f} hours")

        return metrics

    def _count_tickets_created(self, start_date: str, end_date: str) -> int:
        """
        Count reactive tickets created in the period.

        Filters:
        - Board: "Help Desk"
        - Parent tickets only (parentTicketId = null)
        - Created date within period (dateEntered)

        Args:
            start_date: Period start date (ISO 8601 with brackets)
            end_date: Period end date (ISO 8601 with brackets)

        Returns:
            int: Count of tickets created
        """
        conditions = (
            f'dateEntered>={start_date} AND '
            f'dateEntered<={end_date} AND '
            f'board/name="{self.HELP_DESK_BOARD}" AND '
            f'parentTicketId = null'
        )

        self.logger.debug(f"Tickets Created conditions: {conditions}")

        tickets = self.api.get_tickets(
            conditions=conditions,
            fields='id'  # Only need count, so just get ID
        )

        return len(tickets)

    def _count_tickets_closed(self, start_date: str, end_date: str) -> int:
        """
        Count reactive tickets closed in the period.

        Filters:
        - Board: "Help Desk"
        - Parent tickets only (parentTicketId = null)
        - Closed date within period (closedDate)
        - Status in closed status list

        Args:
            start_date: Period start date (ISO 8601 with brackets)
            end_date: Period end date (ISO 8601 with brackets)

        Returns:
            int: Count of tickets closed
        """
        # Build status condition
        status_list = ','.join(f'"{status}"' for status in self.CLOSED_STATUSES)

        conditions = (
            f'status/name IN ({status_list}) AND '
            f'closedDate>={start_date} AND '
            f'closedDate<={end_date} AND '
            f'board/name="{self.HELP_DESK_BOARD}" AND '
            f'parentTicketId = null'
        )

        self.logger.debug(f"Tickets Closed conditions: {conditions}")

        tickets = self.api.get_tickets(
            conditions=conditions,
            fields='id'  # Only need count, so just get ID
        )

        return len(tickets)

    def _sum_reactive_time(self, start_date: str, end_date: str) -> float:
        """
        Sum time spent on reactive tickets in the period.

        Process:
        1. Get all time entries for the period (chargeToType="ServiceTicket")
        2. Extract unique ticket IDs from time entries
        3. Query tickets in batches to identify Help Desk tickets
        4. Sum actualHours only for Help Desk tickets

        Args:
            start_date: Period start date (ISO 8601 with brackets)
            end_date: Period end date (ISO 8601 with brackets)

        Returns:
            float: Total hours spent
        """
        # Step 1: Get all time entries for the period
        time_conditions = (
            f'dateEntered>={start_date} AND '
            f'dateEntered<={end_date} AND '
            f'chargeToType="ServiceTicket"'
        )

        self.logger.debug(f"Time Entries conditions: {time_conditions}")

        time_entries = self.api.get_time_entries(
            conditions=time_conditions,
            fields='id,chargeToId,actualHours'
        )

        if not time_entries:
            self.logger.info("No time entries found for period")
            return 0.0

        self.logger.info(f"Retrieved {len(time_entries)} time entries")

        # Step 2: Extract unique ticket IDs
        ticket_ids = set()
        time_by_ticket = {}  # ticket_id -> total hours

        for entry in time_entries:
            ticket_id = entry.get('chargeToId')
            actual_hours = entry.get('actualHours', 0)

            if ticket_id:
                ticket_ids.add(ticket_id)
                time_by_ticket[ticket_id] = time_by_ticket.get(ticket_id, 0) + actual_hours

        self.logger.info(f"Time entries reference {len(ticket_ids)} unique tickets")

        # Step 3: Query tickets in batches to identify Help Desk tickets
        help_desk_ticket_ids = set()

        if ticket_ids:
            tickets = self.api.get_tickets_by_ids(
                ticket_ids=list(ticket_ids),
                batch_size=20  # Batch to avoid URL length limits
            )

            for ticket in tickets:
                board_name = ticket.get('board', {}).get('name') if isinstance(ticket.get('board'), dict) else None
                if board_name == self.HELP_DESK_BOARD:
                    help_desk_ticket_ids.add(ticket.get('id'))

            self.logger.info(f"Found {len(help_desk_ticket_ids)} Help Desk tickets out of {len(ticket_ids)} total")

        # Step 4: Sum hours only for Help Desk tickets
        total_hours = sum(
            hours
            for ticket_id, hours in time_by_ticket.items()
            if ticket_id in help_desk_ticket_ids
        )

        return total_hours

"""NinjaOne QBR collector - collects device counts from existing snapshots."""

from typing import List, Dict, Any
from decimal import Decimal

from sqlalchemy import func, and_, or_
from sqlalchemy.orm import Session

from common.db import session_scope
from storage.schema import DeviceSnapshot
from .base_collector import BaseQBRCollector
from .utils import get_period_boundaries


class NinjaQBRCollector(BaseQBRCollector):
    """
    NinjaOne QBR collector.

    Collects two metrics:
    1. # of Endpoints Managed (billable count)
    2. # of Seats Managed (BHAG calculation)

    Note: This collector queries existing device_snapshot data, not the Ninja API.
    The daily Ninja collector already populates device_snapshot at 02:10 AM.
    """

    # Organizations to exclude from both metrics
    EXCLUDED_ORGS = ['Ener Systems', 'Internal Infrastructure', 'z_Terese Ashley']

    # Node classes to exclude from BHAG only
    BHAG_EXCLUDED_NODE_CLASSES = ['VMWARE_VM_GUEST', 'WINDOWS_SERVER', 'VMWARE_VM_HOST']

    def __init__(self, organization_id: int = 1):
        """
        Initialize NinjaOne QBR collector.

        Args:
            organization_id: Organization ID (default: 1 for Enersystems, LLC)
        """
        super().__init__(vendor_name='Ninja', organization_id=organization_id)

    def collect_metrics(self, period: str) -> List[Dict[str, Any]]:
        """
        Collect NinjaOne metrics for the specified period.

        Args:
            period: Period string (YYYY-MM)

        Returns:
            List of metric dictionaries
        """
        metrics = []

        with session_scope() as session:
            # Get latest snapshot date within the period
            latest_snapshot_date = self._get_latest_snapshot_date(session, period)

            if latest_snapshot_date is None:
                self.logger.warning(f"No Ninja snapshots found for period {period}")
                return metrics

            self.logger.info(f"Using snapshot date: {latest_snapshot_date} for period {period}")

            # Collect Endpoints Managed (billable count)
            endpoints_managed = self._count_endpoints_managed(session, latest_snapshot_date)
            metrics.append({
                'metric_name': 'endpoints_managed',
                'metric_value': Decimal(str(endpoints_managed)),
                'data_source': 'collected',
                'notes': f'Snapshot date: {latest_snapshot_date}'
            })
            self.logger.info(f"Endpoints Managed: {endpoints_managed}")

            # Collect Seats Managed (BHAG calculation)
            seats_managed = self._count_seats_managed(session, latest_snapshot_date)
            metrics.append({
                'metric_name': 'seats_managed',
                'metric_value': Decimal(str(seats_managed)),
                'data_source': 'collected',
                'notes': f'BHAG calculation, snapshot date: {latest_snapshot_date}'
            })
            self.logger.info(f"Seats Managed (BHAG): {seats_managed}")

        return metrics

    def _get_latest_snapshot_date(self, session: Session, period: str):
        """
        Get the latest snapshot date within the period.

        Args:
            session: Database session
            period: Period string (YYYY-MM)

        Returns:
            Latest snapshot date, or None if no snapshots found
        """
        period_start, period_end = get_period_boundaries(period)

        latest_date = session.query(func.max(DeviceSnapshot.snapshot_date)).filter(
            DeviceSnapshot.vendor_id == 2,  # Ninja vendor ID
            DeviceSnapshot.snapshot_date >= period_start.date(),
            DeviceSnapshot.snapshot_date <= period_end.date()
        ).scalar()

        return latest_date

    def _count_endpoints_managed(self, session: Session, snapshot_date) -> int:
        """
        Count # of Endpoints Managed (billable devices).

        Includes:
        - Physical workstations (not spare, not from excluded orgs)
        - Physical servers (not spare, not from excluded orgs)
        - VM hosts (not spare, not from excluded orgs)

        Excludes:
        - VM guests (already excluded - not in database)
        - Spare devices (billing_status = 'spare')
        - Internal organizations

        Args:
            session: Database session
            snapshot_date: Snapshot date to query

        Returns:
            int: Count of billable endpoints
        """
        count = session.query(func.count(func.distinct(DeviceSnapshot.device_identity_id))).filter(
            DeviceSnapshot.vendor_id == 2,  # Ninja
            DeviceSnapshot.snapshot_date == snapshot_date,
            DeviceSnapshot.billing_status_id == 1,  # billable status ID
            ~DeviceSnapshot.organization_name.in_(self.EXCLUDED_ORGS)
        ).scalar()

        return count or 0

    def _count_seats_managed(self, session: Session, snapshot_date) -> int:
        """
        Count # of Seats Managed (BHAG calculation).

        BHAG = Total devices MINUS:
        1. Servers (device_type_name = 'server')
        2. Spare devices (display name or location contains "spare")
        3. Internal organizations

        Note: VM guests are already excluded (not in database).
        VM hosts cannot be distinguished in current schema, so we exclude all servers as proxy.

        Args:
            session: Database session
            snapshot_date: Snapshot date to query

        Returns:
            int: Count of seats (BHAG)
        """
        # Get all devices for the snapshot date
        all_devices_query = session.query(
            DeviceSnapshot.device_identity_id,
            DeviceSnapshot.device_type_name,
            DeviceSnapshot.display_name,
            DeviceSnapshot.location_name,
            DeviceSnapshot.organization_name
        ).filter(
            DeviceSnapshot.vendor_id == 2,  # Ninja
            DeviceSnapshot.snapshot_date == snapshot_date
        )

        # Build exclusion criteria
        excluded_device_ids = set()

        for device_identity_id, device_type, display_name, location, org_name in all_devices_query:
            # Exclusion 1: Servers (includes Windows Server and VM hosts)
            if device_type == 'server':
                excluded_device_ids.add(device_identity_id)
                continue

            # Exclusion 2: Spare devices (display name or location contains "spare")
            if display_name and 'spare' in display_name.lower():
                excluded_device_ids.add(device_identity_id)
                continue

            if location and 'spare' in location.lower():
                excluded_device_ids.add(device_identity_id)
                continue

            # Exclusion 3: Internal organizations
            if org_name in self.EXCLUDED_ORGS:
                excluded_device_ids.add(device_identity_id)
                continue

        # Count total devices
        total_devices = session.query(
            func.count(func.distinct(DeviceSnapshot.device_identity_id))
        ).filter(
            DeviceSnapshot.vendor_id == 2,  # Ninja
            DeviceSnapshot.snapshot_date == snapshot_date
        ).scalar() or 0

        # Calculate BHAG
        bhag = total_devices - len(excluded_device_ids)

        self.logger.info(
            f"BHAG calculation: {total_devices} total - {len(excluded_device_ids)} excluded = {bhag}"
        )

        return bhag

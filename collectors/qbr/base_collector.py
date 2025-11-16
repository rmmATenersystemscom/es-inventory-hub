"""Base collector class for QBR metric collection."""

import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from common.logging import get_logger
from common.db import session_scope
from storage.schema import QBRCollectionLog, QBRMetricsMonthly, Organization, Vendor


class BaseQBRCollector(ABC):
    """
    Base class for all QBR collectors.

    Provides common functionality:
    - Database connection handling
    - Error handling with retry logic
    - Logging to qbr_collection_log table
    - Period calculation utilities
    - Data validation methods
    """

    def __init__(self, vendor_name: str, organization_id: int = 1):
        """
        Initialize the base collector.

        Args:
            vendor_name: Name of the vendor (e.g., 'Ninja', 'ConnectWise')
            organization_id: Organization ID (default: 1 for Enersystems, LLC)
        """
        self.vendor_name = vendor_name
        self.organization_id = organization_id
        self.logger = get_logger(f"qbr.{vendor_name.lower()}")
        self.vendor_id: Optional[int] = None

    def collect_period(self, period: str, max_retries: int = 3) -> bool:
        """
        Collect metrics for a specific period with retry logic.

        Args:
            period: Period string in format YYYY-MM (e.g., "2025-01")
            max_retries: Maximum number of retry attempts (default: 3)

        Returns:
            bool: True if collection succeeded, False otherwise
        """
        collection_started_at = datetime.now(timezone.utc)
        log_id: Optional[int] = None

        try:
            # Validate period format
            self._validate_period(period)

            # Get vendor ID
            with session_scope() as session:
                self.vendor_id = self._get_vendor_id(session)

                # Create collection log entry
                log_id = self._log_collection_start(session, period, collection_started_at)

            # Attempt collection with retries
            for attempt in range(1, max_retries + 1):
                try:
                    self.logger.info(f"Starting collection for {period} (attempt {attempt}/{max_retries})")

                    # Call subclass-specific collection logic
                    metrics = self.collect_metrics(period)

                    # Store metrics in database
                    with session_scope() as session:
                        metrics_count = self._store_metrics(session, period, metrics)

                    # Log success
                    collection_ended_at = datetime.now(timezone.utc)
                    duration_seconds = int((collection_ended_at - collection_started_at).total_seconds())

                    with session_scope() as session:
                        self._log_collection_success(
                            session, log_id, collection_ended_at,
                            metrics_count, duration_seconds
                        )

                    self.logger.info(f"Successfully collected {metrics_count} metrics for {period}")
                    return True

                except Exception as e:
                    self.logger.warning(f"Collection attempt {attempt} failed: {e}")

                    if attempt < max_retries:
                        # Exponential backoff: 2^attempt seconds
                        wait_time = 2 ** attempt
                        self.logger.info(f"Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                    else:
                        # All retries exhausted
                        raise

            return False

        except Exception as e:
            error_message = f"Collection failed after {max_retries} attempts: {str(e)}"
            self.logger.error(error_message)

            # Log failure
            collection_ended_at = datetime.now(timezone.utc)
            duration_seconds = int((collection_ended_at - collection_started_at).total_seconds())

            try:
                with session_scope() as session:
                    self._log_collection_failure(
                        session, log_id, collection_ended_at,
                        error_message, duration_seconds
                    )
            except Exception as log_error:
                self.logger.error(f"Failed to log collection failure: {log_error}")

            return False

    @abstractmethod
    def collect_metrics(self, period: str) -> List[Dict[str, Any]]:
        """
        Collect metrics for the specified period.

        Subclasses must implement this method to perform vendor-specific
        metric collection.

        Args:
            period: Period string in format YYYY-MM (e.g., "2025-01")

        Returns:
            List of metric dictionaries with keys:
                - metric_name: str
                - metric_value: Decimal or float
                - data_source: str (default: 'collected')
                - notes: Optional[str]
        """
        pass

    def _validate_period(self, period: str) -> None:
        """
        Validate period format (YYYY-MM).

        Args:
            period: Period string to validate

        Raises:
            ValueError: If period format is invalid
        """
        try:
            datetime.strptime(period, '%Y-%m')
        except ValueError:
            raise ValueError(f"Invalid period format: {period}. Expected YYYY-MM")

    def _get_vendor_id(self, session: Session) -> int:
        """
        Get vendor ID from database.

        Args:
            session: Database session

        Returns:
            int: Vendor ID

        Raises:
            ValueError: If vendor not found
        """
        vendor = session.query(Vendor).filter_by(name=self.vendor_name).first()
        if not vendor:
            raise ValueError(f"Vendor '{self.vendor_name}' not found in database")
        return vendor.id

    def _log_collection_start(
        self,
        session: Session,
        period: str,
        started_at: datetime
    ) -> int:
        """
        Log the start of a collection run.

        Args:
            session: Database session
            period: Period being collected
            started_at: Collection start timestamp

        Returns:
            int: Collection log ID
        """
        log_entry = QBRCollectionLog(
            collection_started_at=started_at,
            period=period,
            vendor_id=self.vendor_id,
            status='running'
        )
        session.add(log_entry)
        session.flush()  # Get the ID
        return log_entry.id

    def _log_collection_success(
        self,
        session: Session,
        log_id: int,
        ended_at: datetime,
        metrics_count: int,
        duration_seconds: int
    ) -> None:
        """
        Log successful collection completion.

        Args:
            session: Database session
            log_id: Collection log ID
            ended_at: Collection end timestamp
            metrics_count: Number of metrics collected
            duration_seconds: Collection duration in seconds
        """
        log_entry = session.query(QBRCollectionLog).filter_by(id=log_id).first()
        if log_entry:
            log_entry.collection_ended_at = ended_at
            log_entry.status = 'completed'
            log_entry.metrics_collected = metrics_count
            log_entry.duration_seconds = duration_seconds
            session.commit()

    def _log_collection_failure(
        self,
        session: Session,
        log_id: Optional[int],
        ended_at: datetime,
        error_message: str,
        duration_seconds: int
    ) -> None:
        """
        Log collection failure.

        Args:
            session: Database session
            log_id: Collection log ID (may be None if logging failed)
            ended_at: Collection end timestamp
            error_message: Error message
            duration_seconds: Collection duration in seconds
        """
        if log_id:
            log_entry = session.query(QBRCollectionLog).filter_by(id=log_id).first()
            if log_entry:
                log_entry.collection_ended_at = ended_at
                log_entry.status = 'failed'
                log_entry.error_message = error_message
                log_entry.duration_seconds = duration_seconds
                session.commit()

    def _store_metrics(
        self,
        session: Session,
        period: str,
        metrics: List[Dict[str, Any]]
    ) -> int:
        """
        Store collected metrics in the database.

        Args:
            session: Database session
            period: Period string (YYYY-MM)
            metrics: List of metric dictionaries

        Returns:
            int: Number of metrics stored
        """
        stored_count = 0
        current_time = datetime.now(timezone.utc)

        for metric_data in metrics:
            metric_name = metric_data['metric_name']
            metric_value = metric_data.get('metric_value')
            data_source = metric_data.get('data_source', 'collected')
            notes = metric_data.get('notes')

            # Convert to Decimal if needed
            if metric_value is not None and not isinstance(metric_value, Decimal):
                metric_value = Decimal(str(metric_value))

            # Check if metric already exists (upsert logic)
            existing = session.query(QBRMetricsMonthly).filter_by(
                period=period,
                metric_name=metric_name,
                organization_id=self.organization_id,
                vendor_id=self.vendor_id
            ).first()

            if existing:
                # Only update if data_source is 'collected' (don't overwrite manual entries)
                if existing.data_source == 'collected':
                    existing.metric_value = metric_value
                    existing.collected_at = current_time
                    existing.updated_at = current_time
                    if notes:
                        existing.notes = notes
                    stored_count += 1
                else:
                    self.logger.info(
                        f"Skipping metric '{metric_name}' - manually entered data preserved"
                    )
            else:
                # Insert new metric
                new_metric = QBRMetricsMonthly(
                    period=period,
                    organization_id=self.organization_id,
                    vendor_id=self.vendor_id,
                    metric_name=metric_name,
                    metric_value=metric_value,
                    data_source=data_source,
                    collected_at=current_time if data_source == 'collected' else None,
                    notes=notes
                )
                session.add(new_metric)
                stored_count += 1

        session.commit()
        return stored_count

    def get_period_boundaries(self, period: str) -> tuple[datetime, datetime]:
        """
        Calculate start and end timestamps for a period.

        Args:
            period: Period string (YYYY-MM)

        Returns:
            Tuple of (period_start, period_end) as UTC datetime objects
        """
        from calendar import monthrange

        year, month = map(int, period.split('-'))

        # First day of month at 00:00:00 UTC
        period_start = datetime(year, month, 1, 0, 0, 0, tzinfo=timezone.utc)

        # Last day of month at 23:59:59 UTC
        last_day = monthrange(year, month)[1]
        period_end = datetime(year, month, last_day, 23, 59, 59, tzinfo=timezone.utc)

        return period_start, period_end

    def validate_metric_value(
        self,
        value: Any,
        metric_name: str,
        allow_negative: bool = False,
        allow_zero: bool = True
    ) -> Optional[Decimal]:
        """
        Validate and convert a metric value.

        Args:
            value: The value to validate
            metric_name: Name of the metric (for error messages)
            allow_negative: Whether to allow negative values
            allow_zero: Whether to allow zero values

        Returns:
            Decimal: Validated metric value, or None if validation fails

        Raises:
            ValueError: If value is invalid
        """
        if value is None:
            return None

        try:
            decimal_value = Decimal(str(value))
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid value for metric '{metric_name}': {value}")

        # Check for negative values
        if not allow_negative and decimal_value < 0:
            raise ValueError(
                f"Negative value not allowed for metric '{metric_name}': {decimal_value}"
            )

        # Check for zero values
        if not allow_zero and decimal_value == 0:
            self.logger.warning(
                f"Zero value detected for metric '{metric_name}' - may indicate data issue"
            )

        return decimal_value

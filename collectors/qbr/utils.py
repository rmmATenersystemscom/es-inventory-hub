"""Utility functions for QBR collectors."""

from datetime import datetime, timezone, timedelta
from calendar import monthrange
from typing import List
from zoneinfo import ZoneInfo


def get_period_string(year: int, month: int) -> str:
    """
    Get period string in YYYY-MM format.

    Args:
        year: Year (e.g., 2025)
        month: Month (1-12)

    Returns:
        str: Period string (e.g., "2025-01")
    """
    return f"{year:04d}-{month:02d}"


def parse_period(period: str) -> tuple[int, int]:
    """
    Parse period string into year and month.

    Args:
        period: Period string (YYYY-MM)

    Returns:
        Tuple of (year, month)

    Raises:
        ValueError: If period format is invalid
    """
    try:
        year, month = map(int, period.split('-'))
        if not (1 <= month <= 12):
            raise ValueError("Month must be between 1 and 12")
        return year, month
    except (ValueError, AttributeError) as e:
        raise ValueError(f"Invalid period format: {period}. Expected YYYY-MM")


def get_period_boundaries(period: str) -> tuple[datetime, datetime]:
    """
    Calculate start and end timestamps for a period in Central Time.

    ConnectWise interprets dates in Central Time, so we need to provide
    month boundaries in CT and convert to UTC for the API.

    Args:
        period: Period string (YYYY-MM)

    Returns:
        Tuple of (period_start, period_end) as UTC datetime objects
        representing the full month in Central Time
    """
    year, month = parse_period(period)

    # Central Time zone
    central = ZoneInfo("America/Chicago")

    # First day of month at 00:00:00 Central Time
    period_start_ct = datetime(year, month, 1, 0, 0, 0, tzinfo=central)

    # Last day of month at 23:59:59 Central Time
    last_day = monthrange(year, month)[1]
    period_end_ct = datetime(year, month, last_day, 23, 59, 59, tzinfo=central)

    # Convert to UTC for API
    period_start = period_start_ct.astimezone(timezone.utc)
    period_end = period_end_ct.astimezone(timezone.utc)

    return period_start, period_end


def get_last_n_periods(n: int, end_period: str = None) -> List[str]:
    """
    Get list of last N periods (months).

    Args:
        n: Number of periods to retrieve
        end_period: End period (YYYY-MM). If None, uses current month.

    Returns:
        List of period strings in descending order (most recent first)

    Example:
        get_last_n_periods(3, "2025-03") -> ["2025-03", "2025-02", "2025-01"]
    """
    if end_period is None:
        now = datetime.now(timezone.utc)
        end_year, end_month = now.year, now.month
    else:
        end_year, end_month = parse_period(end_period)

    periods = []
    year, month = end_year, end_month

    for _ in range(n):
        periods.append(get_period_string(year, month))

        # Go back one month
        month -= 1
        if month < 1:
            month = 12
            year -= 1

    return periods


def get_current_period() -> str:
    """
    Get current period string (YYYY-MM) in UTC.

    Returns:
        str: Current period (e.g., "2025-01")
    """
    now = datetime.now(timezone.utc)
    return get_period_string(now.year, now.month)


def format_iso_date(dt: datetime) -> str:
    """
    Format datetime for ConnectWise API (ISO 8601 with brackets).

    Args:
        dt: Datetime to format

    Returns:
        str: Formatted string (e.g., "[2025-01-01T00:00:00Z]")
    """
    # Ensure UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)

    # Format as ISO 8601 with Z suffix and brackets
    return f"[{dt.strftime('%Y-%m-%dT%H:%M:%S')}Z]"


def is_current_period(period: str) -> bool:
    """
    Check if a period is the current period.

    Args:
        period: Period string (YYYY-MM)

    Returns:
        bool: True if period is current period, False otherwise
    """
    return period == get_current_period()


def get_period_month_name(period: str) -> str:
    """
    Get month name for a period.

    Args:
        period: Period string (YYYY-MM)

    Returns:
        str: Month name (e.g., "January")
    """
    year, month = parse_period(period)
    return datetime(year, month, 1).strftime('%B')

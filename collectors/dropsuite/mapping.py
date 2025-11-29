"""Dropsuite data normalization and mapping."""

from typing import Dict, Any, Optional, List
from datetime import datetime
from decimal import Decimal


def normalize_dropsuite_user(raw_user: Dict[str, Any],
                              accounts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Normalize a raw Dropsuite user record with aggregated account data.

    Dropsuite API response structure:
    User (from /api/users):
    {
        "id": "440032-6",
        "organization_name": "Company Name",
        "seats_used": 22,
        "archive": true,
        "customer_deactivated": false,
        "flg_suspended": false,
        "authentication_token": "...",
        ...
    }

    Account (from /api/accounts):
    {
        "id": 442803,
        "email": "user@company.com",
        "storage": 3525592,        # bytes
        "msg_count": 29437,
        "last_backup": "2025-11-26T00:02:23.939Z",
        "current_backup_status": "Completed",
        ...
    }

    Args:
        raw_user: Raw user/organization data from Dropsuite API
        accounts: List of account records for this user/organization

    Returns:
        dict: Normalized data for dropsuite_snapshot table
    """
    # User/organization ID
    user_id = raw_user.get('id', '')

    # Organization name
    organization_name = raw_user.get('organization_name', '')

    # Billable seats
    seats_used = raw_user.get('seats_used', 0)
    if not isinstance(seats_used, int):
        try:
            seats_used = int(seats_used)
        except (ValueError, TypeError):
            seats_used = 0

    # Archive type - boolean to string
    archive = raw_user.get('archive')
    if archive is True:
        archive_type = 'Archive'
    elif archive is False:
        archive_type = 'Backup Only'
    else:
        archive_type = None

    # Status - derive from deactivated/suspended flags
    customer_deactivated = raw_user.get('customer_deactivated', False)
    flg_suspended = raw_user.get('flg_suspended', False)

    if customer_deactivated:
        status = 'Deactivated'
    elif flg_suspended:
        status = 'Suspended'
    else:
        status = 'Active'

    # Aggregate account data
    total_emails = 0
    total_storage_bytes = 0
    last_backup_str = None

    for account in accounts:
        # Sum email counts
        msg_count = account.get('msg_count', 0)
        if isinstance(msg_count, int):
            total_emails += msg_count

        # Sum storage
        storage = account.get('storage', 0)
        if isinstance(storage, (int, float)):
            total_storage_bytes += storage

        # Track most recent backup
        backup_time = account.get('last_backup')
        if backup_time:
            if last_backup_str is None or backup_time > last_backup_str:
                last_backup_str = backup_time

    # Convert storage bytes to GB (with 2 decimal precision)
    storage_gb = Decimal(total_storage_bytes) / Decimal(1073741824)
    storage_gb = round(storage_gb, 2)

    # Parse last backup timestamp
    last_backup = _parse_iso_datetime(last_backup_str)

    # Compliance - check for any compliance-related fields
    # The API doesn't seem to have a direct compliance field,
    # so we'll derive it from archive setting for now
    compliance = archive if isinstance(archive, bool) else None

    return {
        'user_id': str(user_id) if user_id else None,
        'organization_name': _safe_strip(organization_name),
        'seats_used': seats_used,
        'archive_type': archive_type,
        'status': status,
        'total_emails': total_emails,
        'storage_gb': storage_gb,
        'last_backup': last_backup,
        'compliance': compliance,
        'raw': raw_user  # Store raw data for debugging
    }


def _safe_strip(value: Any) -> Optional[str]:
    """Safely strip whitespace from a value, handling non-strings."""
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped if stripped else None
    return str(value)


def _parse_iso_datetime(iso_str: Any) -> Optional[datetime]:
    """Parse ISO datetime string to datetime object."""
    if not iso_str or not isinstance(iso_str, str):
        return None
    try:
        # Handle ISO format: "2025-11-26T00:02:23.939Z"
        clean_str = iso_str.replace('Z', '+00:00')
        return datetime.fromisoformat(clean_str)
    except (ValueError, TypeError):
        return None

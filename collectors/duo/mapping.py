"""Duo data normalization and mapping."""

from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, List, Optional
from collections import Counter


def normalize_duo_account(
    account: Dict[str, Any],
    users: List[Dict[str, Any]],
    phones: List[Dict[str, Any]],
    groups: List[Dict[str, Any]],
    integrations: List[Dict[str, Any]],
    webauthn: List[Dict[str, Any]],
    settings: Dict[str, Any],
    info: Dict[str, Any],
    auth_logs: List[Dict[str, Any]],
    telephony_logs: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Normalize Duo account data into snapshot record.

    Args:
        account: Account metadata from list_accounts
        users: List of users for this account
        phones: List of phones/devices
        groups: List of groups
        integrations: List of integrations
        webauthn: List of WebAuthn credentials
        settings: Account settings
        info: Account info/summary
        auth_logs: Recent authentication logs
        telephony_logs: Recent telephony logs

    Returns:
        Normalized dictionary matching duo_snapshot schema.
    """
    account_id = account.get('account_id', '')
    organization_name = account.get('name', '')

    # User counts
    user_count = len(users)
    admin_count = _count_admins(users)
    enrollment_pct = _calculate_enrollment_pct(users)
    last_login = _get_most_recent_login(users)

    # Resource counts
    phone_count = len(phones)
    group_count = len(groups)
    integration_count = len(integrations)
    webauthn_count = len(webauthn)

    # Auth metrics
    auth_volume = len(auth_logs)
    failed_auth_pct = _calculate_failed_auth_pct(auth_logs)
    peak_usage = _calculate_peak_usage(auth_logs)
    last_activity = _get_last_activity(auth_logs)

    # Settings-based fields
    auth_methods = _extract_auth_methods(settings)
    directory_sync = _has_directory_sync(settings)

    # Telephony
    telephony_credits = _calculate_telephony_credits(telephony_logs)

    # Account metadata
    status = _determine_status(account, info)
    account_type = account.get('edition', info.get('edition', ''))

    return {
        'account_id': account_id,
        'organization_name': organization_name,
        'user_count': user_count,
        'admin_count': admin_count,
        'integration_count': integration_count,
        'phone_count': phone_count,
        'status': status,
        'last_activity': last_activity,
        'group_count': group_count,
        'webauthn_count': webauthn_count,
        'last_login': last_login,
        'enrollment_pct': enrollment_pct,
        'auth_methods': auth_methods,
        'directory_sync': directory_sync,
        'telephony_credits': telephony_credits,
        'auth_volume': auth_volume,
        'failed_auth_pct': failed_auth_pct,
        'peak_usage': peak_usage,
        'account_type': account_type
    }


def _count_admins(users: List[Dict[str, Any]]) -> int:
    """Count users with admin privileges.

    Duo users have an 'is_admin' or 'role' field indicating admin status.
    """
    count = 0
    for user in users:
        # Check is_admin flag
        if user.get('is_admin'):
            count += 1
        # Also check for admin role
        elif user.get('role') in ('admin', 'owner'):
            count += 1
    return count


def _calculate_enrollment_pct(users: List[Dict[str, Any]]) -> Optional[Decimal]:
    """Calculate percentage of users who are enrolled.

    Enrolled users have completed Duo setup (have phones, tokens, etc).
    """
    if not users:
        return None

    enrolled_count = 0
    for user in users:
        # Check status field - 'active' or 'enrolled' indicates enrollment
        status = user.get('status', '')
        if status in ('active', 'enrolled'):
            enrolled_count += 1
        # Also check is_enrolled flag if present
        elif user.get('is_enrolled'):
            enrolled_count += 1

    pct = (enrolled_count / len(users)) * 100
    return Decimal(str(round(pct, 2)))


def _get_most_recent_login(users: List[Dict[str, Any]]) -> Optional[datetime]:
    """Get the most recent last_login timestamp across all users."""
    most_recent = None

    for user in users:
        last_login = user.get('last_login')
        if last_login:
            # Duo returns epoch seconds
            try:
                login_dt = datetime.fromtimestamp(int(last_login))
                if most_recent is None or login_dt > most_recent:
                    most_recent = login_dt
            except (ValueError, TypeError):
                pass

    return most_recent


def _calculate_failed_auth_pct(auth_logs: List[Dict[str, Any]]) -> Optional[Decimal]:
    """Calculate percentage of failed authentications."""
    if not auth_logs:
        return None

    failed_count = 0
    for log in auth_logs:
        result = log.get('result', '')
        if result in ('denied', 'failure', 'fraud'):
            failed_count += 1

    pct = (failed_count / len(auth_logs)) * 100
    return Decimal(str(round(pct, 2)))


def _calculate_peak_usage(auth_logs: List[Dict[str, Any]]) -> Optional[str]:
    """Determine peak usage hour from auth logs.

    Returns the hour (0-23) with most authentication activity.
    """
    if not auth_logs:
        return None

    hour_counts = Counter()

    for log in auth_logs:
        timestamp = log.get('timestamp') or log.get('isotimestamp')
        if timestamp:
            try:
                # Try epoch seconds first
                if isinstance(timestamp, (int, float)):
                    dt = datetime.fromtimestamp(timestamp)
                else:
                    # Try ISO format
                    dt = datetime.fromisoformat(str(timestamp).replace('Z', '+00:00'))
                hour_counts[dt.hour] += 1
            except (ValueError, TypeError):
                pass

    if not hour_counts:
        return None

    peak_hour = hour_counts.most_common(1)[0][0]
    # Format as readable time range
    end_hour = (peak_hour + 1) % 24
    return f"{peak_hour:02d}:00-{end_hour:02d}:00"


def _get_last_activity(auth_logs: List[Dict[str, Any]]) -> Optional[datetime]:
    """Get the most recent authentication timestamp."""
    if not auth_logs:
        return None

    most_recent = None

    for log in auth_logs:
        timestamp = log.get('timestamp') or log.get('isotimestamp')
        if timestamp:
            try:
                if isinstance(timestamp, (int, float)):
                    dt = datetime.fromtimestamp(timestamp)
                else:
                    dt = datetime.fromisoformat(str(timestamp).replace('Z', '+00:00'))

                if most_recent is None or dt > most_recent:
                    most_recent = dt
            except (ValueError, TypeError):
                pass

    return most_recent


def _extract_auth_methods(settings: Dict[str, Any]) -> Optional[List[str]]:
    """Extract enabled authentication methods from settings."""
    methods = []

    # Check common auth method settings
    if settings.get('push_enabled', True):
        methods.append('push')
    if settings.get('sms_enabled', True):
        methods.append('sms')
    if settings.get('voice_enabled', True):
        methods.append('voice')
    if settings.get('u2f_enabled') or settings.get('webauthn_enabled'):
        methods.append('webauthn')
    if settings.get('mobile_otp_enabled', True):
        methods.append('mobile_otp')

    # If no specific settings found, return common defaults
    if not methods and settings:
        methods = ['push', 'sms', 'voice', 'mobile_otp']

    return methods if methods else None


def _has_directory_sync(settings: Dict[str, Any]) -> Optional[bool]:
    """Check if directory sync is enabled."""
    # Check for AD sync or LDAP sync settings
    if settings.get('ad_sync_enabled'):
        return True
    if settings.get('directory_sync'):
        return True
    if settings.get('ldap_enabled'):
        return True

    # Check for Azure AD or other directory integrations
    if settings.get('azure_ad_enabled'):
        return True

    return False if settings else None


def _calculate_telephony_credits(telephony_logs: List[Dict[str, Any]]) -> Optional[int]:
    """Calculate telephony credits used from logs.

    Note: This represents credits consumed in the log period, not remaining balance.
    """
    if not telephony_logs:
        return 0

    # Sum up credits used in logs
    total_credits = 0
    for log in telephony_logs:
        credits = log.get('credits', 0)
        try:
            total_credits += int(credits)
        except (ValueError, TypeError):
            pass

    return total_credits


def _determine_status(account: Dict[str, Any], info: Dict[str, Any]) -> str:
    """Determine account status.

    Returns: 'active', 'inactive', 'suspended', or 'unknown'
    """
    # Check account-level status
    status = account.get('status', '').lower()
    if status:
        if status in ('active', 'enabled'):
            return 'active'
        elif status in ('inactive', 'disabled'):
            return 'inactive'
        elif status == 'suspended':
            return 'suspended'

    # Check info-level status
    info_status = info.get('status', '').lower()
    if info_status:
        if info_status in ('active', 'enabled'):
            return 'active'
        elif info_status in ('inactive', 'disabled'):
            return 'inactive'

    # Default to active if no explicit status
    return 'active'


def normalize_duo_users(
    account_id: str,
    organization_name: str,
    users: List[Dict[str, Any]],
    phones: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Normalize Duo user data into user snapshot records.

    Args:
        account_id: Duo account ID
        organization_name: Account/organization name
        users: List of users from Duo API
        phones: List of phones for this account (to map primary phone)

    Returns:
        List of normalized user dictionaries matching duo_user_snapshot schema.
    """
    # Build phone lookup by user_id
    phone_by_user: Dict[str, str] = {}
    for phone in phones:
        # Get the users associated with this phone
        phone_users = phone.get('users', [])
        phone_number = phone.get('number', '')
        for pu in phone_users:
            user_id = pu.get('user_id', '')
            if user_id and phone_number:
                # Only store first phone found (primary)
                if user_id not in phone_by_user:
                    phone_by_user[user_id] = phone_number

    results = []
    for user in users:
        user_id = user.get('user_id', '')
        if not user_id:
            continue

        # Parse last_login timestamp
        last_login = None
        last_login_ts = user.get('last_login')
        if last_login_ts:
            try:
                last_login = datetime.fromtimestamp(int(last_login_ts))
            except (ValueError, TypeError):
                pass

        # Determine enrollment status
        status = user.get('status', '')
        is_enrolled = status in ('active', 'enrolled') or user.get('is_enrolled', False)

        results.append({
            'account_id': account_id,
            'organization_name': organization_name,
            'user_id': user_id,
            'username': user.get('username', ''),
            'full_name': user.get('realname', ''),
            'email': user.get('email', ''),
            'status': status,
            'last_login': last_login,
            'phone': phone_by_user.get(user_id, ''),
            'is_enrolled': is_enrolled,
        })

    return results

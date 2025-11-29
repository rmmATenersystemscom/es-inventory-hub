"""M365 data normalization and license filtering."""

import csv
import json
import os
from typing import Dict, Any, List, Set, Optional
from pathlib import Path

from common.logging import get_logger

logger = get_logger(__name__)

# Config file paths
CONFIG_DIR = Path(__file__).parent / 'config'
SKU_MAPPING_FILE = CONFIG_DIR / 'sku_mapping.csv'
EXCLUDED_LICENSES_FILE = CONFIG_DIR / 'excluded_licenses.json'

# Cached data
_sku_mapping: Optional[Dict[str, str]] = None
_excluded_licenses: Optional[Set[str]] = None


def load_sku_mapping() -> Dict[str, str]:
    """Load SKU GUID to product name mapping from CSV.

    Returns:
        Dict mapping GUID -> Product_Display_Name
    """
    global _sku_mapping

    if _sku_mapping is not None:
        return _sku_mapping

    _sku_mapping = {}

    if not SKU_MAPPING_FILE.exists():
        logger.warning(f"SKU mapping file not found: {SKU_MAPPING_FILE}")
        return _sku_mapping

    try:
        with open(SKU_MAPPING_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                guid = row.get('GUID', '').strip().lower()
                name = row.get('Product_Display_Name', '').strip()
                if guid and name:
                    _sku_mapping[guid] = name

        logger.info(f"Loaded {len(_sku_mapping)} SKU mappings")
    except Exception as e:
        logger.error(f"Failed to load SKU mapping: {e}")

    return _sku_mapping


def load_excluded_licenses() -> Set[str]:
    """Load excluded license names from JSON config.

    Returns:
        Set of excluded license product names
    """
    global _excluded_licenses

    if _excluded_licenses is not None:
        return _excluded_licenses

    _excluded_licenses = set()

    if not EXCLUDED_LICENSES_FILE.exists():
        logger.warning(f"Excluded licenses file not found: {EXCLUDED_LICENSES_FILE}")
        return _excluded_licenses

    try:
        with open(EXCLUDED_LICENSES_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            licenses = data.get('excluded_licenses', [])
            _excluded_licenses = set(licenses)

        logger.info(f"Loaded {len(_excluded_licenses)} excluded license types")
    except Exception as e:
        logger.error(f"Failed to load excluded licenses: {e}")

    return _excluded_licenses


def get_license_names(assigned_licenses: List[Dict[str, Any]],
                      sku_mapping: Dict[str, str]) -> List[str]:
    """Convert license SKU IDs to product names.

    Args:
        assigned_licenses: List of license dicts with 'skuId'
        sku_mapping: GUID to name mapping

    Returns:
        List of product display names
    """
    names = []
    for license_info in assigned_licenses:
        sku_id = license_info.get('skuId', '').lower()
        if sku_id:
            name = sku_mapping.get(sku_id, sku_id)  # Fallback to GUID if not mapped
            names.append(name)
    return names


def is_user_counted(user: Dict[str, Any], sku_mapping: Dict[str, str],
                    excluded_licenses: Set[str]) -> bool:
    """Determine if a user should be counted based on license filtering.

    Two-stage filtering:
    1. Exclude users with no licenses (empty assignedLicenses)
    2. Exclude users where ALL licenses are in the excluded list

    Args:
        user: User dict with 'assignedLicenses'
        sku_mapping: GUID to name mapping
        excluded_licenses: Set of excluded license names

    Returns:
        True if user should be counted, False otherwise
    """
    assigned_licenses = user.get('assignedLicenses', [])

    # Stage 1: Exclude users with no licenses
    if not assigned_licenses:
        return False

    # Get license names for this user
    license_names = get_license_names(assigned_licenses, sku_mapping)

    if not license_names:
        return False

    # Stage 2: Exclude users where ALL licenses are excluded types
    # User is counted if they have at least one non-excluded license
    for name in license_names:
        if name not in excluded_licenses:
            return True

    # All licenses are excluded types
    return False


def count_filtered_users(users: List[Dict[str, Any]]) -> int:
    """Count users after applying license filtering.

    Args:
        users: List of user dicts from Graph API

    Returns:
        Count of users that pass the filter
    """
    sku_mapping = load_sku_mapping()
    excluded_licenses = load_excluded_licenses()

    count = 0
    for user in users:
        if is_user_counted(user, sku_mapping, excluded_licenses):
            count += 1

    return count


def get_filtered_users_with_details(users: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Get filtered users with their details (username, display_name, licenses).

    Args:
        users: List of user dicts from Graph API

    Returns:
        List of user detail dicts for users that pass the filter
    """
    sku_mapping = load_sku_mapping()
    excluded_licenses = load_excluded_licenses()

    filtered_users = []
    for user in users:
        if is_user_counted(user, sku_mapping, excluded_licenses):
            # Get license names
            assigned_licenses = user.get('assignedLicenses', [])
            license_names = get_license_names(assigned_licenses, sku_mapping)

            filtered_users.append({
                'username': user.get('userPrincipalName', ''),
                'display_name': user.get('displayName', ''),
                'licenses': ', '.join(license_names)
            })

    return filtered_users


def normalize_m365_tenant(tenant: Dict[str, str], users: List[Dict[str, Any]],
                          organization: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Normalize M365 tenant data into snapshot record.

    Args:
        tenant: Tenant configuration dict
        users: List of users from Graph API
        organization: Optional organization info from Graph API

    Returns:
        Normalized dictionary with tenant summary and user details
    """
    # Get organization name (prefer from API, fallback to config name)
    org_name = tenant['name']
    if organization:
        org_name = organization.get('displayName', org_name)

    # Get filtered users with details
    filtered_users = get_filtered_users_with_details(users)
    user_count = len(filtered_users)

    return {
        'tenant_id': tenant['tenant_id'],
        'organization_name': org_name,
        'user_count': user_count,
        'users': filtered_users  # List of user detail dicts
    }

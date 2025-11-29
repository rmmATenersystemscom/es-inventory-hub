"""Veeam data normalization."""

from typing import Dict, Any, List
from common.logging import get_logger

logger = get_logger(__name__)

# Bytes to GB conversion factor
BYTES_TO_GB = 1024 ** 3


def extract_cloud_usage(usage_data: List[Dict[str, Any]]) -> Dict[str, float]:
    """Extract cloud storage usage by company UID.

    Args:
        usage_data: List of usage records from /organizations/companies/usage

    Returns:
        Dict mapping companyUid -> usage in GB
    """
    usage_by_uid: Dict[str, float] = {}

    for record in usage_data:
        company_uid = record.get('companyUid')
        if not company_uid:
            continue

        # Find CloudTotalUsage counter
        for counter in record.get('counters', []):
            if counter.get('type') == 'CloudTotalUsage':
                usage_bytes = counter.get('value', 0) or 0
                usage_by_uid[company_uid] = usage_bytes / BYTES_TO_GB
                break

    logger.info(f"Extracted cloud usage for {len(usage_by_uid)} companies")
    return usage_by_uid


def extract_quota_data(quota_data: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    """Extract storage quota by company UID.

    Args:
        quota_data: List of quota records from /organizations/companies/sites/backupResources/usage

    Returns:
        Dict mapping companyUid -> {quota_gb, used_quota_gb}
    """
    quota_by_uid: Dict[str, Dict[str, float]] = {}

    for record in quota_data:
        company_uid = record.get('companyUid')
        if not company_uid:
            continue

        quota_bytes = record.get('storageQuota', 0) or 0
        used_bytes = record.get('usedStorageQuota', 0) or 0

        quota_by_uid[company_uid] = {
            'quota_gb': quota_bytes / BYTES_TO_GB,
            'used_quota_gb': used_bytes / BYTES_TO_GB,
        }

    logger.info(f"Extracted quota data for {len(quota_by_uid)} companies")
    return quota_by_uid


def normalize_veeam_data(
    companies: List[Dict[str, Any]],
    usage_data: List[Dict[str, Any]],
    quota_data: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Normalize all Veeam data into organization usage records.

    Args:
        companies: List of companies from VSPC
        usage_data: List of cloud usage records from VSPC
        quota_data: List of quota records from VSPC

    Returns:
        List of normalized organization usage dicts
    """
    # Extract usage and quota by company UID
    usage_by_uid = extract_cloud_usage(usage_data)
    quota_by_uid = extract_quota_data(quota_data)

    results = []
    for company in companies:
        company_uid = company.get('instanceUid', '')
        company_name = company.get('name', '')

        # Get cloud usage
        storage_gb = usage_by_uid.get(company_uid, 0)

        # Get quota
        quota_info = quota_by_uid.get(company_uid, {})
        quota_gb = quota_info.get('quota_gb', 0)

        # Calculate usage percentage
        if quota_gb > 0:
            usage_pct = (storage_gb / quota_gb) * 100
        else:
            usage_pct = 0

        # Only include companies with storage or quota data
        if storage_gb > 0 or quota_gb > 0:
            results.append({
                'company_uid': company_uid,
                'organization_name': company_name,
                'storage_gb': round(storage_gb, 2),
                'quota_gb': round(quota_gb, 2),
                'usage_pct': round(usage_pct, 1),
            })

    # Sort by storage descending
    results.sort(key=lambda x: x['storage_gb'], reverse=True)

    logger.info(f"Normalized {len(results)} organizations with Veeam data")
    return results

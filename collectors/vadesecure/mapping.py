"""VadeSecure data normalization and mapping."""

from typing import Dict, Any, Optional
from datetime import datetime

# VadeSecure license state codes
LICENSE_STATE_MAP = {
    2: 'active',
    3: 'expired',
}

# VadeSecure product type codes
PRODUCT_TYPE_MAP = {
    9: 'M365',
    # Add more product types as discovered
}


def normalize_vadesecure_customer(raw_customer: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a raw VadeSecure customer record for database insertion.

    VadeSecure API response structure:
    {
        "id": "ZY8NtfyNcEMxnKfnNVganA",  # Customer ID (string)
        "brand": "Company Name",           # Customer/company name
        "domain": "company.onmicrosoft.com",
        "mail": "admin@company.com",
        "ctime": "2022-08-19T16:31:29.325Z",  # Created date (ISO format)
        "firstname": "Rene",
        "lastname": "Miller",
        "phone": "555-1234",
        "address": "123 Main St",
        "city": "Hammond",
        "state": "Louisiana",
        "migrated": true,
        "licenses": [{
            "id": 32332,                   # License ID (integer)
            "tenantID": "guid...",         # M365 tenant ID
            "product": 9,                  # Product type code (integer)
            "state": 2,                    # License state: 2=active, 3=expired
            "startDate": 1660926748240,    # Epoch milliseconds
            "usage": 17,                   # Actual user count (USE THIS)
            "userCount": 0,                # Often 0 - unreliable
        }]
    }

    Args:
        raw_customer: Raw customer data from VadeSecure API

    Returns:
        dict: Normalized customer data for vadesecure_snapshot table
    """
    # Extract customer ID
    customer_id = raw_customer.get('id', '')

    # Extract customer name - VadeSecure uses 'brand' for company name
    customer_name = (
        raw_customer.get('brand') or
        raw_customer.get('name') or
        raw_customer.get('customerName') or
        ''
    )

    # Extract domain/company domain
    company_domain = (
        raw_customer.get('domain') or
        raw_customer.get('primaryDomain') or
        ''
    )

    # Extract contact email - VadeSecure uses 'mail'
    contact_email = (
        raw_customer.get('mail') or
        raw_customer.get('email') or
        raw_customer.get('contactEmail') or
        ''
    )

    # Extract license information from licenses array
    licenses = raw_customer.get('licenses', [])
    license_data = licenses[0] if licenses else {}

    # License ID is an integer
    license_id = license_data.get('id')

    # Product type is an integer code
    product_code = license_data.get('product')
    product_type = PRODUCT_TYPE_MAP.get(product_code, str(product_code) if product_code else None)

    # License state is an integer code (2=active, 3=expired)
    state_code = license_data.get('state')
    license_status = LICENSE_STATE_MAP.get(state_code, f'unknown-{state_code}' if state_code else None)

    # Parse dates - VadeSecure uses epoch milliseconds
    license_start_date = _parse_epoch_ms(license_data.get('startDate'))
    license_end_date = _parse_epoch_ms(license_data.get('endDate'))

    # Tenant ID is in the license object
    tenant_id = license_data.get('tenantID') or raw_customer.get('tenantId') or ''

    # Usage count - use 'usage' field, NOT 'userCount' (often shows 0)
    usage_count = license_data.get('usage', 0)
    if not isinstance(usage_count, int):
        try:
            usage_count = int(usage_count)
        except (ValueError, TypeError):
            usage_count = 0

    # Contact/location info
    migrated = raw_customer.get('migrated')
    created_date = _parse_iso_datetime(raw_customer.get('ctime'))

    # Build contact name from firstname + lastname
    firstname = _safe_strip(raw_customer.get('firstname')) or ''
    lastname = _safe_strip(raw_customer.get('lastname')) or ''
    contact_name = f"{firstname} {lastname}".strip() or None

    phone = _safe_strip(raw_customer.get('phone'))
    address = _safe_strip(raw_customer.get('address'))
    city = _safe_strip(raw_customer.get('city'))
    state = _safe_strip(raw_customer.get('state'))

    return {
        'customer_id': str(customer_id) if customer_id else None,
        'customer_name': _safe_strip(customer_name),
        'company_domain': _safe_strip(company_domain),
        'contact_email': _safe_strip(contact_email),
        'license_id': str(license_id) if license_id else None,
        'product_type': product_type,
        'license_status': license_status,
        'license_start_date': license_start_date,
        'license_end_date': license_end_date,
        'tenant_id': _safe_strip(tenant_id),
        'usage_count': usage_count,
        'migrated': migrated,
        'created_date': created_date,
        'contact_name': contact_name,
        'phone': phone,
        'address': address,
        'city': city,
        'state': state,
        'raw': raw_customer  # Store raw data for debugging
    }


def _safe_strip(value: Any) -> Optional[str]:
    """Safely strip whitespace from a value, handling non-strings."""
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped if stripped else None
    return str(value)


def _parse_epoch_ms(epoch_ms: Any) -> Optional[datetime]:
    """Parse epoch milliseconds to datetime.date."""
    if not epoch_ms:
        return None
    try:
        # Convert milliseconds to seconds
        epoch_seconds = int(epoch_ms) / 1000
        return datetime.fromtimestamp(epoch_seconds).date()
    except (ValueError, TypeError, OSError):
        return None


def _parse_iso_datetime(iso_str: Any) -> Optional[datetime]:
    """Parse ISO datetime string to datetime object."""
    if not iso_str or not isinstance(iso_str, str):
        return None
    try:
        # Handle ISO format: "2022-08-19T16:31:29.325Z"
        # Remove trailing Z and parse
        clean_str = iso_str.replace('Z', '+00:00')
        return datetime.fromisoformat(clean_str)
    except (ValueError, TypeError):
        return None

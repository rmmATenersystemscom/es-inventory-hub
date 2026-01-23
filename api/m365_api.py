"""
M365 API Endpoints

Provides REST API endpoints for:
1. M365 usage changes - Compare user/license data between two dates
2. Available dates - List dates with M365 snapshot data
3. Summary - Organization-level user counts (ES Users vs M365 Licensed Users)
4. Users - Per-user details for a specific organization
5. Export - Full dataset export (CSV/JSON)
"""

import csv
import io
import re
import sys
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional
import time

from flask import Blueprint, jsonify, request, Response
from sqlalchemy import text

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Create Blueprint for M365 API
m365_api = Blueprint('m365_api', __name__)

# Email license patterns - licenses that provide an Exchange mailbox
EMAIL_LICENSE_INCLUDE_PATTERNS = [
    r'^Microsoft 365 Business',      # Basic, Standard, Premium
    r'^Microsoft 365 E\d',           # E3, E5, etc.
    r'^Microsoft 365 F\d',           # F1, F3, etc.
    r'^Office 365 E\d',              # E1, E3, E5, etc.
    r'^Office 365 F\d',              # F3, etc.
    r'^Exchange Online \(Plan',      # Plan 1, Plan 2
    r'^Exchange Online Kiosk',
    r'^Exchange Online Essentials',
]

# Patterns that should NOT count as email licenses (add-ons, not mailboxes)
EMAIL_LICENSE_EXCLUDE_PATTERNS = [
    r'Archiving',
    r'Protection',
]


def has_email_license(licenses_str: str) -> bool:
    """
    Determine if a user has at least one license that provides an Exchange mailbox.

    Args:
        licenses_str: Comma-separated list of license names

    Returns:
        True if user has an email-capable license, False otherwise
    """
    if not licenses_str:
        return False

    licenses = [lic.strip() for lic in licenses_str.split(',') if lic.strip()]

    for license_name in licenses:
        # Check if license matches any exclude pattern first
        is_excluded = any(
            re.search(pattern, license_name, re.IGNORECASE)
            for pattern in EMAIL_LICENSE_EXCLUDE_PATTERNS
        )
        if is_excluded:
            continue

        # Check if license matches any include pattern
        is_email_license = any(
            re.search(pattern, license_name, re.IGNORECASE)
            for pattern in EMAIL_LICENSE_INCLUDE_PATTERNS
        )
        if is_email_license:
            return True

    return False


def validate_date(date_str: str) -> Optional[date]:
    """
    Validate and parse date string in YYYY-MM-DD format.

    Args:
        date_str: Date string to validate

    Returns:
        date object if valid, None otherwise
    """
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return None


def check_m365_date_availability(session, check_date: date) -> bool:
    """
    Check if M365 data exists for a given date.

    Args:
        session: Database session
        check_date: Date to check

    Returns:
        bool: True if data exists, False otherwise
    """
    result = session.execute(text("""
        SELECT COUNT(*)
        FROM m365_user_snapshot
        WHERE snapshot_date = :check_date
    """), {'check_date': check_date}).scalar()

    return result > 0


def get_m365_available_dates(session, start_date: date, end_date: date) -> List[date]:
    """
    Get list of dates with M365 data in a range.

    Args:
        session: Database session
        start_date: Start of range
        end_date: End of range

    Returns:
        List of dates with data
    """
    results = session.execute(text("""
        SELECT DISTINCT snapshot_date
        FROM m365_user_snapshot
        WHERE snapshot_date BETWEEN :start_date AND :end_date
        ORDER BY snapshot_date DESC
    """), {
        'start_date': start_date,
        'end_date': end_date
    }).fetchall()

    return [row[0] for row in results]


def find_m365_change_dates(session, changes_by_type: Dict[str, List[Dict]],
                           start_date: date, end_date: date) -> Dict[str, str]:
    """
    Find the specific date when each user change occurred.

    Args:
        session: Database session
        changes_by_type: Dict mapping change_type to list of change details
        start_date: Start of date range
        end_date: End of date range

    Returns:
        Dict mapping (username, org_name) tuple string to change_date
    """
    change_dates = {}

    # Find first appearance date for added users
    if changes_by_type.get('user_added'):
        for change in changes_by_type['user_added']:
            username = change['user_principal_name']
            org_name = change['organization_name']
            query = text("""
                SELECT MIN(snapshot_date) as first_seen
                FROM m365_user_snapshot
                WHERE username = :username
                  AND organization_name = :org_name
                  AND snapshot_date > :start_date
                  AND snapshot_date <= :end_date
            """)
            result = session.execute(query, {
                'username': username,
                'org_name': org_name,
                'start_date': start_date,
                'end_date': end_date
            }).fetchone()
            if result and result.first_seen:
                key = f"{username}|{org_name}"
                change_dates[key] = result.first_seen.strftime('%Y-%m-%d')

    # Find license change dates
    for change_type in ['license_added', 'license_removed']:
        if changes_by_type.get(change_type):
            for change in changes_by_type[change_type]:
                username = change['user_principal_name']
                org_name = change['organization_name']
                new_licenses = change.get('to_licenses', '')
                query = text("""
                    SELECT MIN(snapshot_date) as change_date
                    FROM m365_user_snapshot
                    WHERE username = :username
                      AND organization_name = :org_name
                      AND COALESCE(licenses, '') = :new_licenses
                      AND snapshot_date > :start_date
                      AND snapshot_date <= :end_date
                """)
                result = session.execute(query, {
                    'username': username,
                    'org_name': org_name,
                    'new_licenses': new_licenses,
                    'start_date': start_date,
                    'end_date': end_date
                }).fetchone()
                if result and result.change_date:
                    key = f"{username}|{org_name}"
                    change_dates[key] = result.change_date.strftime('%Y-%m-%d')

    return change_dates


@m365_api.route('/api/m365/usage-changes', methods=['GET'])
def get_m365_usage_changes():
    """
    Compare M365 user/license data between two dates.

    Identifies users that were:
    - user_added: Present in end_date but not start_date
    - user_removed: Present in start_date but not end_date
    - license_added: User exists in both, but has new licenses
    - license_removed: User exists in both, but lost licenses

    Query Parameters:
        start_date (required): Baseline date in YYYY-MM-DD format
        end_date (required): Comparison date in YYYY-MM-DD format
        detail_level (optional): "summary" (default) or "full"
        organization_name (optional): Filter by specific organization name

    Returns:
        JSON response with change summary and optionally user details
    """
    from api.api_server import get_session

    start_time = time.time()

    # Parse parameters
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    detail_level = request.args.get('detail_level', 'summary')
    org_filter = request.args.get('organization_name')

    # Validate required parameters
    if not start_date_str or not end_date_str:
        return jsonify({
            "success": False,
            "error": {
                "code": "MISSING_PARAMETERS",
                "message": "Both start_date and end_date are required (YYYY-MM-DD format)",
                "status": 400
            }
        }), 400

    # Validate date formats
    start_date = validate_date(start_date_str)
    end_date = validate_date(end_date_str)

    if not start_date:
        return jsonify({
            "success": False,
            "error": {
                "code": "INVALID_DATE",
                "message": f"Invalid start_date format: {start_date_str}. Use YYYY-MM-DD",
                "status": 400
            }
        }), 400

    if not end_date:
        return jsonify({
            "success": False,
            "error": {
                "code": "INVALID_DATE",
                "message": f"Invalid end_date format: {end_date_str}. Use YYYY-MM-DD",
                "status": 400
            }
        }), 400

    # Validate date order
    if start_date >= end_date:
        return jsonify({
            "success": False,
            "error": {
                "code": "INVALID_DATE_RANGE",
                "message": "start_date must be before end_date",
                "status": 400
            }
        }), 400

    # Validate detail_level
    if detail_level not in ('summary', 'full'):
        return jsonify({
            "success": False,
            "error": {
                "code": "INVALID_PARAMETER",
                "message": "detail_level must be 'summary' or 'full'",
                "status": 400
            }
        }), 400

    with get_session() as session:
        # Check data availability for both dates
        if not check_m365_date_availability(session, start_date):
            return jsonify({
                "success": False,
                "error": {
                    "code": "NO_DATA",
                    "message": f"No M365 data available for start_date: {start_date_str}",
                    "status": 404
                }
            }), 404

        if not check_m365_date_availability(session, end_date):
            return jsonify({
                "success": False,
                "error": {
                    "code": "NO_DATA",
                    "message": f"No M365 data available for end_date: {end_date_str}",
                    "status": 404
                }
            }), 404

        # Build the comparison query
        org_filter_clause = ""
        params = {
            'start_date': start_date,
            'end_date': end_date
        }

        if org_filter:
            org_filter_clause = "AND (s.organization_name ILIKE :org_filter OR e.organization_name ILIKE :org_filter)"
            params['org_filter'] = f'%{org_filter}%'

        # Main comparison query using FULL OUTER JOIN
        query = text(f"""
            WITH start_snap AS (
                SELECT
                    tenant_id,
                    organization_name,
                    username,
                    display_name,
                    COALESCE(licenses, '') as licenses
                FROM m365_user_snapshot
                WHERE snapshot_date = :start_date
            ),
            end_snap AS (
                SELECT
                    tenant_id,
                    organization_name,
                    username,
                    display_name,
                    COALESCE(licenses, '') as licenses
                FROM m365_user_snapshot
                WHERE snapshot_date = :end_date
            )
            SELECT
                COALESCE(s.username, e.username) as username,
                COALESCE(s.organization_name, e.organization_name) as organization_name,
                -- Start date values
                s.tenant_id as start_tenant_id,
                s.display_name as start_display_name,
                s.licenses as start_licenses,
                -- End date values
                e.tenant_id as end_tenant_id,
                e.display_name as end_display_name,
                e.licenses as end_licenses,
                -- Change classification
                CASE
                    WHEN s.username IS NULL THEN 'user_added'
                    WHEN e.username IS NULL THEN 'user_removed'
                    WHEN s.licenses != e.licenses THEN
                        CASE
                            WHEN LENGTH(e.licenses) > LENGTH(s.licenses) THEN 'license_added'
                            WHEN LENGTH(e.licenses) < LENGTH(s.licenses) THEN 'license_removed'
                            ELSE 'license_changed'
                        END
                    ELSE 'unchanged'
                END as change_type
            FROM start_snap s
            FULL OUTER JOIN end_snap e
                ON s.username = e.username AND s.organization_name = e.organization_name
            WHERE 1=1 {org_filter_clause}
            ORDER BY
                CASE
                    WHEN s.username IS NULL THEN 1
                    WHEN e.username IS NULL THEN 2
                    WHEN s.licenses != e.licenses THEN 3
                    ELSE 4
                END,
                COALESCE(e.organization_name, s.organization_name),
                COALESCE(e.username, s.username)
        """)

        results = session.execute(query, params).fetchall()

        # Process results
        summary = {
            'user_added': 0,
            'user_removed': 0,
            'license_added': 0,
            'license_removed': 0,
            'license_changed': 0,
            'unchanged': 0
        }

        by_organization = {}
        changes = {
            'user_added': [],
            'user_removed': [],
            'license_added': [],
            'license_removed': []
        }

        # Track totals
        start_total_users = 0
        end_total_users = 0
        start_total_licenses = 0
        end_total_licenses = 0

        for row in results:
            change_type = row.change_type
            summary[change_type] += 1

            org_name = row.organization_name

            # Count licenses (comma-separated)
            start_license_count = len([l for l in (row.start_licenses or '').split(',') if l.strip()])
            end_license_count = len([l for l in (row.end_licenses or '').split(',') if l.strip()])

            # Track totals
            if row.start_licenses is not None:
                start_total_users += 1
                start_total_licenses += start_license_count
            if row.end_licenses is not None:
                end_total_users += 1
                end_total_licenses += end_license_count

            # Build per-organization breakdown
            if org_name not in by_organization:
                by_organization[org_name] = {
                    'start_user_count': 0,
                    'end_user_count': 0,
                    'user_change': 0,
                    'changes': {
                        'user_added': 0,
                        'user_removed': 0,
                        'license_added': 0,
                        'license_removed': 0
                    }
                }

            org_data = by_organization[org_name]
            if change_type == 'user_added':
                org_data['end_user_count'] += 1
                org_data['changes']['user_added'] += 1
            elif change_type == 'user_removed':
                org_data['start_user_count'] += 1
                org_data['changes']['user_removed'] += 1
            elif change_type in ('license_added', 'license_removed', 'license_changed'):
                org_data['start_user_count'] += 1
                org_data['end_user_count'] += 1
                if change_type in org_data['changes']:
                    org_data['changes'][change_type] += 1
            else:  # unchanged
                org_data['start_user_count'] += 1
                org_data['end_user_count'] += 1

            # Collect user details for full mode
            if detail_level == 'full' and change_type != 'unchanged':
                user_detail = {
                    'user_principal_name': row.username,
                    'organization_name': org_name,
                    'display_name': row.end_display_name or row.start_display_name
                }

                if change_type == 'user_added':
                    user_detail['licenses'] = row.end_licenses
                    changes['user_added'].append(user_detail)
                elif change_type == 'user_removed':
                    user_detail['licenses'] = row.start_licenses
                    user_detail['last_seen_date'] = start_date_str
                    changes['user_removed'].append(user_detail)
                elif change_type in ('license_added', 'license_removed', 'license_changed'):
                    user_detail['from_licenses'] = row.start_licenses
                    user_detail['to_licenses'] = row.end_licenses
                    # Determine which licenses were added/removed
                    start_set = set(l.strip() for l in (row.start_licenses or '').split(',') if l.strip())
                    end_set = set(l.strip() for l in (row.end_licenses or '').split(',') if l.strip())
                    user_detail['licenses_added'] = list(end_set - start_set)
                    user_detail['licenses_removed'] = list(start_set - end_set)

                    if change_type == 'license_added':
                        changes['license_added'].append(user_detail)
                    elif change_type == 'license_removed':
                        changes['license_removed'].append(user_detail)

        # Calculate user_change for each organization
        for org_name, org_data in by_organization.items():
            org_data['user_change'] = org_data['end_user_count'] - org_data['start_user_count']

        # Find specific change dates (only in full mode)
        if detail_level == 'full':
            change_dates = find_m365_change_dates(session, changes, start_date, end_date)

            # Add change_date to each user detail
            for change_type in ['user_added', 'license_added', 'license_removed']:
                for user in changes.get(change_type, []):
                    key = f"{user['user_principal_name']}|{user['organization_name']}"
                    if key in change_dates:
                        user['change_date'] = change_dates[key]

        query_time_ms = int((time.time() - start_time) * 1000)

        # Build response
        response_data = {
            'start_date': start_date_str,
            'end_date': end_date_str,
            'summary': {
                'start_total_users': start_total_users,
                'end_total_users': end_total_users,
                'net_user_change': end_total_users - start_total_users,
                'start_total_licenses': start_total_licenses,
                'end_total_licenses': end_total_licenses,
                'net_license_change': end_total_licenses - start_total_licenses,
                'changes': {
                    'users_added': summary['user_added'],
                    'users_removed': summary['user_removed'],
                    'licenses_added': summary['license_added'],
                    'licenses_removed': summary['license_removed']
                }
            },
            'by_organization': dict(sorted(by_organization.items())),
            'metadata': {
                'vendor_name': 'Microsoft 365',
                'query_time_ms': query_time_ms,
                'detail_level': detail_level,
                'data_retention_note': 'User-level data available for historical snapshots'
            }
        }

        # Add user details in full mode
        if detail_level == 'full':
            response_data['changes'] = changes

        # Add organization filter info if used
        if org_filter:
            response_data['metadata']['organization_filter'] = org_filter

        return jsonify({
            'success': True,
            'data': response_data
        })


@m365_api.route('/api/m365/available-dates', methods=['GET'])
def get_available_dates():
    """
    Get list of dates with M365 snapshot data available.

    Query Parameters:
        days (optional): Number of days to look back (default: 90)

    Returns:
        JSON response with list of available dates in descending order
    """
    from api.api_server import get_session

    days = request.args.get('days', 90, type=int)
    if days < 1 or days > 365:
        days = 90

    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    with get_session() as session:
        available = get_m365_available_dates(session, start_date, end_date)

        return jsonify({
            'success': True,
            'data': {
                'dates': [d.isoformat() for d in available],
                'count': len(available),
                'range': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                }
            }
        })


@m365_api.route('/api/m365/summary', methods=['GET'])
def get_m365_summary():
    """
    Get organization-level summary counts for the M365 dashboard.

    Provides two user counts per organization:
    - es_user_count: Users with a functioning email account (Exchange mailbox)
    - m365_licensed_user_count: All users with any M365 license

    Returns:
        JSON response with organization summaries and totals
    """
    from api.api_server import get_session

    start_time = time.time()

    with get_session() as session:
        # Get the most recent snapshot date
        latest_date_result = session.execute(text("""
            SELECT MAX(snapshot_date) as latest_date
            FROM m365_user_snapshot
        """)).fetchone()

        if not latest_date_result or not latest_date_result.latest_date:
            return jsonify({
                "status": "error",
                "error": "No M365 data available"
            }), 404

        snapshot_date = latest_date_result.latest_date

        # Get all users from the latest snapshot
        results = session.execute(text("""
            SELECT
                organization_name,
                username,
                display_name,
                licenses
            FROM m365_user_snapshot
            WHERE snapshot_date = :snapshot_date
            ORDER BY organization_name, display_name
        """), {'snapshot_date': snapshot_date}).fetchall()

        # Aggregate by organization
        org_data = {}
        for row in results:
            org_name = row.organization_name
            if org_name not in org_data:
                org_data[org_name] = {
                    'organization_name': org_name,
                    'es_user_count': 0,
                    'm365_licensed_user_count': 0
                }

            org_data[org_name]['m365_licensed_user_count'] += 1
            if has_email_license(row.licenses):
                org_data[org_name]['es_user_count'] += 1

        # Sort by organization name and build response
        organizations = sorted(org_data.values(), key=lambda x: x['organization_name'])

        # Calculate totals
        total_es_users = sum(org['es_user_count'] for org in organizations)
        total_m365_users = sum(org['m365_licensed_user_count'] for org in organizations)

        query_time_ms = int((time.time() - start_time) * 1000)

        return jsonify({
            "status": "success",
            "organizations": organizations,
            "totals": {
                "total_organizations": len(organizations),
                "total_es_users": total_es_users,
                "total_m365_licensed_users": total_m365_users
            },
            "last_collected": snapshot_date.isoformat() + "T00:00:00Z",
            "metadata": {
                "query_time_ms": query_time_ms
            }
        })


@m365_api.route('/api/m365/users', methods=['GET'])
def get_m365_users():
    """
    Get detailed user list for a specific organization.

    Query Parameters:
        org (required): Organization name to filter by

    Returns:
        JSON response with user details including has_email_license flag
    """
    from api.api_server import get_session

    org_name = request.args.get('org')

    if not org_name:
        return jsonify({
            "status": "error",
            "error": "Missing required parameter: org"
        }), 400

    with get_session() as session:
        # Get the most recent snapshot date
        latest_date_result = session.execute(text("""
            SELECT MAX(snapshot_date) as latest_date
            FROM m365_user_snapshot
        """)).fetchone()

        if not latest_date_result or not latest_date_result.latest_date:
            return jsonify({
                "status": "error",
                "error": "No M365 data available"
            }), 404

        snapshot_date = latest_date_result.latest_date

        # Get users for the specified organization
        results = session.execute(text("""
            SELECT
                username,
                display_name,
                licenses
            FROM m365_user_snapshot
            WHERE snapshot_date = :snapshot_date
              AND organization_name = :org_name
            ORDER BY display_name
        """), {
            'snapshot_date': snapshot_date,
            'org_name': org_name
        }).fetchall()

        if not results:
            return jsonify({
                "status": "error",
                "error": f"No users found for organization: {org_name}"
            }), 404

        users = []
        for row in results:
            users.append({
                "user_principal_name": row.username,
                "display_name": row.display_name,
                "licenses": row.licenses or "",
                "has_email_license": has_email_license(row.licenses)
            })

        return jsonify({
            "status": "success",
            "organization": org_name,
            "users": users,
            "total_users": len(users)
        })


@m365_api.route('/api/m365/export', methods=['GET'])
def export_m365_data():
    """
    Export full M365 dataset for CSV/Excel export.

    Query Parameters:
        format (optional): 'csv' or 'json' (default: 'json')
        sort (optional): Field to sort by (default: 'organization_name')

    Returns:
        JSON or CSV response with all user data
    """
    from api.api_server import get_session

    export_format = request.args.get('format', 'json').lower()
    sort_field = request.args.get('sort', 'organization_name')

    if export_format not in ('csv', 'json'):
        return jsonify({
            "status": "error",
            "error": "Invalid format. Use 'csv' or 'json'"
        }), 400

    # Validate sort field
    valid_sort_fields = ['organization_name', 'user_principal_name', 'display_name']
    if sort_field not in valid_sort_fields:
        sort_field = 'organization_name'

    with get_session() as session:
        # Get the most recent snapshot date
        latest_date_result = session.execute(text("""
            SELECT MAX(snapshot_date) as latest_date
            FROM m365_user_snapshot
        """)).fetchone()

        if not latest_date_result or not latest_date_result.latest_date:
            if export_format == 'csv':
                return Response(
                    "No M365 data available",
                    mimetype='text/plain',
                    status=404
                )
            return jsonify({
                "status": "error",
                "error": "No M365 data available"
            }), 404

        snapshot_date = latest_date_result.latest_date

        # Build sort clause
        sort_clause = "organization_name, display_name"
        if sort_field == 'user_principal_name':
            sort_clause = "username, organization_name"
        elif sort_field == 'display_name':
            sort_clause = "display_name, organization_name"

        # Get all users from the latest snapshot
        results = session.execute(text(f"""
            SELECT
                organization_name,
                username,
                display_name,
                licenses
            FROM m365_user_snapshot
            WHERE snapshot_date = :snapshot_date
            ORDER BY {sort_clause}
        """), {'snapshot_date': snapshot_date}).fetchall()

        data = []
        for row in results:
            data.append({
                "organization_name": row.organization_name,
                "user_principal_name": row.username,
                "display_name": row.display_name,
                "licenses": row.licenses or "",
                "has_email_license": has_email_license(row.licenses)
            })

        if export_format == 'csv':
            # Generate CSV response
            output = io.StringIO()
            writer = csv.writer(output)

            # Write header
            writer.writerow([
                'organization_name',
                'user_principal_name',
                'display_name',
                'licenses',
                'has_email_license'
            ])

            # Write data
            for record in data:
                writer.writerow([
                    record['organization_name'],
                    record['user_principal_name'],
                    record['display_name'],
                    record['licenses'],
                    str(record['has_email_license']).lower()
                ])

            csv_content = output.getvalue()
            output.close()

            return Response(
                csv_content,
                mimetype='text/csv',
                headers={
                    'Content-Disposition': f'attachment; filename=m365_users_{snapshot_date.isoformat()}.csv'
                }
            )

        # JSON format
        return jsonify({
            "status": "success",
            "data": data,
            "total_records": len(data),
            "last_collected": snapshot_date.isoformat() + "T00:00:00Z"
        })

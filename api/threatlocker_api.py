"""
ThreatLocker API Endpoints

Provides REST API endpoints for:
1. ThreatLocker usage changes - Compare device inventory between two dates
2. Available dates - List dates with ThreatLocker snapshot data
"""

import sys
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional
import time

from flask import Blueprint, jsonify, request
from sqlalchemy import text

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Create Blueprint for ThreatLocker API
threatlocker_api = Blueprint('threatlocker_api', __name__)

# ThreatLocker vendor ID (constant)
THREATLOCKER_VENDOR_ID = 1

# Internal organizations to exclude from reporting
EXCLUDED_ORGS = ['Ener Systems, LLC', 'Ener Systems']


def validate_date(date_str: str) -> Optional[date]:
    """
    Validate and parse date string in YYYY-MM-DD format.
    """
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return None


def check_tl_date_availability(session, check_date: date) -> bool:
    """
    Check if ThreatLocker data exists for a given date.
    """
    result = session.execute(text("""
        SELECT COUNT(*)
        FROM device_snapshot
        WHERE snapshot_date = :check_date AND vendor_id = :vendor_id
    """), {'check_date': check_date, 'vendor_id': THREATLOCKER_VENDOR_ID}).scalar()

    return result > 0


def fetch_tl_available_dates(session, start_date: date, end_date: date) -> List[date]:
    """
    Get list of dates with ThreatLocker data in a range.
    """
    results = session.execute(text("""
        SELECT DISTINCT snapshot_date
        FROM device_snapshot
        WHERE vendor_id = :vendor_id
          AND snapshot_date BETWEEN :start_date AND :end_date
        ORDER BY snapshot_date
    """), {
        'vendor_id': THREATLOCKER_VENDOR_ID,
        'start_date': start_date,
        'end_date': end_date
    }).fetchall()

    return [row[0] for row in results]


def find_tl_change_dates(session, device_ids: Dict[str, List[int]], start_date: date,
                          end_date: date, change_contexts: Dict[int, Dict]) -> Dict[int, str]:
    """
    Find the specific date when each device change occurred.
    """
    change_dates = {}

    # Find first appearance date for added devices
    if device_ids.get('added'):
        added_ids = device_ids['added']
        query = text("""
            SELECT device_identity_id, MIN(snapshot_date) as first_seen
            FROM device_snapshot
            WHERE vendor_id = :vendor_id
              AND device_identity_id = ANY(:device_ids)
              AND snapshot_date > :start_date
              AND snapshot_date <= :end_date
            GROUP BY device_identity_id
        """)
        results = session.execute(query, {
            'vendor_id': THREATLOCKER_VENDOR_ID,
            'device_ids': added_ids,
            'start_date': start_date,
            'end_date': end_date
        }).fetchall()
        for row in results:
            change_dates[row.device_identity_id] = row.first_seen.strftime('%Y-%m-%d')

    # Find org change date
    if device_ids.get('org_changed'):
        org_ids = device_ids['org_changed']
        for device_id in org_ids:
            ctx = change_contexts.get(device_id, {})
            new_org = ctx.get('to_organization')
            if new_org:
                query = text("""
                    SELECT MIN(snapshot_date) as change_date
                    FROM device_snapshot
                    WHERE vendor_id = :vendor_id
                      AND device_identity_id = :device_id
                      AND organization_name = :new_org
                      AND snapshot_date > :start_date
                      AND snapshot_date <= :end_date
                """)
                result = session.execute(query, {
                    'vendor_id': THREATLOCKER_VENDOR_ID,
                    'device_id': device_id,
                    'new_org': new_org,
                    'start_date': start_date,
                    'end_date': end_date
                }).fetchone()
                if result and result.change_date:
                    change_dates[device_id] = result.change_date.strftime('%Y-%m-%d')

    return change_dates


@threatlocker_api.route('/api/threatlocker/usage-changes', methods=['GET'])
def get_tl_usage_changes():
    """
    Compare ThreatLocker device inventory between two dates.

    Identifies devices that were:
    - Added (exist on end_date but not start_date)
    - Removed (exist on start_date but not end_date)
    - Moved to different organization

    Query Parameters:
        start_date (required): Baseline date in YYYY-MM-DD format
        end_date (required): Comparison date in YYYY-MM-DD format
        detail_level (optional): "summary" (default) or "full"
        organization_name (optional): Filter by specific organization

    Returns:
        JSON response with change summary and optionally device details
    """
    from api.api_server import get_session

    start_time = time.time()

    # Parse parameters
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    detail_level = request.args.get('detail_level', 'summary')
    organization_filter = request.args.get('organization_name')

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
        if not check_tl_date_availability(session, start_date):
            return jsonify({
                "success": False,
                "error": {
                    "code": "NO_DATA",
                    "message": f"No ThreatLocker data available for start_date: {start_date_str}",
                    "status": 404
                }
            }), 404

        if not check_tl_date_availability(session, end_date):
            return jsonify({
                "success": False,
                "error": {
                    "code": "NO_DATA",
                    "message": f"No ThreatLocker data available for end_date: {end_date_str}",
                    "status": 404
                }
            }), 404

        # Build the comparison query
        org_filter_clause = ""
        params = {
            'start_date': start_date,
            'end_date': end_date,
            'vendor_id': THREATLOCKER_VENDOR_ID
        }

        if organization_filter:
            org_filter_clause = "AND (s.organization_name = :org_filter OR e.organization_name = :org_filter)"
            params['org_filter'] = organization_filter

        # Main comparison query using FULL OUTER JOIN
        # Note: ThreatLocker doesn't have billing_status - that comes from Ninja
        query = text(f"""
            WITH start_snap AS (
                SELECT
                    device_identity_id,
                    organization_name,
                    hostname,
                    display_name,
                    device_type_name,
                    computer_group,
                    security_mode,
                    location_name
                FROM device_snapshot
                WHERE snapshot_date = :start_date AND vendor_id = :vendor_id
            ),
            end_snap AS (
                SELECT
                    device_identity_id,
                    organization_name,
                    hostname,
                    display_name,
                    device_type_name,
                    computer_group,
                    security_mode,
                    location_name
                FROM device_snapshot
                WHERE snapshot_date = :end_date AND vendor_id = :vendor_id
            )
            SELECT
                COALESCE(s.device_identity_id, e.device_identity_id) as device_identity_id,
                -- Start date values
                s.organization_name as start_org,
                s.hostname as start_hostname,
                s.display_name as start_display_name,
                s.device_type_name as start_device_type,
                s.computer_group as start_computer_group,
                s.security_mode as start_security_mode,
                s.location_name as start_location,
                -- End date values
                e.organization_name as end_org,
                e.hostname as end_hostname,
                e.display_name as end_display_name,
                e.device_type_name as end_device_type,
                e.computer_group as end_computer_group,
                e.security_mode as end_security_mode,
                e.location_name as end_location,
                -- Change classification
                CASE
                    WHEN s.device_identity_id IS NULL THEN 'added'
                    WHEN e.device_identity_id IS NULL THEN 'removed'
                    WHEN s.organization_name IS DISTINCT FROM e.organization_name THEN 'org_changed'
                    ELSE 'unchanged'
                END as change_type
            FROM start_snap s
            FULL OUTER JOIN end_snap e
                ON s.device_identity_id = e.device_identity_id
            WHERE 1=1 {org_filter_clause}
            ORDER BY
                CASE
                    WHEN s.device_identity_id IS NULL THEN 'added'
                    WHEN e.device_identity_id IS NULL THEN 'removed'
                    WHEN s.organization_name IS DISTINCT FROM e.organization_name THEN 'org_changed'
                    ELSE 'unchanged'
                END,
                COALESCE(e.organization_name, s.organization_name),
                COALESCE(e.hostname, s.hostname)
        """)

        results = session.execute(query, params).fetchall()

        # Process results
        summary = {
            'added': 0,
            'removed': 0,
            'org_changed': 0,
            'unchanged': 0
        }

        by_organization = {}
        changes = {
            'added': [],
            'removed': [],
            'org_changed': []
        }

        # Track device IDs and contexts for finding change dates
        device_ids_by_type = {
            'added': [],
            'org_changed': []
        }
        change_contexts = {}

        for row in results:
            change_type = row.change_type
            summary[change_type] += 1

            # Determine organization for grouping
            if change_type == 'removed':
                org = row.start_org
            else:
                org = row.end_org

            # Skip internal orgs from org breakdown
            if org not in EXCLUDED_ORGS:
                if org not in by_organization:
                    by_organization[org] = {
                        'start_count': 0,
                        'end_count': 0,
                        'added': 0,
                        'removed': 0,
                        'org_in': 0,
                        'org_out': 0
                    }

                if change_type == 'added':
                    by_organization[org]['added'] += 1
                    by_organization[org]['end_count'] += 1
                elif change_type == 'removed':
                    by_organization[org]['removed'] += 1
                    by_organization[org]['start_count'] += 1
                elif change_type == 'org_changed':
                    # Device moved - track in both orgs
                    if row.start_org and row.start_org not in EXCLUDED_ORGS:
                        if row.start_org not in by_organization:
                            by_organization[row.start_org] = {
                                'start_count': 0, 'end_count': 0, 'added': 0,
                                'removed': 0, 'org_in': 0, 'org_out': 0
                            }
                        by_organization[row.start_org]['org_out'] += 1
                        by_organization[row.start_org]['start_count'] += 1
                    if row.end_org and row.end_org not in EXCLUDED_ORGS:
                        by_organization[row.end_org]['org_in'] += 1
                        by_organization[row.end_org]['end_count'] += 1
                elif change_type == 'unchanged':
                    by_organization[org]['start_count'] += 1
                    by_organization[org]['end_count'] += 1

            # Collect device details for full mode
            if detail_level == 'full' and change_type != 'unchanged':
                device_id = row.device_identity_id
                device_detail = {
                    'device_identity_id': device_id
                }

                if change_type == 'added':
                    device_ids_by_type['added'].append(device_id)
                    device_detail.update({
                        'hostname': row.end_hostname,
                        'display_name': row.end_display_name,
                        'organization_name': row.end_org,
                        'device_type': row.end_device_type,
                        'computer_group': row.end_computer_group,
                        'security_mode': row.end_security_mode,
                        'location_name': row.end_location
                    })
                elif change_type == 'removed':
                    device_detail.update({
                        'hostname': row.start_hostname,
                        'display_name': row.start_display_name,
                        'organization_name': row.start_org,
                        'device_type': row.start_device_type,
                        'computer_group': row.start_computer_group,
                        'security_mode': row.start_security_mode,
                        'location_name': row.start_location,
                        'last_seen_date': start_date_str
                    })
                elif change_type == 'org_changed':
                    device_ids_by_type['org_changed'].append(device_id)
                    change_contexts[device_id] = {'to_organization': row.end_org}
                    device_detail.update({
                        'hostname': row.end_hostname or row.start_hostname,
                        'display_name': row.end_display_name or row.start_display_name,
                        'from_organization': row.start_org,
                        'to_organization': row.end_org,
                        'device_type': row.end_device_type,
                        'computer_group': row.end_computer_group,
                        'security_mode': row.end_security_mode
                    })

                changes[change_type].append(device_detail)

        # Find specific change dates for each device (only in full mode)
        if detail_level == 'full':
            change_dates = find_tl_change_dates(
                session, device_ids_by_type, start_date, end_date, change_contexts
            )

            # Add change_date to each device detail
            for change_type in ['added', 'org_changed']:
                for device in changes[change_type]:
                    device_id = device.get('device_identity_id')
                    if device_id in change_dates:
                        device['change_date'] = change_dates[device_id]

        # Calculate totals
        start_total = summary['removed'] + summary['org_changed'] + summary['unchanged']
        end_total = summary['added'] + summary['org_changed'] + summary['unchanged']

        query_time_ms = int((time.time() - start_time) * 1000)

        # Build response
        response_data = {
            'start_date': start_date_str,
            'end_date': end_date_str,
            'summary': {
                'start_total_devices': start_total,
                'end_total_devices': end_total,
                'net_change': end_total - start_total,
                'changes': {
                    'added': summary['added'],
                    'removed': summary['removed'],
                    'org_changed': summary['org_changed']
                }
            },
            'by_organization': dict(sorted(by_organization.items())),
            'metadata': {
                'vendor_id': THREATLOCKER_VENDOR_ID,
                'vendor_name': 'ThreatLocker',
                'query_time_ms': query_time_ms,
                'detail_level': detail_level,
                'data_retention_note': 'Device-level data available for last 65 days',
                'billing_note': 'Billing status comes from Ninja, not ThreatLocker'
            }
        }

        # Add device details in full mode
        if detail_level == 'full':
            response_data['changes'] = changes

        # Add organization filter info if used
        if organization_filter:
            response_data['metadata']['organization_filter'] = organization_filter

        return jsonify({
            'success': True,
            'data': response_data
        })


@threatlocker_api.route('/api/threatlocker/available-dates', methods=['GET'])
def get_tl_available_dates():
    """
    Get list of dates with ThreatLocker snapshot data available.

    Query Parameters:
        days (optional): Number of days to look back (default: 65)

    Returns:
        JSON response with list of available dates
    """
    from api.api_server import get_session

    days = request.args.get('days', 65, type=int)
    if days < 1 or days > 365:
        days = 65

    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    with get_session() as session:
        available = fetch_tl_available_dates(session, start_date, end_date)

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

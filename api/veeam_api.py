"""
Veeam API Endpoints

Provides REST API endpoints for:
1. Veeam usage changes - Compare cloud storage data between two dates
2. Available dates - List dates with Veeam snapshot data
"""

import sys
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional
from decimal import Decimal
import time

from flask import Blueprint, jsonify, request
from sqlalchemy import text

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Create Blueprint for Veeam API
veeam_api = Blueprint('veeam_api', __name__)


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


def check_veeam_date_availability(session, check_date: date) -> bool:
    """
    Check if Veeam data exists for a given date.

    Args:
        session: Database session
        check_date: Date to check

    Returns:
        bool: True if data exists, False otherwise
    """
    result = session.execute(text("""
        SELECT COUNT(*)
        FROM veeam_snapshot
        WHERE snapshot_date = :check_date
    """), {'check_date': check_date}).scalar()

    return result > 0


def get_veeam_available_dates(session, start_date: date, end_date: date) -> List[date]:
    """
    Get list of dates with Veeam data in a range.

    Args:
        session: Database session
        start_date: Start of range
        end_date: End of range

    Returns:
        List of dates with data
    """
    results = session.execute(text("""
        SELECT DISTINCT snapshot_date
        FROM veeam_snapshot
        WHERE snapshot_date BETWEEN :start_date AND :end_date
        ORDER BY snapshot_date
    """), {
        'start_date': start_date,
        'end_date': end_date
    }).fetchall()

    return [row[0] for row in results]


def decimal_to_float(val):
    """Convert Decimal to float for JSON serialization."""
    if isinstance(val, Decimal):
        return float(val)
    return val


@veeam_api.route('/api/veeam/available-dates', methods=['GET'])
def get_available_dates():
    """
    Get list of dates with Veeam snapshot data available.

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
        available = get_veeam_available_dates(session, start_date, end_date)

        # Get earliest and latest dates in database
        date_range = session.execute(text("""
            SELECT MIN(snapshot_date) as earliest, MAX(snapshot_date) as latest
            FROM veeam_snapshot
        """)).fetchone()

        return jsonify({
            'success': True,
            'data': {
                'dates': [d.isoformat() for d in available],
                'count': len(available),
                'earliest': date_range.earliest.isoformat() if date_range.earliest else None,
                'latest': date_range.latest.isoformat() if date_range.latest else None,
                'range': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                }
            }
        })


@veeam_api.route('/api/veeam/usage-changes', methods=['GET'])
def get_veeam_usage_changes():
    """
    Compare Veeam cloud storage data between two dates.

    Identifies organizations that were:
    - Added (exist on end_date but not start_date)
    - Removed (exist on start_date but not end_date)
    - Increased (storage grew)
    - Decreased (storage reduced)
    - Unchanged (same storage amount)

    Query Parameters:
        start_date (required): Baseline date in YYYY-MM-DD format
        end_date (required): Comparison date in YYYY-MM-DD format
        detail_level (optional): "summary" or "full" (default: "full")

    Returns:
        JSON response with change summary and organization details
    """
    from api.api_server import get_session

    start_time = time.time()

    # Parse parameters
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    detail_level = request.args.get('detail_level', 'full')

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
        if not check_veeam_date_availability(session, start_date):
            return jsonify({
                "success": False,
                "error": {
                    "code": "NO_DATA",
                    "message": f"No Veeam data available for start_date: {start_date_str}",
                    "status": 404
                }
            }), 404

        if not check_veeam_date_availability(session, end_date):
            return jsonify({
                "success": False,
                "error": {
                    "code": "NO_DATA",
                    "message": f"No Veeam data available for end_date: {end_date_str}",
                    "status": 404
                }
            }), 404

        # Main comparison query using FULL OUTER JOIN
        query = text("""
            WITH start_snap AS (
                SELECT
                    company_uid,
                    organization_name,
                    storage_gb,
                    quota_gb,
                    usage_pct
                FROM veeam_snapshot
                WHERE snapshot_date = :start_date
            ),
            end_snap AS (
                SELECT
                    company_uid,
                    organization_name,
                    storage_gb,
                    quota_gb,
                    usage_pct
                FROM veeam_snapshot
                WHERE snapshot_date = :end_date
            )
            SELECT
                COALESCE(s.company_uid, e.company_uid) as organization_uid,
                COALESCE(e.organization_name, s.organization_name) as organization_name,
                -- Start date values
                s.storage_gb as start_storage_gb,
                s.quota_gb as start_quota_gb,
                -- End date values
                e.storage_gb as end_storage_gb,
                e.quota_gb as end_quota_gb,
                -- Change classification
                CASE
                    WHEN s.company_uid IS NULL THEN 'added'
                    WHEN e.company_uid IS NULL THEN 'removed'
                    WHEN COALESCE(e.storage_gb, 0) > COALESCE(s.storage_gb, 0) THEN 'increased'
                    WHEN COALESCE(e.storage_gb, 0) < COALESCE(s.storage_gb, 0) THEN 'decreased'
                    ELSE 'unchanged'
                END as change_type,
                -- Calculate change
                COALESCE(e.storage_gb, 0) - COALESCE(s.storage_gb, 0) as storage_change_gb
            FROM start_snap s
            FULL OUTER JOIN end_snap e
                ON s.company_uid = e.company_uid
            ORDER BY
                CASE
                    WHEN s.company_uid IS NULL THEN 1
                    WHEN e.company_uid IS NULL THEN 2
                    WHEN COALESCE(e.storage_gb, 0) > COALESCE(s.storage_gb, 0) THEN 3
                    WHEN COALESCE(e.storage_gb, 0) < COALESCE(s.storage_gb, 0) THEN 4
                    ELSE 5
                END,
                ABS(COALESCE(e.storage_gb, 0) - COALESCE(s.storage_gb, 0)) DESC
        """)

        results = session.execute(query, {
            'start_date': start_date,
            'end_date': end_date
        }).fetchall()

        # Process results
        summary_counts = {
            'added': 0,
            'removed': 0,
            'increased': 0,
            'decreased': 0,
            'unchanged': 0
        }

        changes = {
            'added': [],
            'removed': [],
            'increased': [],
            'decreased': [],
            'unchanged': []
        }

        # Track totals
        start_total_storage = Decimal('0')
        end_total_storage = Decimal('0')

        for row in results:
            change_type = row.change_type
            summary_counts[change_type] += 1

            # Track storage totals
            if row.start_storage_gb:
                start_total_storage += row.start_storage_gb
            if row.end_storage_gb:
                end_total_storage += row.end_storage_gb

            # Build organization detail
            org_detail = {
                'organization_name': row.organization_name,
                'organization_uid': row.organization_uid
            }

            if change_type == 'added':
                org_detail['cloud_storage_used_gb'] = decimal_to_float(row.end_storage_gb)
                org_detail['quota_gb'] = decimal_to_float(row.end_quota_gb)
            elif change_type == 'removed':
                org_detail['cloud_storage_used_gb'] = decimal_to_float(row.start_storage_gb)
                org_detail['quota_gb'] = decimal_to_float(row.start_quota_gb)
            elif change_type in ('increased', 'decreased'):
                org_detail['start_gb'] = decimal_to_float(row.start_storage_gb)
                org_detail['end_gb'] = decimal_to_float(row.end_storage_gb)
                org_detail['change_gb'] = decimal_to_float(row.storage_change_gb)
                if row.start_storage_gb and row.start_storage_gb > 0:
                    change_pct = (row.storage_change_gb / row.start_storage_gb) * 100
                    org_detail['change_percent'] = round(decimal_to_float(change_pct), 2)
                else:
                    org_detail['change_percent'] = None
            else:  # unchanged
                org_detail['storage_gb'] = decimal_to_float(row.end_storage_gb)

            changes[change_type].append(org_detail)

        # Calculate totals
        start_total_orgs = summary_counts['removed'] + summary_counts['increased'] + summary_counts['decreased'] + summary_counts['unchanged']
        end_total_orgs = summary_counts['added'] + summary_counts['increased'] + summary_counts['decreased'] + summary_counts['unchanged']
        total_storage_change = end_total_storage - start_total_storage

        # Calculate percent change
        if start_total_storage > 0:
            storage_change_pct = round(decimal_to_float((total_storage_change / start_total_storage) * 100), 2)
        else:
            storage_change_pct = None

        query_time_ms = int((time.time() - start_time) * 1000)

        # Build response
        response_data = {
            'period': {
                'start_date': start_date_str,
                'end_date': end_date_str
            },
            'summary': {
                'total_organizations_start': start_total_orgs,
                'total_organizations_end': end_total_orgs,
                'organizations_added': summary_counts['added'],
                'organizations_removed': summary_counts['removed'],
                'total_storage_start_gb': round(decimal_to_float(start_total_storage), 2),
                'total_storage_end_gb': round(decimal_to_float(end_total_storage), 2),
                'total_storage_change_gb': round(decimal_to_float(total_storage_change), 2),
                'total_storage_change_percent': storage_change_pct
            },
            'metadata': {
                'vendor_name': 'Veeam',
                'query_time_ms': query_time_ms,
                'detail_level': detail_level
            }
        }

        # Add detailed changes in full mode
        if detail_level == 'full':
            response_data['changes'] = changes

        return jsonify({
            'success': True,
            'data': response_data
        })

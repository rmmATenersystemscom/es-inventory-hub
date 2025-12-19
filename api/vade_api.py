"""
Vade API Endpoints

Provides REST API endpoints for:
1. Vade usage changes - Compare customer/license data between two dates
2. Available dates - List dates with Vade snapshot data
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

# Create Blueprint for Vade API
vade_api = Blueprint('vade_api', __name__)

# Internal customers to exclude from reporting (if any)
EXCLUDED_CUSTOMERS = []


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


def check_vade_date_availability(session, check_date: date) -> bool:
    """
    Check if Vade data exists for a given date.

    Args:
        session: Database session
        check_date: Date to check

    Returns:
        bool: True if data exists, False otherwise
    """
    result = session.execute(text("""
        SELECT COUNT(*)
        FROM vadesecure_snapshot
        WHERE snapshot_date = :check_date
    """), {'check_date': check_date}).scalar()

    return result > 0


def get_vade_available_dates(session, start_date: date, end_date: date) -> List[date]:
    """
    Get list of dates with Vade data in a range.

    Args:
        session: Database session
        start_date: Start of range
        end_date: End of range

    Returns:
        List of dates with data
    """
    results = session.execute(text("""
        SELECT DISTINCT snapshot_date
        FROM vadesecure_snapshot
        WHERE snapshot_date BETWEEN :start_date AND :end_date
        ORDER BY snapshot_date
    """), {
        'start_date': start_date,
        'end_date': end_date
    }).fetchall()

    return [row[0] for row in results]


def find_vade_change_dates(session, customer_ids: Dict[str, List[str]], start_date: date,
                           end_date: date, change_contexts: Dict[str, Dict]) -> Dict[str, str]:
    """
    Find the specific date when each customer change occurred.

    Args:
        session: Database session
        customer_ids: Dict mapping change_type to list of customer_ids
        start_date: Start of date range
        end_date: End of date range
        change_contexts: Dict mapping customer_id to context info

    Returns:
        Dict mapping customer_id to change_date string (YYYY-MM-DD)
    """
    change_dates = {}

    # Find first appearance date for added customers
    if customer_ids.get('added'):
        added_ids = customer_ids['added']
        query = text("""
            SELECT customer_id, MIN(snapshot_date) as first_seen
            FROM vadesecure_snapshot
            WHERE customer_id = ANY(:customer_ids)
              AND snapshot_date > :start_date
              AND snapshot_date <= :end_date
            GROUP BY customer_id
        """)
        results = session.execute(query, {
            'customer_ids': added_ids,
            'start_date': start_date,
            'end_date': end_date
        }).fetchall()
        for row in results:
            change_dates[row.customer_id] = row.first_seen.strftime('%Y-%m-%d')

    # Find usage change date
    if customer_ids.get('usage_changed'):
        for customer_id in customer_ids['usage_changed']:
            ctx = change_contexts.get(customer_id, {})
            new_usage = ctx.get('to_usage_count')
            if new_usage is not None:
                query = text("""
                    SELECT MIN(snapshot_date) as change_date
                    FROM vadesecure_snapshot
                    WHERE customer_id = :customer_id
                      AND usage_count = :new_usage
                      AND snapshot_date > :start_date
                      AND snapshot_date <= :end_date
                """)
                result = session.execute(query, {
                    'customer_id': customer_id,
                    'new_usage': new_usage,
                    'start_date': start_date,
                    'end_date': end_date
                }).fetchone()
                if result and result.change_date:
                    change_dates[customer_id] = result.change_date.strftime('%Y-%m-%d')

    # Find license status change date
    if customer_ids.get('license_changed'):
        for customer_id in customer_ids['license_changed']:
            ctx = change_contexts.get(customer_id, {})
            new_status = ctx.get('to_license_status')
            if new_status:
                query = text("""
                    SELECT MIN(snapshot_date) as change_date
                    FROM vadesecure_snapshot
                    WHERE customer_id = :customer_id
                      AND license_status = :new_status
                      AND snapshot_date > :start_date
                      AND snapshot_date <= :end_date
                """)
                result = session.execute(query, {
                    'customer_id': customer_id,
                    'new_status': new_status,
                    'start_date': start_date,
                    'end_date': end_date
                }).fetchone()
                if result and result.change_date:
                    change_dates[customer_id] = result.change_date.strftime('%Y-%m-%d')

    return change_dates


@vade_api.route('/api/vade/usage-changes', methods=['GET'])
def get_vade_usage_changes():
    """
    Compare Vade customer/license data between two dates.

    Identifies customers that were:
    - Added (exist on end_date but not start_date)
    - Removed (exist on start_date but not end_date)
    - Usage changed (same customer, different usage_count)
    - License status changed (active <-> expired, etc.)

    Query Parameters:
        start_date (required): Baseline date in YYYY-MM-DD format
        end_date (required): Comparison date in YYYY-MM-DD format
        detail_level (optional): "summary" (default) or "full"
        customer_name (optional): Filter by specific customer name

    Returns:
        JSON response with change summary and optionally customer details
    """
    from api.api_server import get_session

    start_time = time.time()

    # Parse parameters
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    detail_level = request.args.get('detail_level', 'summary')
    customer_filter = request.args.get('customer_name')

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
        if not check_vade_date_availability(session, start_date):
            return jsonify({
                "success": False,
                "error": {
                    "code": "NO_DATA",
                    "message": f"No Vade data available for start_date: {start_date_str}",
                    "status": 404
                }
            }), 404

        if not check_vade_date_availability(session, end_date):
            return jsonify({
                "success": False,
                "error": {
                    "code": "NO_DATA",
                    "message": f"No Vade data available for end_date: {end_date_str}",
                    "status": 404
                }
            }), 404

        # Build the comparison query
        customer_filter_clause = ""
        params = {
            'start_date': start_date,
            'end_date': end_date
        }

        if customer_filter:
            customer_filter_clause = "AND (s.customer_name ILIKE :customer_filter OR e.customer_name ILIKE :customer_filter)"
            params['customer_filter'] = f'%{customer_filter}%'

        # Main comparison query using FULL OUTER JOIN
        query = text(f"""
            WITH start_snap AS (
                SELECT
                    customer_id,
                    customer_name,
                    company_domain,
                    contact_email,
                    license_id,
                    product_type,
                    license_status,
                    license_start_date,
                    license_end_date,
                    tenant_id,
                    usage_count
                FROM vadesecure_snapshot
                WHERE snapshot_date = :start_date
            ),
            end_snap AS (
                SELECT
                    customer_id,
                    customer_name,
                    company_domain,
                    contact_email,
                    license_id,
                    product_type,
                    license_status,
                    license_start_date,
                    license_end_date,
                    tenant_id,
                    usage_count
                FROM vadesecure_snapshot
                WHERE snapshot_date = :end_date
            )
            SELECT
                COALESCE(s.customer_id, e.customer_id) as customer_id,
                -- Start date values
                s.customer_name as start_customer_name,
                s.company_domain as start_company_domain,
                s.contact_email as start_contact_email,
                s.license_id as start_license_id,
                s.product_type as start_product_type,
                s.license_status as start_license_status,
                s.usage_count as start_usage_count,
                -- End date values
                e.customer_name as end_customer_name,
                e.company_domain as end_company_domain,
                e.contact_email as end_contact_email,
                e.license_id as end_license_id,
                e.product_type as end_product_type,
                e.license_status as end_license_status,
                e.usage_count as end_usage_count,
                -- Change classification (priority order)
                CASE
                    WHEN s.customer_id IS NULL THEN 'added'
                    WHEN e.customer_id IS NULL THEN 'removed'
                    WHEN COALESCE(s.usage_count, 0) != COALESCE(e.usage_count, 0) THEN 'usage_changed'
                    WHEN s.license_status IS DISTINCT FROM e.license_status THEN 'license_changed'
                    ELSE 'unchanged'
                END as change_type
            FROM start_snap s
            FULL OUTER JOIN end_snap e
                ON s.customer_id = e.customer_id
            WHERE 1=1 {customer_filter_clause}
            ORDER BY
                CASE
                    WHEN s.customer_id IS NULL THEN 1
                    WHEN e.customer_id IS NULL THEN 2
                    WHEN COALESCE(s.usage_count, 0) != COALESCE(e.usage_count, 0) THEN 3
                    WHEN s.license_status IS DISTINCT FROM e.license_status THEN 4
                    ELSE 5
                END,
                COALESCE(e.customer_name, s.customer_name)
        """)

        results = session.execute(query, params).fetchall()

        # Process results
        summary = {
            'added': 0,
            'removed': 0,
            'usage_changed': 0,
            'license_changed': 0,
            'unchanged': 0
        }

        by_customer = {}
        changes = {
            'added': [],
            'removed': [],
            'usage_changed': [],
            'license_changed': []
        }

        # Track totals for usage
        start_total_usage = 0
        end_total_usage = 0

        # Track customer IDs and contexts for finding change dates
        customer_ids_by_type = {
            'added': [],
            'usage_changed': [],
            'license_changed': []
        }
        change_contexts = {}

        for row in results:
            change_type = row.change_type
            summary[change_type] += 1

            # Determine customer name for grouping
            customer_name = row.end_customer_name or row.start_customer_name

            # Skip excluded customers
            if customer_name in EXCLUDED_CUSTOMERS:
                continue

            # Track usage totals
            if row.start_usage_count:
                start_total_usage += row.start_usage_count
            if row.end_usage_count:
                end_total_usage += row.end_usage_count

            # Build per-customer breakdown
            if customer_name not in by_customer:
                by_customer[customer_name] = {
                    'customer_id': row.customer_id,
                    'start_usage': row.start_usage_count,
                    'end_usage': row.end_usage_count,
                    'usage_change': (row.end_usage_count or 0) - (row.start_usage_count or 0),
                    'change_type': change_type,
                    'start_license_status': row.start_license_status,
                    'end_license_status': row.end_license_status
                }

            # Collect customer details for full mode
            if detail_level == 'full' and change_type != 'unchanged':
                customer_id = row.customer_id
                customer_detail = {
                    'customer_id': customer_id,
                    'customer_name': customer_name
                }

                if change_type == 'added':
                    customer_ids_by_type['added'].append(customer_id)
                    customer_detail.update({
                        'company_domain': row.end_company_domain,
                        'contact_email': row.end_contact_email,
                        'product_type': row.end_product_type,
                        'license_status': row.end_license_status,
                        'usage_count': row.end_usage_count
                    })
                elif change_type == 'removed':
                    customer_detail.update({
                        'company_domain': row.start_company_domain,
                        'contact_email': row.start_contact_email,
                        'product_type': row.start_product_type,
                        'license_status': row.start_license_status,
                        'usage_count': row.start_usage_count,
                        'last_seen_date': start_date_str
                    })
                elif change_type == 'usage_changed':
                    customer_ids_by_type['usage_changed'].append(customer_id)
                    change_contexts[customer_id] = {'to_usage_count': row.end_usage_count}
                    customer_detail.update({
                        'company_domain': row.end_company_domain,
                        'contact_email': row.end_contact_email,
                        'product_type': row.end_product_type,
                        'license_status': row.end_license_status,
                        'from_usage_count': row.start_usage_count,
                        'to_usage_count': row.end_usage_count,
                        'usage_delta': (row.end_usage_count or 0) - (row.start_usage_count or 0)
                    })
                elif change_type == 'license_changed':
                    customer_ids_by_type['license_changed'].append(customer_id)
                    change_contexts[customer_id] = {'to_license_status': row.end_license_status}
                    customer_detail.update({
                        'company_domain': row.end_company_domain,
                        'contact_email': row.end_contact_email,
                        'product_type': row.end_product_type,
                        'from_license_status': row.start_license_status,
                        'to_license_status': row.end_license_status,
                        'usage_count': row.end_usage_count
                    })

                changes[change_type].append(customer_detail)

        # Find specific change dates for each customer (only in full mode)
        if detail_level == 'full':
            change_dates = find_vade_change_dates(
                session, customer_ids_by_type, start_date, end_date, change_contexts
            )

            # Add change_date to each customer detail
            for change_type in ['added', 'usage_changed', 'license_changed']:
                for customer in changes[change_type]:
                    customer_id = customer.get('customer_id')
                    if customer_id in change_dates:
                        customer['change_date'] = change_dates[customer_id]

        # Calculate totals
        start_total_customers = summary['removed'] + summary['usage_changed'] + summary['license_changed'] + summary['unchanged']
        end_total_customers = summary['added'] + summary['usage_changed'] + summary['license_changed'] + summary['unchanged']

        query_time_ms = int((time.time() - start_time) * 1000)

        # Build response
        response_data = {
            'start_date': start_date_str,
            'end_date': end_date_str,
            'summary': {
                'start_total_customers': start_total_customers,
                'end_total_customers': end_total_customers,
                'net_customer_change': end_total_customers - start_total_customers,
                'start_total_usage': start_total_usage,
                'end_total_usage': end_total_usage,
                'net_usage_change': end_total_usage - start_total_usage,
                'changes': {
                    'added': summary['added'],
                    'removed': summary['removed'],
                    'usage_changed': summary['usage_changed'],
                    'license_changed': summary['license_changed']
                }
            },
            'by_customer': dict(sorted(by_customer.items())),
            'metadata': {
                'vendor_name': 'VadeSecure',
                'query_time_ms': query_time_ms,
                'detail_level': detail_level,
                'data_retention_note': 'Customer-level data available for historical snapshots'
            }
        }

        # Add customer details in full mode
        if detail_level == 'full':
            response_data['changes'] = changes

        # Add customer filter info if used
        if customer_filter:
            response_data['metadata']['customer_filter'] = customer_filter

        return jsonify({
            'success': True,
            'data': response_data
        })


@vade_api.route('/api/vade/available-dates', methods=['GET'])
def get_available_dates():
    """
    Get list of dates with Vade snapshot data available.

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
        available = get_vade_available_dates(session, start_date, end_date)

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

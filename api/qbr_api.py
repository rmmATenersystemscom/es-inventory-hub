"""
QBR (Quarterly Business Review) API Endpoints

Provides REST API endpoints for:
1. Retrieving monthly and quarterly metrics
2. Calculating and retrieving SmartNumbers/KPIs
3. Managing performance thresholds
4. Manual data entry for missing metrics
"""

import sys
from pathlib import Path
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, List, Any, Optional

from flask import Blueprint, jsonify, request
from sqlalchemy.orm import Session
from sqlalchemy import text, and_, func

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import authentication decorator
from api.auth_microsoft import require_auth

from storage.schema import (
    QBRMetricsMonthly,
    QBRMetricsQuarterly,
    QBRSmartNumbers,
    QBRThresholds,
    QBRCollectionLog,
    Organization,
    DeviceSnapshot,
    Vendor
)
from collectors.qbr.smartnumbers import (
    SmartNumbersCalculator,
    MonthlyMetrics,
    QuarterlyMetrics,
    aggregate_monthly_to_quarterly
)
from collectors.qbr.utils import get_period_boundaries

# Create Blueprint for QBR API
qbr_api = Blueprint('qbr_api', __name__)


def validate_period(period: str, period_type: str = 'monthly') -> bool:
    """
    Validate period format.

    Args:
        period: Period string (YYYY-MM for monthly, YYYY-Q1 for quarterly)
        period_type: 'monthly' or 'quarterly'

    Returns:
        bool: True if valid, False otherwise
    """
    if period_type == 'monthly':
        # Format: YYYY-MM
        if len(period) != 7 or period[4] != '-':
            return False
        try:
            year = int(period[:4])
            month = int(period[5:7])
            return 1 <= month <= 12 and 2000 <= year <= 2100
        except ValueError:
            return False

    elif period_type == 'quarterly':
        # Format: YYYY-Q1, YYYY-Q2, YYYY-Q3, YYYY-Q4
        if len(period) != 7 or period[4] != '-' or period[5] != 'Q':
            return False
        try:
            year = int(period[:4])
            quarter = int(period[6])
            return 1 <= quarter <= 4 and 2000 <= year <= 2100
        except ValueError:
            return False

    return False


def period_to_months(period: str) -> List[str]:
    """
    Convert quarterly period to list of month periods.

    Args:
        period: Quarterly period (e.g., '2025-Q1')

    Returns:
        List of monthly periods (e.g., ['2025-01', '2025-02', '2025-03'])
    """
    year = period[:4]
    quarter = int(period[6])

    quarters = {
        1: ['01', '02', '03'],
        2: ['04', '05', '06'],
        3: ['07', '08', '09'],
        4: ['10', '11', '12']
    }

    return [f"{year}-{month}" for month in quarters[quarter]]


def decimal_to_float(obj):
    """Convert Decimal objects to float for JSON serialization."""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


# ============================================================================
# GET /api/qbr/metrics/monthly
# ============================================================================

@qbr_api.route('/api/qbr/metrics/monthly', methods=['GET'])
@require_auth
def get_monthly_metrics():
    """
    Get monthly QBR metrics.

    Query Parameters:
        period (optional): Specific period (YYYY-MM). Returns latest if not specified.
        organization_id (optional): Filter by organization (default: 1)
        vendor_id (optional): Filter by vendor
        metric_name (optional): Filter by specific metric name
        data_source (optional): Filter by data source: 'quickbooks', 'manual', 'collected', or 'best'
                               'best' returns highest-priority value per metric (quickbooks > collected > manual)

    Returns:
        JSON response with monthly metrics
    """
    from api.api_server import get_session

    period = request.args.get('period')
    organization_id = request.args.get('organization_id', 1, type=int)
    vendor_id = request.args.get('vendor_id', type=int)
    metric_name = request.args.get('metric_name')
    data_source = request.args.get('data_source')

    # Validate period if provided
    if period and not validate_period(period, 'monthly'):
        return jsonify({
            "success": False,
            "error": {
                "code": "INVALID_PERIOD",
                "message": "Period format must be YYYY-MM",
                "status": 400
            }
        }), 400

    # Validate data_source if provided
    valid_sources = ['quickbooks', 'manual', 'collected', 'best']
    if data_source and data_source not in valid_sources:
        return jsonify({
            "success": False,
            "error": {
                "code": "INVALID_DATA_SOURCE",
                "message": f"data_source must be one of: {', '.join(valid_sources)}",
                "status": 400
            }
        }), 400

    try:
        with get_session() as session:
            query = session.query(QBRMetricsMonthly).filter(
                QBRMetricsMonthly.organization_id == organization_id
            )

            if period:
                query = query.filter(QBRMetricsMonthly.period == period)
            else:
                # Get latest period
                latest_period = session.query(QBRMetricsMonthly.period)\
                    .filter(QBRMetricsMonthly.organization_id == organization_id)\
                    .order_by(QBRMetricsMonthly.period.desc())\
                    .first()

                if latest_period:
                    query = query.filter(QBRMetricsMonthly.period == latest_period[0])
                    period = latest_period[0]

            if vendor_id:
                query = query.filter(QBRMetricsMonthly.vendor_id == vendor_id)

            if metric_name:
                query = query.filter(QBRMetricsMonthly.metric_name == metric_name)

            # Filter by data_source (except 'best' which needs post-processing)
            if data_source and data_source != 'best':
                query = query.filter(QBRMetricsMonthly.data_source == data_source)

            metrics = query.order_by(
                QBRMetricsMonthly.period.desc(),
                QBRMetricsMonthly.vendor_id,
                QBRMetricsMonthly.metric_name
            ).all()

            # If 'best' mode, select highest-priority source per metric
            if data_source == 'best':
                # Priority: calculated > quickbooks > collected > manual
                source_priority = {'calculated': 1, 'quickbooks': 2, 'collected': 3, 'manual': 4}
                metrics_by_name = {}
                for m in metrics:
                    priority = source_priority.get(m.data_source, 99)
                    if m.metric_name not in metrics_by_name:
                        metrics_by_name[m.metric_name] = (m, priority)
                    elif priority < metrics_by_name[m.metric_name][1]:
                        metrics_by_name[m.metric_name] = (m, priority)
                metrics = [item[0] for item in metrics_by_name.values()]

            result = {
                "success": True,
                "data": {
                    "period": period or (metrics[0].period if metrics else None),
                    "organization_id": organization_id,
                    "data_source_filter": data_source,
                    "metrics": [
                        {
                            "metric_name": m.metric_name,
                            "metric_value": float(m.metric_value) if m.metric_value else None,
                            "vendor_id": m.vendor_id,
                            "data_source": m.data_source,
                            "notes": m.notes,
                            "updated_at": m.updated_at.isoformat() if m.updated_at else None
                        }
                        for m in metrics
                    ]
                }
            }

            return jsonify(result), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": {
                "code": "SERVER_ERROR",
                "message": str(e),
                "status": 500
            }
        }), 500


# ============================================================================
# GET /api/qbr/metrics/devices-by-client
# ============================================================================

def get_period_range(start_period: str, end_period: str) -> List[str]:
    """
    Generate list of monthly periods between start and end (inclusive).

    Args:
        start_period: Start month in YYYY-MM format
        end_period: End month in YYYY-MM format

    Returns:
        List of period strings in YYYY-MM format
    """
    periods = []
    start_year, start_month = map(int, start_period.split('-'))
    end_year, end_month = map(int, end_period.split('-'))

    current_year, current_month = start_year, start_month
    while (current_year, current_month) <= (end_year, end_month):
        periods.append(f"{current_year:04d}-{current_month:02d}")
        current_month += 1
        if current_month > 12:
            current_month = 1
            current_year += 1

    return periods


def get_period_date_bounds(period: str) -> tuple:
    """
    Get the first and last day of a period.

    Args:
        period: Month in YYYY-MM format

    Returns:
        Tuple of (first_day, last_day) as date objects
    """
    year, month = map(int, period.split('-'))
    first_day = date(year, month, 1)
    if month == 12:
        last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)
    return first_day, last_day


def get_devices_for_period(session, period: str, ninja_vendor_id: int, excluded_orgs: List[str]) -> Optional[Dict]:
    """
    Get seat and endpoint counts for a single period.

    Args:
        session: Database session
        period: Month in YYYY-MM format
        ninja_vendor_id: ID of the Ninja vendor
        excluded_orgs: List of organization names to exclude

    Returns:
        Dict with period data or None if no data available
    """
    # Determine data source based on period
    use_historical = period < '2025-10'

    if use_historical:
        # Query historical data from qbr_client_metrics table
        historical_query = text("""
            SELECT client_name, seats, endpoints
            FROM qbr_client_metrics
            WHERE period = :period
            ORDER BY endpoints DESC
        """)
        results = session.execute(historical_query, {'period': period}).fetchall()

        if not results:
            return None

        clients = [
            {
                'client_name': row[0],
                'seats': row[1] or 0,
                'endpoints': row[2] or 0
            }
            for row in results
        ]

        return {
            "period": period,
            "data_source": "historical",
            "clients": clients,
            "total_seats": sum(c['seats'] for c in clients),
            "total_endpoints": sum(c['endpoints'] for c in clients)
        }

    else:
        # Use live device_snapshot data
        # Find the most recent snapshot date within this period
        first_day, last_day = get_period_date_bounds(period)

        # Query for the most recent snapshot date in the period
        most_recent = session.query(
            func.max(DeviceSnapshot.snapshot_date)
        ).filter(
            DeviceSnapshot.vendor_id == ninja_vendor_id,
            DeviceSnapshot.snapshot_date >= first_day,
            DeviceSnapshot.snapshot_date <= last_day
        ).scalar()

        if not most_recent:
            return None

        snapshot_date = most_recent

        # Query ENDPOINTS (all billable devices, exclude internal orgs)
        endpoint_results = session.query(
            DeviceSnapshot.organization_name,
            func.count().label('endpoints')
        ).filter(
            DeviceSnapshot.snapshot_date == snapshot_date,
            DeviceSnapshot.vendor_id == ninja_vendor_id,
            DeviceSnapshot.billable_status_name == 'billable',
            ~DeviceSnapshot.organization_name.in_(excluded_orgs)
        ).group_by(DeviceSnapshot.organization_name).all()

        endpoints_by_client = {r.organization_name: r.endpoints for r in endpoint_results}

        # Query SEATS (billable workstations only, exclude internal orgs)
        seat_results = session.query(
            DeviceSnapshot.organization_name,
            func.count().label('seats')
        ).filter(
            DeviceSnapshot.snapshot_date == snapshot_date,
            DeviceSnapshot.vendor_id == ninja_vendor_id,
            DeviceSnapshot.device_type_name == 'workstation',
            DeviceSnapshot.billable_status_name == 'billable',
            ~DeviceSnapshot.organization_name.in_(excluded_orgs)
        ).group_by(DeviceSnapshot.organization_name).all()

        seats_by_client = {r.organization_name: r.seats for r in seat_results}

        # Merge results (all clients that have either seats or endpoints)
        all_clients = set(endpoints_by_client.keys()) | set(seats_by_client.keys())
        clients = [
            {
                'client_name': name,
                'seats': seats_by_client.get(name, 0),
                'endpoints': endpoints_by_client.get(name, 0)
            }
            for name in sorted(all_clients, key=lambda x: endpoints_by_client.get(x, 0), reverse=True)
        ]

        return {
            "period": period,
            "data_source": "live",
            "snapshot_date": snapshot_date.isoformat(),
            "clients": clients,
            "total_seats": sum(seats_by_client.values()),
            "total_endpoints": sum(endpoints_by_client.values())
        }


@qbr_api.route('/api/qbr/metrics/devices-by-client', methods=['GET'])
def get_devices_by_client():
    """
    Get seat and endpoint counts by client for one or more months.

    Data Sources:
    - Oct 2025 onwards: Live device_snapshot data from Ninja collector
    - Before Oct 2025: Historical data from qbr_client_metrics table (imported from EnerCare)

    Definitions (per STD_SEAT_ENDPOINT_DEFINITIONS.md):
    - Endpoint: All billable devices (workstations + servers), excludes internal orgs
    - Seat: Billable workstations only, excludes internal orgs

    Query Parameters:
        period (optional): Single month in YYYY-MM format
        start_period (optional): Start month for range query (YYYY-MM)
        end_period (optional): End month for range query (YYYY-MM)
        organization_id (optional): Filter by organization (default: 1)

    Note: Either 'period' OR both 'start_period' and 'end_period' must be provided.

    Returns:
        JSON response with per-client seat and endpoint counts.
        - Single period: Returns data object directly
        - Date range: Returns array of period objects in 'periods' field
    """
    from api.api_server import get_session

    period = request.args.get('period')
    start_period = request.args.get('start_period')
    end_period = request.args.get('end_period')
    organization_id = request.args.get('organization_id', 1, type=int)

    # Validate parameters - need either period OR (start_period AND end_period)
    is_range_query = start_period is not None or end_period is not None

    if is_range_query:
        # Range query validation
        if not start_period or not end_period:
            return jsonify({
                "success": False,
                "error": {
                    "code": "INVALID_PARAMETERS",
                    "message": "Both start_period and end_period are required for range queries",
                    "status": 400
                }
            }), 400

        if not validate_period(start_period, 'monthly') or not validate_period(end_period, 'monthly'):
            return jsonify({
                "success": False,
                "error": {
                    "code": "INVALID_PERIOD",
                    "message": "start_period and end_period must be in YYYY-MM format",
                    "status": 400
                }
            }), 400

        if start_period > end_period:
            return jsonify({
                "success": False,
                "error": {
                    "code": "INVALID_PERIOD_RANGE",
                    "message": "start_period must be before or equal to end_period",
                    "status": 400
                }
            }), 400

        periods = get_period_range(start_period, end_period)

        # Limit to 24 months to prevent abuse
        if len(periods) > 24:
            return jsonify({
                "success": False,
                "error": {
                    "code": "RANGE_TOO_LARGE",
                    "message": "Date range cannot exceed 24 months",
                    "status": 400
                }
            }), 400

    else:
        # Single period query
        if not period or not validate_period(period, 'monthly'):
            return jsonify({
                "success": False,
                "error": {
                    "code": "INVALID_PERIOD",
                    "message": "Period parameter required in YYYY-MM format, or provide start_period and end_period",
                    "status": 400
                }
            }), 400

        periods = [period]

    try:
        # Excluded organizations (per STD_SEAT_ENDPOINT_DEFINITIONS.md)
        excluded_orgs = ['Ener Systems, LLC', 'Internal Infrastructure', 'z_Terese Ashley']

        with get_session() as session:
            # Get Ninja vendor (needed for live data queries)
            ninja_vendor = session.query(Vendor).filter_by(name='Ninja').first()
            if not ninja_vendor:
                return jsonify({
                    "success": False,
                    "error": {
                        "code": "VENDOR_NOT_FOUND",
                        "message": "Ninja vendor not found in database",
                        "status": 500
                    }
                }), 500

            # Fetch data for all requested periods
            results = []
            for p in periods:
                period_data = get_devices_for_period(session, p, ninja_vendor.id, excluded_orgs)
                if period_data:
                    results.append(period_data)

            if not results:
                return jsonify({
                    "success": False,
                    "error": {
                        "code": "NO_DATA",
                        "message": f"No data available for the requested period(s). Historical data available from 2024-10, live data from 2025-10.",
                        "status": 404
                    }
                }), 404

            # Return format depends on query type
            if is_range_query:
                return jsonify({
                    "success": True,
                    "data": {
                        "start_period": start_period,
                        "end_period": end_period,
                        "organization_id": organization_id,
                        "periods": results,
                        "periods_returned": len(results),
                        "periods_requested": len(periods)
                    }
                })
            else:
                # Single period - return in original format for backward compatibility
                result = results[0]
                result["organization_id"] = organization_id
                return jsonify({
                    "success": True,
                    "data": result
                })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": {
                "code": "SERVER_ERROR",
                "message": str(e),
                "status": 500
            }
        }), 500


# ============================================================================
# GET /api/qbr/metrics/quarterly
# ============================================================================

@qbr_api.route('/api/qbr/metrics/quarterly', methods=['GET'])
@require_auth
def get_quarterly_metrics():
    """
    Get quarterly QBR metrics with aggregation from monthly data.

    Query Parameters:
        period (optional): Specific period (YYYY-Q1). Returns latest if not specified.
        organization_id (optional): Filter by organization (default: 1)

    Returns:
        JSON response with quarterly aggregated metrics
    """
    from api.api_server import get_session

    period = request.args.get('period')
    organization_id = request.args.get('organization_id', 1, type=int)

    # Validate period if provided
    if period and not validate_period(period, 'quarterly'):
        return jsonify({
            "success": False,
            "error": {
                "code": "INVALID_PERIOD",
                "message": "Period format must be YYYY-Q1, YYYY-Q2, YYYY-Q3, or YYYY-Q4",
                "status": 400
            }
        }), 400

    try:
        with get_session() as session:
            if not period:
                # Get latest quarterly period
                latest = session.query(QBRMetricsMonthly.period)\
                    .filter(QBRMetricsMonthly.organization_id == organization_id)\
                    .order_by(QBRMetricsMonthly.period.desc())\
                    .first()

                if latest:
                    # Convert latest month to quarter
                    year, month = latest[0].split('-')
                    quarter = ((int(month) - 1) // 3) + 1
                    period = f"{year}-Q{quarter}"
                else:
                    return jsonify({
                        "success": False,
                        "error": {
                            "code": "NO_DATA",
                            "message": "No monthly data available",
                            "status": 404
                        }
                    }), 404

            # Get monthly periods for this quarter
            monthly_periods = period_to_months(period)

            # Fetch monthly data for all 3 months
            monthly_data = session.query(QBRMetricsMonthly).filter(
                QBRMetricsMonthly.organization_id == organization_id,
                QBRMetricsMonthly.period.in_(monthly_periods)
            ).order_by(
                QBRMetricsMonthly.period,
                QBRMetricsMonthly.metric_name
            ).all()

            # Group by period and metric
            metrics_by_period = {}
            for metric in monthly_data:
                if metric.period not in metrics_by_period:
                    metrics_by_period[metric.period] = {}
                metrics_by_period[metric.period][metric.metric_name] = metric.metric_value

            # Build aggregated quarterly metrics
            quarterly_metrics = {}

            # Metrics to sum
            sum_metrics = [
                'reactive_tickets_created', 'reactive_tickets_closed', 'reactive_time_spent',
                'nrr', 'mrr', 'orr', 'product_sales', 'misc_revenue', 'total_revenue',
                'employee_expense', 'owner_comp_taxes', 'owner_comp', 'product_cogs',
                'other_expenses', 'total_expenses', 'net_profit',
                'telemarketing_dials', 'first_time_appointments', 'prospects_to_pbr',
                'new_agreements', 'new_mrr', 'lost_mrr'
            ]

            # Metrics to average
            avg_metrics = [
                'endpoints_managed', 'employees', 'technical_employees',
                'seats_managed', 'agreements'
            ]

            # Sum metrics
            for metric_name in sum_metrics:
                total = Decimal('0')
                count = 0
                for period_data in metrics_by_period.values():
                    if metric_name in period_data and period_data[metric_name] is not None:
                        total += period_data[metric_name]
                        count += 1

                if count > 0:
                    quarterly_metrics[metric_name] = float(total)

            # Average metrics
            for metric_name in avg_metrics:
                total = Decimal('0')
                count = 0
                for period_data in metrics_by_period.values():
                    if metric_name in period_data and period_data[metric_name] is not None:
                        total += period_data[metric_name]
                        count += 1

                if count > 0:
                    quarterly_metrics[metric_name] = float(total / count)

            result = {
                "success": True,
                "data": {
                    "period": period,
                    "organization_id": organization_id,
                    "monthly_periods": monthly_periods,
                    "metrics": quarterly_metrics
                }
            }

            return jsonify(result), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": {
                "code": "SERVER_ERROR",
                "message": str(e),
                "status": 500
            }
        }), 500


# ============================================================================
# GET /api/qbr/smartnumbers
# ============================================================================

@qbr_api.route('/api/qbr/smartnumbers', methods=['GET'])
@require_auth
def get_smartnumbers():
    """
    Calculate and return SmartNumbers/KPIs for a quarterly period.

    Query Parameters:
        period (required): Quarterly period (YYYY-Q1, YYYY-Q2, etc.)
        organization_id (optional): Filter by organization (default: 1)

    Returns:
        JSON response with calculated SmartNumbers
    """
    from api.api_server import get_session

    period = request.args.get('period')
    organization_id = request.args.get('organization_id', 1, type=int)

    if not period:
        return jsonify({
            "success": False,
            "error": {
                "code": "MISSING_PERIOD",
                "message": "Period parameter is required (format: YYYY-Q1)",
                "status": 400
            }
        }), 400

    if not validate_period(period, 'quarterly'):
        return jsonify({
            "success": False,
            "error": {
                "code": "INVALID_PERIOD",
                "message": "Period format must be YYYY-Q1, YYYY-Q2, YYYY-Q3, or YYYY-Q4",
                "status": 400
            }
        }), 400

    try:
        with get_session() as session:
            # Get monthly periods for this quarter
            monthly_periods = period_to_months(period)

            # Fetch monthly data for all 3 months
            monthly_data = session.query(QBRMetricsMonthly).filter(
                QBRMetricsMonthly.organization_id == organization_id,
                QBRMetricsMonthly.period.in_(monthly_periods)
            ).order_by(
                QBRMetricsMonthly.period,
                QBRMetricsMonthly.metric_name
            ).all()

            # Group by period and metric
            metrics_by_period = {}
            for metric in monthly_data:
                if metric.period not in metrics_by_period:
                    metrics_by_period[metric.period] = {}
                metrics_by_period[metric.period][metric.metric_name] = metric.metric_value

            # Aggregate to quarterly
            def sum_metric(metric_name):
                return sum(
                    metrics_by_period[p].get(metric_name, Decimal('0'))
                    for p in monthly_periods
                    if p in metrics_by_period
                ) or None

            def avg_metric(metric_name):
                values = [
                    metrics_by_period[p].get(metric_name)
                    for p in monthly_periods
                    if p in metrics_by_period and metrics_by_period[p].get(metric_name) is not None
                ]
                return sum(values) / len(values) if values else None

            # Build QuarterlyMetrics object
            quarterly = QuarterlyMetrics(
                # Summed metrics
                reactive_tickets_created=sum_metric('reactive_tickets_created'),
                reactive_tickets_closed=sum_metric('reactive_tickets_closed'),
                total_time_reactive=sum_metric('reactive_time_spent'),
                nrr=sum_metric('nrr'),
                mrr=sum_metric('mrr'),
                orr=sum_metric('orr'),
                product_sales=sum_metric('product_sales'),
                misc_revenue=sum_metric('misc_revenue'),
                total_revenue=sum_metric('total_revenue'),
                employee_expense=sum_metric('employee_expense'),
                owner_comp_taxes=sum_metric('owner_comp_taxes'),
                owner_comp=sum_metric('owner_comp'),
                product_cogs=sum_metric('product_cogs'),
                other_expenses=sum_metric('other_expenses'),
                total_expenses=sum_metric('total_expenses'),
                net_profit=sum_metric('net_profit'),
                telemarketing_dials=sum_metric('telemarketing_dials'),
                first_time_appointments=sum_metric('first_time_appointments'),
                prospects_to_pbr=sum_metric('prospects_to_pbr'),
                new_agreements=sum_metric('new_agreements'),
                new_mrr=sum_metric('new_mrr'),
                lost_mrr=sum_metric('lost_mrr'),

                # Averaged metrics
                endpoints_managed=avg_metric('endpoints_managed'),
                employees=avg_metric('employees'),
                technical_employees=avg_metric('technical_employees'),
                seats_managed=avg_metric('seats_managed'),
                agreements=avg_metric('agreements'),
            )

            # Calculate SmartNumbers
            calculator = SmartNumbersCalculator()
            smartnumbers = calculator.calculate_quarterly(quarterly)

            # Convert Decimal to float for JSON
            smartnumbers_float = {
                k: float(v) if v is not None else None
                for k, v in smartnumbers.items()
            }

            result = {
                "success": True,
                "data": {
                    "period": period,
                    "organization_id": organization_id,
                    "monthly_periods": monthly_periods,
                    "smartnumbers": smartnumbers_float
                }
            }

            return jsonify(result), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": {
                "code": "SERVER_ERROR",
                "message": str(e),
                "status": 500
            }
        }), 500


# ============================================================================
# GET /api/qbr/thresholds
# ============================================================================

@qbr_api.route('/api/qbr/thresholds', methods=['GET'])
@require_auth
def get_thresholds():
    """
    Get performance thresholds for SmartNumbers.

    Query Parameters:
        organization_id (optional): Filter by organization (default: 1)

    Returns:
        JSON response with performance thresholds
    """
    from api.api_server import get_session

    organization_id = request.args.get('organization_id', 1, type=int)

    try:
        with get_session() as session:
            thresholds = session.query(QBRThresholds).filter(
                QBRThresholds.organization_id == organization_id
            ).order_by(QBRThresholds.metric_name).all()

            result = {
                "success": True,
                "data": {
                    "organization_id": organization_id,
                    "thresholds": [
                        {
                            "metric_name": t.metric_name,
                            "green_min": float(t.green_min) if t.green_min else None,
                            "green_max": float(t.green_max) if t.green_max else None,
                            "yellow_min": float(t.yellow_min) if t.yellow_min else None,
                            "yellow_max": float(t.yellow_max) if t.yellow_max else None,
                            "red_threshold": float(t.red_threshold) if t.red_threshold else None,
                            "notes": t.notes
                        }
                        for t in thresholds
                    ]
                }
            }

            return jsonify(result), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": {
                "code": "SERVER_ERROR",
                "message": str(e),
                "status": 500
            }
        }), 500


# ============================================================================
# POST /api/qbr/thresholds
# ============================================================================

@qbr_api.route('/api/qbr/thresholds', methods=['POST'])
@require_auth
def update_thresholds():
    """
    Update performance thresholds for SmartNumbers.

    Request Body:
        {
            "organization_id": 1,
            "thresholds": [
                {
                    "metric_name": "tickets_per_tech_per_month",
                    "green_min": 50,
                    "green_max": 70,
                    "yellow_min": 40,
                    "yellow_max": 80,
                    "red_threshold": 90,
                    "notes": "Target range based on industry standards"
                }
            ]
        }

    Returns:
        JSON response with updated thresholds
    """
    from api.api_server import get_session

    data = request.get_json()

    if not data or 'thresholds' not in data:
        return jsonify({
            "success": False,
            "error": {
                "code": "MISSING_DATA",
                "message": "Request body must include 'thresholds' array",
                "status": 400
            }
        }), 400

    organization_id = data.get('organization_id', 1)

    try:
        with get_session() as session:
            updated_count = 0

            for threshold_data in data['thresholds']:
                metric_name = threshold_data.get('metric_name')

                if not metric_name:
                    continue

                # Upsert threshold
                threshold = session.query(QBRThresholds).filter(
                    QBRThresholds.organization_id == organization_id,
                    QBRThresholds.metric_name == metric_name
                ).first()

                if threshold:
                    # Update existing
                    threshold.green_min = threshold_data.get('green_min')
                    threshold.green_max = threshold_data.get('green_max')
                    threshold.yellow_min = threshold_data.get('yellow_min')
                    threshold.yellow_max = threshold_data.get('yellow_max')
                    threshold.red_threshold = threshold_data.get('red_threshold')
                    threshold.notes = threshold_data.get('notes')
                else:
                    # Create new
                    threshold = QBRThresholds(
                        organization_id=organization_id,
                        metric_name=metric_name,
                        green_min=threshold_data.get('green_min'),
                        green_max=threshold_data.get('green_max'),
                        yellow_min=threshold_data.get('yellow_min'),
                        yellow_max=threshold_data.get('yellow_max'),
                        red_threshold=threshold_data.get('red_threshold'),
                        notes=threshold_data.get('notes')
                    )
                    session.add(threshold)

                updated_count += 1

            session.commit()

            result = {
                "success": True,
                "data": {
                    "organization_id": organization_id,
                    "updated_count": updated_count
                }
            }

            return jsonify(result), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": {
                "code": "SERVER_ERROR",
                "message": str(e),
                "status": 500
            }
        }), 500


# ============================================================================
# POST /api/qbr/metrics/manual
# ============================================================================

@qbr_api.route('/api/qbr/metrics/manual', methods=['POST'])
@require_auth
def manual_metrics_entry():
    """
    Manually enter or update metrics for a period.

    Request Body:
        {
            "period": "2025-01",
            "organization_id": 1,
            "metrics": [
                {
                    "metric_name": "employees",
                    "metric_value": 8.5,
                    "vendor_id": null,
                    "notes": "Manual entry for January 2025"
                }
            ]
        }

    Returns:
        JSON response with updated metrics
    """
    from api.api_server import get_session

    data = request.get_json()

    if not data or 'period' not in data or 'metrics' not in data:
        return jsonify({
            "success": False,
            "error": {
                "code": "MISSING_DATA",
                "message": "Request body must include 'period' and 'metrics'",
                "status": 400
            }
        }), 400

    period = data['period']
    organization_id = data.get('organization_id', 1)

    if not validate_period(period, 'monthly'):
        return jsonify({
            "success": False,
            "error": {
                "code": "INVALID_PERIOD",
                "message": "Period format must be YYYY-MM",
                "status": 400
            }
        }), 400

    try:
        with get_session() as session:
            # Get or create the Manual vendor for manual entries
            from storage.schema import Vendor
            manual_vendor = session.query(Vendor).filter_by(name='Manual').first()
            if not manual_vendor:
                manual_vendor = Vendor(name='Manual')
                session.add(manual_vendor)
                session.flush()
            default_vendor_id = manual_vendor.id

            updated_count = 0

            for metric_data in data['metrics']:
                metric_name = metric_data.get('metric_name')
                metric_value = metric_data.get('metric_value')

                if not metric_name:
                    continue

                # Use provided vendor_id or default to Manual vendor
                vendor_id = metric_data.get('vendor_id') or default_vendor_id

                # Upsert metric - check for existing with same vendor or with manual data_source
                metric = session.query(QBRMetricsMonthly).filter(
                    QBRMetricsMonthly.organization_id == organization_id,
                    QBRMetricsMonthly.period == period,
                    QBRMetricsMonthly.metric_name == metric_name,
                    QBRMetricsMonthly.data_source == 'manual'
                ).first()

                if metric:
                    # Update existing (only if it's not a collected metric or if forced)
                    if metric.data_source != 'collected' or data.get('force_update', False):
                        metric.metric_value = metric_value
                        metric.data_source = 'manual'
                        metric.notes = metric_data.get('notes')
                        updated_count += 1
                else:
                    # Create new
                    metric = QBRMetricsMonthly(
                        organization_id=organization_id,
                        period=period,
                        metric_name=metric_name,
                        metric_value=metric_value,
                        vendor_id=vendor_id,
                        data_source='manual',
                        notes=metric_data.get('notes')
                    )
                    session.add(metric)
                    updated_count += 1

            session.commit()

            result = {
                "success": True,
                "data": {
                    "period": period,
                    "organization_id": organization_id,
                    "updated_count": updated_count
                }
            }

            return jsonify(result), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": {
                "code": "SERVER_ERROR",
                "message": str(e),
                "status": 500
            }
        }), 500


# ============================================================================
# POST /api/qbr/expenses/calculate
# ============================================================================

@qbr_api.route('/api/qbr/expenses/calculate', methods=['POST'])
@require_auth
def calculate_expenses():
    """
    Calculate and store expense breakdown for a period.

    Takes CFO manual inputs (owner_comp, owner_comp_taxes), fetches QuickBooks
    data (payroll_total, total_expenses_qb), calculates derived values
    (employee_expense, other_expenses), and stores everything.

    Request Body:
        {
            "period": "2025-11",
            "organization_id": 1,
            "owner_comp": 15000.00,
            "owner_comp_taxes": 5000.00
        }

    Formulas:
        employee_expense = payroll_total - owner_comp_taxes - owner_comp
        other_expenses = total_expenses_qb - employee_expense - owner_comp_taxes - owner_comp
        total_expenses = employee_expense + other_expenses + owner_comp_taxes + owner_comp + product_cogs - uncategorized_expenses

    Note: uncategorized_expenses is QuickBooks account 6999; most months it will be zero.

    Returns:
        JSON response with complete expense breakdown
    """
    from api.api_server import get_session

    data = request.get_json()

    if not data or 'period' not in data:
        return jsonify({
            "success": False,
            "error": {
                "code": "MISSING_DATA",
                "message": "Request body must include 'period'",
                "status": 400
            }
        }), 400

    period = data['period']
    organization_id = data.get('organization_id', 1)
    owner_comp = Decimal(str(data.get('owner_comp', 0)))
    owner_comp_taxes = Decimal(str(data.get('owner_comp_taxes', 0)))

    if not validate_period(period, 'monthly'):
        return jsonify({
            "success": False,
            "error": {
                "code": "INVALID_PERIOD",
                "message": "Period format must be YYYY-MM",
                "status": 400
            }
        }), 400

    try:
        with get_session() as session:
            # Get or create the CFO vendor for manual/calculated entries
            from storage.schema import Vendor
            cfo_vendor = session.query(Vendor).filter_by(name='CFO').first()
            if not cfo_vendor:
                cfo_vendor = Vendor(name='CFO')
                session.add(cfo_vendor)
                session.flush()
            cfo_vendor_id = cfo_vendor.id

            # Fetch QuickBooks data for this period
            qb_metrics = session.query(QBRMetricsMonthly).filter(
                QBRMetricsMonthly.organization_id == organization_id,
                QBRMetricsMonthly.period == period,
                QBRMetricsMonthly.data_source == 'quickbooks'
            ).all()

            # Build lookup dict
            qb_data = {m.metric_name: m.metric_value for m in qb_metrics}

            # Get required QuickBooks values
            payroll_total = qb_data.get('payroll_total', Decimal('0'))
            product_cogs = qb_data.get('product_cogs', Decimal('0'))
            total_expenses_qb = qb_data.get('total_expenses_qb', Decimal('0'))
            uncategorized_expenses = qb_data.get('uncategorized_expenses', Decimal('0'))

            if payroll_total == 0 or total_expenses_qb == 0:
                return jsonify({
                    "success": False,
                    "error": {
                        "code": "MISSING_QB_DATA",
                        "message": f"QuickBooks data not found for period {period}. "
                                   f"payroll_total={payroll_total}, total_expenses_qb={total_expenses_qb}. "
                                   "Please run QBWC sync first.",
                        "status": 400
                    }
                }), 400

            # Calculate derived values
            # employee_expense = payroll_total - owner_comp_taxes - owner_comp
            # other_expenses = total_expenses_qb - employee_expense - owner_comp_taxes - owner_comp
            # NOTE: product_cogs is NOT subtracted from other_expenses per user's formula
            employee_expense = payroll_total - owner_comp_taxes - owner_comp
            other_expenses = total_expenses_qb - employee_expense - owner_comp_taxes - owner_comp

            # Calculate total_expenses as sum of all expense components minus uncategorized
            # Formula: employee_expense + other_expenses + owner_comp + owner_comp_taxes + product_cogs - uncategorized_expenses
            # Note: uncategorized_expenses (account 6999) is subtracted; most months it will be zero
            total_expenses_calculated = employee_expense + other_expenses + owner_comp + owner_comp_taxes + product_cogs - uncategorized_expenses

            # Prepare all expense metrics to store
            expense_metrics = {
                'owner_comp': owner_comp,
                'owner_comp_taxes': owner_comp_taxes,
                'employee_expense': employee_expense,
                'other_expenses': other_expenses,
                # Also store the QB values under canonical names for consistency
                'payroll_total': payroll_total,
                'product_cogs': product_cogs,
                'uncategorized_expenses': uncategorized_expenses,  # Account 6999, subtracted from total
                'total_expenses': total_expenses_calculated,  # Calculated sum minus uncategorized
            }

            # Store/update each metric
            stored_count = 0
            for metric_name, metric_value in expense_metrics.items():
                # Determine data source based on metric type
                if metric_name in ['owner_comp', 'owner_comp_taxes']:
                    source = 'manual'
                elif metric_name in ['employee_expense', 'other_expenses', 'total_expenses']:
                    source = 'calculated'  # total_expenses is calculated as sum of all components
                else:
                    source = 'quickbooks'

                existing = session.query(QBRMetricsMonthly).filter(
                    QBRMetricsMonthly.organization_id == organization_id,
                    QBRMetricsMonthly.period == period,
                    QBRMetricsMonthly.metric_name == metric_name,
                    QBRMetricsMonthly.vendor_id == cfo_vendor_id,
                    QBRMetricsMonthly.data_source == source
                ).first()

                if existing:
                    existing.metric_value = metric_value
                    existing.notes = f"Calculated via /api/qbr/expenses/calculate"
                else:
                    new_metric = QBRMetricsMonthly(
                        organization_id=organization_id,
                        period=period,
                        vendor_id=cfo_vendor_id,
                        metric_name=metric_name,
                        metric_value=metric_value,
                        data_source=source,
                        notes=f"Calculated via /api/qbr/expenses/calculate"
                    )
                    session.add(new_metric)
                stored_count += 1

            session.commit()

            # Return complete expense breakdown
            result = {
                "success": True,
                "data": {
                    "period": period,
                    "organization_id": organization_id,
                    "inputs": {
                        "from_quickbooks": {
                            "payroll_total": float(payroll_total),
                            "product_cogs": float(product_cogs),
                            "total_expenses_qb": float(total_expenses_qb),
                            "uncategorized_expenses": float(uncategorized_expenses)
                        },
                        "from_cfo": {
                            "owner_comp": float(owner_comp),
                            "owner_comp_taxes": float(owner_comp_taxes)
                        }
                    },
                    "calculated": {
                        "employee_expense": float(employee_expense),
                        "other_expenses": float(other_expenses),
                        "total_expenses": float(total_expenses_calculated)
                    },
                    "formulas": {
                        "employee_expense": "payroll_total - owner_comp_taxes - owner_comp",
                        "other_expenses": "total_expenses_qb - employee_expense - owner_comp_taxes - owner_comp",
                        "total_expenses": "employee_expense + other_expenses + owner_comp + owner_comp_taxes + product_cogs - uncategorized_expenses"
                    },
                    "stored_metrics": stored_count
                }
            }

            return jsonify(result), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": {
                "code": "SERVER_ERROR",
                "message": str(e),
                "status": 500
            }
        }), 500


# ============================================================================
# TEMPORARY TEST ENDPOINT - NO AUTH (for testing backfilled data)
# ============================================================================

@qbr_api.route('/api/qbr/test/smartnumbers', methods=['GET'])
def test_smartnumbers_noauth():
    """
    TEMPORARY: Test endpoint to verify Smart Numbers without authentication.
    Returns SmartNumbers for specified quarter.

    Query Parameters:
        period: Quarter (e.g., '2024-Q1', '2025-Q4')
    """
    from api.api_server import get_session
    from sqlalchemy import text

    period = request.args.get('period', '2024-Q1')
    organization_id = int(request.args.get('organization_id', 1))

    try:
        # Verify period format
        if not validate_period(period, 'quarterly'):
            return jsonify({
                "success": False,
                "error": {
                    "code": "INVALID_PERIOD",
                    "message": f"Invalid period format: {period}. Use YYYY-Q1/Q2/Q3/Q4",
                    "status": 400
                }
            }), 400

        # Get monthly periods for this quarter
        monthly_periods = period_to_months(period)

        # Fetch and aggregate metrics
        with get_session() as session:
            # Fetch all monthly metrics for this quarter
            from decimal import Decimal
            monthly_metrics = []
            for monthly_period in monthly_periods:
                metrics_dict = {}
                query = text("""
                    SELECT metric_name, metric_value
                    FROM qbr_metrics_monthly
                    WHERE period = :period AND organization_id = :org_id
                """)
                results = session.execute(query, {'period': monthly_period, 'org_id': organization_id}).fetchall()
                for row in results:
                    # Keep as Decimal - SmartNumbers calculator expects Decimal type
                    metrics_dict[row[0]] = row[1]
                if metrics_dict:
                    monthly_metrics.append(metrics_dict)

            # Helper functions for aggregation - return Decimal type
            def sum_metric(name):
                values = [m.get(name) for m in monthly_metrics if m.get(name) is not None]
                return sum(values, Decimal('0')) if values else None

            def avg_metric(name):
                values = [m.get(name) for m in monthly_metrics if m.get(name) is not None]
                if not values:
                    return None
                return sum(values, Decimal('0')) / Decimal(str(len(values)))

            # Build QuarterlyMetrics object
            quarterly = QuarterlyMetrics(
                # Summed metrics
                reactive_tickets_created=sum_metric('reactive_tickets_created'),
                reactive_tickets_closed=sum_metric('reactive_tickets_closed'),
                total_time_reactive=sum_metric('reactive_time_spent'),
                nrr=sum_metric('nrr'),
                mrr=sum_metric('mrr'),
                orr=sum_metric('orr'),
                product_sales=sum_metric('product_sales'),
                misc_revenue=sum_metric('misc_revenue'),
                total_revenue=sum_metric('total_revenue'),
                employee_expense=sum_metric('employee_expense'),
                owner_comp_taxes=sum_metric('owner_comp_taxes'),
                owner_comp=sum_metric('owner_comp'),
                product_cogs=sum_metric('product_cogs'),
                other_expenses=sum_metric('other_expenses'),
                total_expenses=sum_metric('total_expenses'),
                net_profit=sum_metric('net_profit'),
                telemarketing_dials=sum_metric('telemarketing_dials'),
                first_time_appointments=sum_metric('first_time_appointments'),
                prospects_to_pbr=sum_metric('prospects_to_pbr'),
                new_agreements=sum_metric('new_agreements'),
                new_mrr=sum_metric('new_mrr'),
                lost_mrr=sum_metric('lost_mrr'),
                # Averaged metrics
                endpoints_managed=avg_metric('endpoints_managed'),
                employees=avg_metric('employees'),
                technical_employees=avg_metric('technical_employees'),
                seats_managed=avg_metric('seats_managed'),
                agreements=avg_metric('agreements'),
            )

            # Calculate SmartNumbers
            calculator = SmartNumbersCalculator()
            smartnumbers = calculator.calculate_quarterly(quarterly)

            return jsonify({
                "success": True,
                "note": "TEMPORARY TEST ENDPOINT - NO AUTHENTICATION REQUIRED",
                "data": {
                    "period": period,
                    "organization_id": organization_id,
                    "monthly_periods": monthly_periods,
                    "smartnumbers": {k: float(v) if v is not None else None for k, v in smartnumbers.items()}
                }
            })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": {
                "code": "SERVER_ERROR",
                "message": str(e),
                "status": 500
            }
        }), 500


# Export blueprint
__all__ = ['qbr_api']

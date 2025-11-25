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

    Returns:
        JSON response with monthly metrics
    """
    from api.api_server import get_session

    period = request.args.get('period')
    organization_id = request.args.get('organization_id', 1, type=int)
    vendor_id = request.args.get('vendor_id', type=int)
    metric_name = request.args.get('metric_name')

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

            if vendor_id:
                query = query.filter(QBRMetricsMonthly.vendor_id == vendor_id)

            if metric_name:
                query = query.filter(QBRMetricsMonthly.metric_name == metric_name)

            metrics = query.order_by(
                QBRMetricsMonthly.period.desc(),
                QBRMetricsMonthly.vendor_id,
                QBRMetricsMonthly.metric_name
            ).all()

            result = {
                "success": True,
                "data": {
                    "period": period or (metrics[0].period if metrics else None),
                    "organization_id": organization_id,
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

@qbr_api.route('/api/qbr/metrics/devices-by-client', methods=['GET'])
@require_auth
def get_devices_by_client():
    """
    Get seat and endpoint counts by client for a given month.

    Data Sources:
    - Oct 2025 onwards: Live device_snapshot data from Ninja collector
    - Before Oct 2025: Historical data from qbr_client_metrics table (imported from EnerCare)

    Definitions (per STD_SEAT_ENDPOINT_DEFINITIONS.md):
    - Endpoint: All billable devices (workstations + servers), excludes internal orgs
    - Seat: Billable workstations only, excludes internal orgs

    Query Parameters:
        period (required): Month in format YYYY-MM
        organization_id (optional): Filter by organization (default: 1)

    Returns:
        JSON response with per-client seat and endpoint counts
    """
    from api.api_server import get_session

    period = request.args.get('period')
    organization_id = request.args.get('organization_id', 1, type=int)

    # Validate period parameter (required)
    if not period or not validate_period(period, 'monthly'):
        return jsonify({
            "success": False,
            "error": {
                "code": "INVALID_PERIOD",
                "message": "Period parameter required in YYYY-MM format",
                "status": 400
            }
        }), 400

    try:
        # Calculate last day of month for snapshot_date
        year, month = map(int, period.split('-'))
        if month == 12:
            last_day = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = date(year, month + 1, 1) - timedelta(days=1)

        # Determine data source based on period
        # Live Ninja data available from 2025-10-08 onwards
        use_historical = period < '2025-10'

        with get_session() as session:
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
                    return jsonify({
                        "success": False,
                        "error": {
                            "code": "NO_DATA",
                            "message": f"No historical data available for {period}. Data available from 2024-10 onwards.",
                            "status": 404
                        }
                    }), 404

                clients = [
                    {
                        'client_name': row[0],
                        'seats': row[1] or 0,
                        'endpoints': row[2] or 0
                    }
                    for row in results
                ]

                total_seats = sum(c['seats'] for c in clients)
                total_endpoints = sum(c['endpoints'] for c in clients)

                return jsonify({
                    "success": True,
                    "data": {
                        "period": period,
                        "organization_id": organization_id,
                        "data_source": "historical",
                        "clients": clients,
                        "total_seats": total_seats,
                        "total_endpoints": total_endpoints
                    }
                })

            else:
                # Use live device_snapshot data
                # Excluded organizations (per STD_SEAT_ENDPOINT_DEFINITIONS.md)
                excluded_orgs = ['Ener Systems, LLC', 'Internal Infrastructure', 'z_Terese Ashley']

                # Get Ninja vendor
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

                # Check if we have data for this date
                data_exists = session.query(DeviceSnapshot).filter(
                    DeviceSnapshot.snapshot_date == last_day,
                    DeviceSnapshot.vendor_id == ninja_vendor.id
                ).first()

                if not data_exists:
                    return jsonify({
                        "success": False,
                        "error": {
                            "code": "NO_DATA",
                            "message": f"No device snapshot data available for {last_day.isoformat()}. Data available from 2025-10-08 onwards.",
                            "status": 404
                        }
                    }), 404

                # Query ENDPOINTS (all billable devices, exclude internal orgs)
                endpoint_results = session.query(
                    DeviceSnapshot.organization_name,
                    func.count().label('endpoints')
                ).filter(
                    DeviceSnapshot.snapshot_date == last_day,
                    DeviceSnapshot.vendor_id == ninja_vendor.id,
                    DeviceSnapshot.billable_status_name == 'billable',
                    ~DeviceSnapshot.organization_name.in_(excluded_orgs)
                ).group_by(DeviceSnapshot.organization_name).all()

                endpoints_by_client = {r.organization_name: r.endpoints for r in endpoint_results}

                # Query SEATS (billable workstations only, exclude internal orgs)
                seat_results = session.query(
                    DeviceSnapshot.organization_name,
                    func.count().label('seats')
                ).filter(
                    DeviceSnapshot.snapshot_date == last_day,
                    DeviceSnapshot.vendor_id == ninja_vendor.id,
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

                total_seats = sum(seats_by_client.values())
                total_endpoints = sum(endpoints_by_client.values())

                return jsonify({
                    "success": True,
                    "data": {
                        "period": period,
                        "organization_id": organization_id,
                        "data_source": "live",
                        "snapshot_date": last_day.isoformat(),
                        "clients": clients,
                        "total_seats": total_seats,
                        "total_endpoints": total_endpoints
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
            updated_count = 0

            for metric_data in data['metrics']:
                metric_name = metric_data.get('metric_name')
                metric_value = metric_data.get('metric_value')

                if not metric_name:
                    continue

                vendor_id = metric_data.get('vendor_id')

                # Upsert metric
                metric = session.query(QBRMetricsMonthly).filter(
                    QBRMetricsMonthly.organization_id == organization_id,
                    QBRMetricsMonthly.period == period,
                    QBRMetricsMonthly.metric_name == metric_name,
                    QBRMetricsMonthly.vendor_id == vendor_id if vendor_id else QBRMetricsMonthly.vendor_id.is_(None)
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

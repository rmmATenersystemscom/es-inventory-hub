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

# Intermediate/working metrics - used for calculations but NOT returned to dashboard
# These are internal values needed to compute display metrics
INTERMEDIATE_METRICS = {
    'payroll_total',        # Used to calculate employee_expense
    'total_expenses_qb',    # Raw QB value, used in other_expenses calculation
    'total_income',         # Raw QB value
    'uncategorized_expenses',  # Subtracted from total_expenses
}

# Protected metrics - cannot be modified via API
# These are collected/calculated by the QBR collector with specific filtering logic
# and have been manually corrected for historical accuracy
PROTECTED_METRICS = {
    'endpoints_managed',    # Ninja billable device count - collected by QBR Ninja collector
    'seats_managed',        # Ninja BHAG calculation - collected by QBR Ninja collector
}

# Metric descriptions - explains the source and calculation for each metric
# These are included in API responses to help Dashboard AI understand the data
METRIC_DESCRIPTIONS = {
    # Ninja collected metrics (protected)
    'endpoints_managed': (
        "Billable Ninja devices. Excludes internal orgs (Ener Systems LLC, "
        "Internal Infrastructure, z_Terese Ashley) and spare devices."
    ),
    'seats_managed': (
        "BHAG calculation: Total Ninja devices minus exclusions. "
        "Excludes node_class (VMWARE_VM_GUEST, WINDOWS_SERVER, VMWARE_VM_HOST), "
        "spare devices (name/location contains 'spare'), and internal orgs."
    ),

    # QuickBooks revenue metrics
    'nrr': "QuickBooks: Non-Recurring Revenue, Professional Services accounts.",
    'mrr': "QuickBooks: Monthly Recurring Revenue, Managed Services accounts.",
    'orr': "QuickBooks: Other Recurring Revenue, Annual Revenue accounts.",
    'product_sales': "Calculated: Total Income minus NRR, MRR, and ORR.",
    'misc_revenue': "QuickBooks: Other Income accounts.",
    'total_revenue': "Calculated: NRR + MRR + ORR + Product Sales + Misc Revenue.",
    'total_income': "QuickBooks: Total Income subtotal (intermediate value).",

    # QuickBooks expense inputs
    'payroll_total': "QuickBooks: Payroll Expenses subtotal (intermediate value).",
    'product_cogs': "QuickBooks: Cost of Goods Sold accounts.",
    'total_expenses_qb': "QuickBooks: Total Expenses subtotal (intermediate value).",
    'uncategorized_expenses': "QuickBooks: Uncategorized Expenses - subtracted from total.",

    # Calculated expense metrics
    'employee_expense': "Formula: payroll_total - owner_comp_taxes - owner_comp",
    'other_expenses': "Calculated: Total QB Expenses minus Employee Expense, Owner Comp, and Owner Taxes. Does NOT include COGS.",
    'total_expenses': (
        "Formula: employee_expense + other_expenses + owner_comp + owner_comp_taxes "
        "+ product_cogs - uncategorized_expenses"
    ),
    'net_profit': "Formula: total_revenue - total_expenses",

    # CFO manual entry metrics
    'owner_comp': "Owner compensation - manual entry from CFO.",
    'owner_comp_taxes': "Owner compensation taxes - manual entry from CFO.",

    # Staffing metrics (manual entry)
    'employees': "Total number of employees - manual entry.",
    'technical_employees': "Number of technical/service employees - manual entry.",
    'agreements': "Number of active managed service agreements - manual entry.",

    # ConnectWise ticket metrics
    'reactive_tickets_created': "Reactive tickets opened during the period from ConnectWise.",
    'reactive_tickets_closed': "Reactive tickets closed during the period from ConnectWise.",
    'reactive_time_spent': "Total hours spent on reactive tickets from ConnectWise.",

    # Sales/marketing metrics (manual entry)
    'telemarketing_dials': "Number of outbound telemarketing calls made - manual entry.",
    'first_time_appointments': "Number of first-time prospect appointments - manual entry.",
    'prospects_to_pbr': "Prospects converted to PBR (Potential Business Review) - manual entry.",
    'new_agreements': "New managed service agreements signed - manual entry.",
    'new_mrr': "New Monthly Recurring Revenue added - manual entry.",
    'lost_mrr': "Monthly Recurring Revenue lost (churn) - manual entry.",
}


def get_metric_description(metric_name: str) -> Optional[str]:
    """Get the description for a metric, or None if not defined."""
    return METRIC_DESCRIPTIONS.get(metric_name)


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

            # Exclude intermediate/working metrics from dashboard results
            query = query.filter(
                ~QBRMetricsMonthly.metric_name.in_(INTERMEDIATE_METRICS)
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
                            "description": get_metric_description(m.metric_name),
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

            # Fetch monthly data for all 3 months (excluding intermediate metrics)
            monthly_data = session.query(QBRMetricsMonthly).filter(
                QBRMetricsMonthly.organization_id == organization_id,
                QBRMetricsMonthly.period.in_(monthly_periods),
                ~QBRMetricsMonthly.metric_name.in_(INTERMEDIATE_METRICS)
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

            # Build metrics with descriptions
            metrics_with_descriptions = [
                {
                    "metric_name": name,
                    "metric_value": value,
                    "description": get_metric_description(name),
                    "aggregation": "sum" if name in sum_metrics else "average"
                }
                for name, value in quarterly_metrics.items()
            ]

            result = {
                "success": True,
                "data": {
                    "period": period,
                    "organization_id": organization_id,
                    "monthly_periods": monthly_periods,
                    "metrics": metrics_with_descriptions
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

            # Fetch monthly data for all 3 months (excluding intermediate metrics)
            monthly_data = session.query(QBRMetricsMonthly).filter(
                QBRMetricsMonthly.organization_id == organization_id,
                QBRMetricsMonthly.period.in_(monthly_periods),
                ~QBRMetricsMonthly.metric_name.in_(INTERMEDIATE_METRICS)
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

    # Check for protected metrics
    protected_in_request = [
        m.get('metric_name') for m in data['metrics']
        if m.get('metric_name') in PROTECTED_METRICS
    ]
    if protected_in_request:
        return jsonify({
            "success": False,
            "error": {
                "code": "PROTECTED_METRIC",
                "message": f"Cannot modify protected metrics via API: {', '.join(protected_in_request)}. "
                           f"These metrics are managed by the QBR Ninja collector.",
                "status": 403
            }
        }), 403

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
# METRIC DEFINITIONS ENDPOINT - For Dashboard AI Tooltips
# ============================================================================

# Complete metric metadata for Dashboard AI
METRIC_METADATA = {
    # Support Tickets
    'reactive_tickets_created': {
        'label': 'Reactive Tickets Opened',
        'category': 'Support Tickets',
        'format': 'number',
        'source': 'connectwise',
        'is_editable': False,
        'is_calculated': False,
        'formula': None,
        'components': []
    },
    'reactive_tickets_closed': {
        'label': 'Reactive Tickets Closed',
        'category': 'Support Tickets',
        'format': 'number',
        'source': 'connectwise',
        'is_editable': False,
        'is_calculated': False,
        'formula': None,
        'components': []
    },
    'reactive_time_spent': {
        'label': 'Reactive Hours',
        'category': 'Support Tickets',
        'format': 'number',
        'source': 'connectwise',
        'is_editable': False,
        'is_calculated': False,
        'formula': None,
        'components': []
    },

    # Device Metrics
    'endpoints_managed': {
        'label': 'Billable Ninja Devices',
        'category': 'Devices',
        'format': 'number',
        'source': 'ninja',
        'is_editable': False,
        'is_calculated': False,
        'formula': None,
        'components': []
    },
    'seats_managed': {
        'label': 'Total Endpoints (BHAG)',
        'category': 'Devices',
        'format': 'number',
        'source': 'ninja',
        'is_editable': False,
        'is_calculated': False,
        'formula': None,
        'components': []
    },

    # Revenue
    'nrr': {
        'label': 'Non-Recurring Revenue',
        'category': 'Revenue',
        'format': 'currency',
        'source': 'quickbooks',
        'is_editable': False,
        'is_calculated': False,
        'formula': None,
        'components': []
    },
    'mrr': {
        'label': 'Monthly Recurring Revenue',
        'category': 'Revenue',
        'format': 'currency',
        'source': 'quickbooks',
        'is_editable': False,
        'is_calculated': False,
        'formula': None,
        'components': []
    },
    'orr': {
        'label': 'Other Recurring Revenue',
        'category': 'Revenue',
        'format': 'currency',
        'source': 'quickbooks',
        'is_editable': False,
        'is_calculated': False,
        'formula': None,
        'components': []
    },
    'product_sales': {
        'label': 'Product Sales',
        'category': 'Revenue',
        'format': 'currency',
        'source': 'calculated',
        'is_editable': False,
        'is_calculated': True,
        'formula': 'total_income - nrr - mrr - orr',
        'components': ['total_income', 'nrr', 'mrr', 'orr']
    },
    'misc_revenue': {
        'label': 'Miscellaneous Revenue',
        'category': 'Revenue',
        'format': 'currency',
        'source': 'quickbooks',
        'is_editable': False,
        'is_calculated': False,
        'formula': None,
        'components': []
    },
    'total_revenue': {
        'label': 'Total Revenue',
        'category': 'Revenue',
        'format': 'currency',
        'source': 'calculated',
        'is_editable': False,
        'is_calculated': True,
        'formula': 'nrr + mrr + orr + product_sales + misc_revenue',
        'components': ['nrr', 'mrr', 'orr', 'product_sales', 'misc_revenue']
    },

    # Expenses
    'employee_expense': {
        'label': 'Employee Expense',
        'category': 'Expenses',
        'format': 'currency',
        'source': 'calculated',
        'is_editable': False,
        'is_calculated': True,
        'formula': 'payroll_total - owner_comp - owner_comp_taxes',
        'components': ['payroll_total', 'owner_comp', 'owner_comp_taxes']
    },
    'owner_comp': {
        'label': 'Owner Compensation',
        'category': 'Expenses',
        'format': 'currency',
        'source': 'manual',
        'is_editable': True,
        'is_calculated': False,
        'formula': None,
        'components': []
    },
    'owner_comp_taxes': {
        'label': 'Owner Comp Taxes',
        'category': 'Expenses',
        'format': 'currency',
        'source': 'manual',
        'is_editable': True,
        'is_calculated': False,
        'formula': None,
        'components': []
    },
    'product_cogs': {
        'label': 'Product COGS',
        'category': 'Expenses',
        'format': 'currency',
        'source': 'quickbooks',
        'is_editable': False,
        'is_calculated': False,
        'formula': None,
        'components': []
    },
    'other_expenses': {
        'label': 'All Other Expenses',
        'category': 'Expenses',
        'format': 'currency',
        'source': 'calculated',
        'is_editable': False,
        'is_calculated': True,
        'formula': 'total_expenses_qb - employee_expense - owner_comp - owner_comp_taxes',
        'components': ['total_expenses_qb', 'employee_expense', 'owner_comp', 'owner_comp_taxes']
    },
    'total_expenses': {
        'label': 'Total Expenses',
        'category': 'Expenses',
        'format': 'currency',
        'source': 'calculated',
        'is_editable': False,
        'is_calculated': True,
        'formula': 'employee_expense + other_expenses + owner_comp + owner_comp_taxes + product_cogs - uncategorized_expenses',
        'components': ['employee_expense', 'other_expenses', 'owner_comp', 'owner_comp_taxes', 'product_cogs', 'uncategorized_expenses']
    },

    # Profit
    'net_profit': {
        'label': 'Net Profit',
        'category': 'Profit',
        'format': 'currency',
        'source': 'calculated',
        'is_editable': False,
        'is_calculated': True,
        'formula': 'total_revenue - total_expenses',
        'components': ['total_revenue', 'total_expenses']
    },

    # Staffing
    'employees': {
        'label': 'Total Employees',
        'category': 'General',
        'format': 'number',
        'source': 'manual',
        'is_editable': True,
        'is_calculated': False,
        'formula': None,
        'components': []
    },
    'technical_employees': {
        'label': 'Technical Employees',
        'category': 'General',
        'format': 'number',
        'source': 'manual',
        'is_editable': True,
        'is_calculated': False,
        'formula': None,
        'components': []
    },
    'agreements': {
        'label': 'MSA Agreements',
        'category': 'General',
        'format': 'number',
        'source': 'manual',
        'is_editable': True,
        'is_calculated': False,
        'formula': None,
        'components': []
    },

    # Sales/Marketing
    'telemarketing_dials': {
        'label': 'Telemarketing Dials',
        'category': 'Sales',
        'format': 'number',
        'source': 'manual',
        'is_editable': True,
        'is_calculated': False,
        'formula': None,
        'components': []
    },
    'first_time_appointments': {
        'label': 'First Time Appointments',
        'category': 'Sales',
        'format': 'number',
        'source': 'manual',
        'is_editable': True,
        'is_calculated': False,
        'formula': None,
        'components': []
    },
    'prospects_to_pbr': {
        'label': 'Prospects to PBR',
        'category': 'Sales',
        'format': 'number',
        'source': 'manual',
        'is_editable': True,
        'is_calculated': False,
        'formula': None,
        'components': []
    },
    'new_agreements': {
        'label': 'New Agreements',
        'category': 'Sales',
        'format': 'number',
        'source': 'manual',
        'is_editable': True,
        'is_calculated': False,
        'formula': None,
        'components': []
    },
    'new_mrr': {
        'label': 'New MRR',
        'category': 'Sales',
        'format': 'currency',
        'source': 'manual',
        'is_editable': True,
        'is_calculated': False,
        'formula': None,
        'components': []
    },
    'lost_mrr': {
        'label': 'Lost MRR',
        'category': 'Sales',
        'format': 'currency',
        'source': 'manual',
        'is_editable': True,
        'is_calculated': False,
        'formula': None,
        'components': []
    },

    # Intermediate/hidden metrics
    'total_income': {
        'label': 'Total Income (QB)',
        'category': 'Intermediate',
        'format': 'currency',
        'source': 'quickbooks',
        'is_editable': False,
        'is_calculated': False,
        'formula': None,
        'components': []
    },
    'payroll_total': {
        'label': 'Payroll Total (QB)',
        'category': 'Intermediate',
        'format': 'currency',
        'source': 'quickbooks',
        'is_editable': False,
        'is_calculated': False,
        'formula': None,
        'components': []
    },
    'total_expenses_qb': {
        'label': 'Total Expenses (QB)',
        'category': 'Intermediate',
        'format': 'currency',
        'source': 'quickbooks',
        'is_editable': False,
        'is_calculated': False,
        'formula': None,
        'components': []
    },
    'uncategorized_expenses': {
        'label': 'Uncategorized Expenses',
        'category': 'Intermediate',
        'format': 'currency',
        'source': 'quickbooks',
        'is_editable': False,
        'is_calculated': False,
        'formula': None,
        'components': []
    },
}


def format_currency(value):
    """Format a decimal value as currency string."""
    if value is None:
        return '$0.00'
    return f"${value:,.2f}"


def build_calculation_display(formula: str, components: dict, result_value) -> str:
    """
    Build a human-readable calculation display string.

    Example: "$88,098.48 - $14,248.85 - $22,588.00 - $13,000.00 = $38,261.63"
    """
    if not formula or not components:
        return None

    # Parse the formula and substitute values
    display_parts = []
    formula_parts = formula.replace(' ', '').replace('-', ' - ').replace('+', ' + ').split()

    for part in formula_parts:
        if part in ['+', '-']:
            display_parts.append(part)
        elif part in components:
            display_parts.append(format_currency(components.get(part, 0)))
        else:
            display_parts.append(part)

    calculation = ' '.join(display_parts)
    result = format_currency(result_value)

    return f"{calculation} = {result}"


@qbr_api.route('/api/qbr/metric-definitions', methods=['GET'])
def get_metric_definitions():
    """
    Get metric definitions with optional period-specific calculations.

    Returns all metric metadata including labels, formats, descriptions,
    and for calculated metrics, the actual component values and calculation display.

    Query Parameters:
        period: Optional. Period to get actual values for (e.g., '2026-01')
        category: Optional. Filter by category (e.g., 'Expenses', 'Revenue')
        include_intermediate: Optional. Include intermediate metrics (default: false)

    Response includes:
        - key: metric identifier
        - label: display name
        - category: grouping
        - format: currency, number, percentage
        - description: human-readable description
        - source: quickbooks, calculated, manual, connectwise, ninja
        - is_editable: whether CFO can edit
        - is_calculated: whether derived from other metrics
        - formula: calculation formula (if calculated)
        - components: list of component metric keys (if calculated)
        - value: actual value for the period (if period specified)
        - component_values: actual component values (if calculated and period specified)
        - calculation_display: formatted calculation string (if calculated and period specified)
    """
    from api.api_server import get_session

    period = request.args.get('period')
    category_filter = request.args.get('category')
    include_intermediate = request.args.get('include_intermediate', 'false').lower() == 'true'
    organization_id = int(request.args.get('organization_id', 1))

    try:
        # Get actual values if period is specified
        period_values = {}
        if period:
            with get_session() as session:
                # Order by updated_at DESC so latest values come first
                # Then keep only the first (latest) value per metric_name
                metrics = session.query(QBRMetricsMonthly).filter(
                    QBRMetricsMonthly.period == period,
                    QBRMetricsMonthly.organization_id == organization_id
                ).order_by(QBRMetricsMonthly.updated_at.desc()).all()

                for m in metrics:
                    # Only keep the first (latest) value for each metric
                    if m.metric_name not in period_values:
                        period_values[m.metric_name] = float(m.metric_value) if m.metric_value else 0

        # Build response
        result_metrics = []

        for key, metadata in METRIC_METADATA.items():
            # Filter by category if specified
            if category_filter and metadata['category'].lower() != category_filter.lower():
                continue

            # Skip intermediate metrics unless requested
            if metadata['category'] == 'Intermediate' and not include_intermediate:
                continue

            metric_def = {
                'key': key,
                'label': metadata['label'],
                'category': metadata['category'],
                'format': metadata['format'],
                'description': METRIC_DESCRIPTIONS.get(key, ''),
                'source': metadata['source'],
                'is_editable': metadata['is_editable'],
                'is_calculated': metadata['is_calculated'],
            }

            # Add formula info for calculated metrics
            if metadata['is_calculated'] and metadata['formula']:
                metric_def['formula'] = metadata['formula']
                metric_def['components'] = metadata['components']

                # Add actual values if period specified
                if period and period_values:
                    metric_def['value'] = period_values.get(key, 0)

                    # Get component values
                    component_values = {}
                    for comp in metadata['components']:
                        component_values[comp] = period_values.get(comp, 0)

                    metric_def['component_values'] = component_values

                    # Build calculation display
                    calc_display = build_calculation_display(
                        metadata['formula'],
                        component_values,
                        metric_def['value']
                    )
                    if calc_display:
                        metric_def['calculation_display'] = calc_display

            elif period and period_values:
                # Non-calculated metrics - just add the value
                metric_def['value'] = period_values.get(key, 0)

            result_metrics.append(metric_def)

        return jsonify({
            'success': True,
            'data': {
                'period': period,
                'organization_id': organization_id,
                'metrics': result_metrics,
                'count': len(result_metrics)
            }
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': {
                'code': 'SERVER_ERROR',
                'message': str(e),
                'status': 500
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

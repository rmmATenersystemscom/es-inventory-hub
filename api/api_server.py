#!/usr/bin/env python3
"""
ES Inventory Hub API Server

Provides REST API endpoints for:
1. Accessing variance report data
2. Triggering collector runs
3. Checking system status

Usage:
    python3 api_server.py
    # Server runs on http://localhost:5400
"""

import os
import sys
import json
import subprocess
from datetime import date, datetime, timedelta
from typing import Dict, List, Any, Optional

from flask import Flask, jsonify, request
from flask_cors import CORS
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the project root to Python path
sys.path.insert(0, '/opt/es-inventory-hub')

from collectors.checks.cross_vendor import run_cross_vendor_checks

app = Flask(__name__)
CORS(app)  # Enable CORS for cross-origin requests

# Database connection
from common.config import get_dsn
DSN = get_dsn()
engine = create_engine(DSN)
Session = sessionmaker(bind=engine)

def get_session():
    """Get database session."""
    return Session()

def get_latest_matching_date() -> Optional[date]:
    """Get the latest date where both vendors have data."""
    with get_session() as session:
        query = text("""
            SELECT snapshot_date, COUNT(DISTINCT vendor_id) as vendor_count
            FROM device_snapshot
            WHERE snapshot_date >= CURRENT_DATE - INTERVAL '7 days'
            GROUP BY snapshot_date
            HAVING COUNT(DISTINCT vendor_id) = 2
            ORDER BY snapshot_date DESC
            LIMIT 1
        """)
        
        result = session.execute(query).fetchone()
        return result[0] if result else None

def get_data_status() -> Dict[str, Any]:
    """Determine the status of the data (current, stale, out_of_sync)."""
    latest_date = get_latest_matching_date()
    
    if not latest_date:
        return {
            "status": "out_of_sync",
            "message": "No matching data found between vendors",
            "latest_date": None
        }
    
    days_old = (date.today() - latest_date).days
    
    if days_old <= 1:
        return {
            "status": "current",
            "message": "Data is current",
            "latest_date": latest_date.isoformat()
        }
    else:
        return {
            "status": "stale_data",
            "message": f"Data is {days_old} days old",
            "latest_date": latest_date.isoformat()
        }

# API Endpoints

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    })

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get overall system status."""
    data_status = get_data_status()
    
    with get_session() as session:
        # Get device counts
        device_query = text("""
            SELECT v.name as vendor, COUNT(*) as count
            FROM device_snapshot ds
            JOIN vendor v ON ds.vendor_id = v.id
            WHERE ds.snapshot_date = (
                SELECT MAX(snapshot_date) FROM device_snapshot
            )
            GROUP BY v.name
        """)
        
        device_counts = {row[0]: row[1] for row in session.execute(device_query).fetchall()}
        
        # Get exception counts
        exception_query = text("""
            SELECT type, COUNT(*) as count
            FROM exceptions
            WHERE resolved = FALSE
            GROUP BY type
        """)
        
        exception_counts = {row[0]: row[1] for row in session.execute(exception_query).fetchall()}
    
    return jsonify({
        "data_status": data_status,
        "device_counts": device_counts,
        "exception_counts": exception_counts,
        "total_exceptions": sum(exception_counts.values())
    })

@app.route('/api/variance-report/latest', methods=['GET'])
def get_latest_variance_report():
    """Get the latest variance report."""
    # Get query parameters
    include_resolved = request.args.get('include_resolved', 'false').lower() == 'true'
    
    latest_date = get_latest_matching_date()
    
    if not latest_date:
        return jsonify({
            "error": "No matching data found between vendors",
            "status": "out_of_sync"
        }), 400
    
    with get_session() as session:
        # Get exceptions for the latest date (filter resolved by default)
        if include_resolved:
            query = text("""
                SELECT id, date_found, type, hostname, details, resolved
                FROM exceptions
                WHERE date_found = :report_date
                ORDER BY type, hostname
            """)
        else:
            query = text("""
                SELECT id, date_found, type, hostname, details, resolved
                FROM exceptions
                WHERE date_found = :report_date
                AND resolved = FALSE
                ORDER BY type, hostname
            """)
        
        exceptions = session.execute(query, {'report_date': latest_date}).fetchall()
        
        # Group by type
        by_type = {}
        for exc in exceptions:
            exc_type = exc[2]
            if exc_type not in by_type:
                by_type[exc_type] = []
            by_type[exc_type].append({
                'id': exc[0],
                'hostname': exc[3],
                'details': exc[4],
                'resolved': exc[5]
            })
        
        # Calculate totals
        total_exceptions = len(exceptions)
        unresolved_count = sum(1 for exc in exceptions if not exc[5])
        
        # Create dashboard-compatible format
        exception_counts = {exc_type: len(devices) for exc_type, devices in by_type.items()}
        
        # Map to dashboard expected format
        dashboard_format = {
            "missing_in_ninja": {
                "total_count": exception_counts.get("MISSING_NINJA", 0)
            },
            "threatlocker_duplicates": {
                "total_count": exception_counts.get("DUPLICATE_TL", 0)
            },
            "ninja_duplicates": {
                "total_count": exception_counts.get("SPARE_MISMATCH", 0)
            },
            "display_name_mismatches": {
                "total_count": exception_counts.get("DISPLAY_NAME_MISMATCH", 0)
            }
        }
        
        # Get collection timestamps
        collection_info = _get_collection_timestamps(session, latest_date)
        
        return jsonify({
            "report_date": latest_date.isoformat(),
            "data_status": get_data_status(),
            "summary": {
                "total_exceptions": total_exceptions,
                "unresolved_count": unresolved_count,
                "resolved_count": total_exceptions - unresolved_count
            },
            "exceptions_by_type": by_type,
            "exception_counts": exception_counts,
            # Collection information
            "collection_info": {
                "ninja_collected": collection_info["ninja_collected"],
                "threatlocker_collected": collection_info["threatlocker_collected"],
                "last_collection": collection_info["last_collection"],
                "data_freshness": collection_info["data_freshness"]
            },
            # Dashboard-compatible format
            **dashboard_format
        })

@app.route('/api/variance-report/<date_str>', methods=['GET'])
def get_variance_report_by_date(date_str: str):
    """Get variance report for a specific date."""
    # Get query parameters
    include_resolved = request.args.get('include_resolved', 'false').lower() == 'true'
    
    try:
        report_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
    
    with get_session() as session:
        # Check if data exists for this date
        check_query = text("""
            SELECT COUNT(DISTINCT vendor_id) as vendor_count
            FROM device_snapshot
            WHERE snapshot_date = :report_date
        """)
        
        result = session.execute(check_query, {'report_date': report_date}).fetchone()
        
        if result[0] < 2:
            return jsonify({
                "error": f"Insufficient data for {date_str}. Found {result[0]} vendors, need 2.",
                "status": "insufficient_data"
            }), 400
        
        # Get exceptions for the date (filter resolved by default)
        if include_resolved:
            query = text("""
                SELECT id, date_found, type, hostname, details, resolved
                FROM exceptions
                WHERE date_found = :report_date
                ORDER BY type, hostname
            """)
        else:
            query = text("""
                SELECT id, date_found, type, hostname, details, resolved
                FROM exceptions
                WHERE date_found = :report_date
                AND resolved = FALSE
                ORDER BY type, hostname
            """)
        
        exceptions = session.execute(query, {'report_date': report_date}).fetchall()
        
        # Group by type
        by_type = {}
        for exc in exceptions:
            exc_type = exc[2]
            if exc_type not in by_type:
                by_type[exc_type] = []
            by_type[exc_type].append({
                'id': exc[0],
                'hostname': exc[3],
                'details': exc[4],
                'resolved': exc[5]
            })
        
        return jsonify({
            "report_date": report_date.isoformat(),
            "summary": {
                "total_exceptions": len(exceptions),
                "unresolved_count": sum(1 for exc in exceptions if not exc[5]),
                "resolved_count": sum(1 for exc in exceptions if exc[5])
            },
            "exceptions_by_type": by_type,
            "exception_counts": {exc_type: len(devices) for exc_type, devices in by_type.items()}
        })

@app.route('/api/collectors/run', methods=['POST'])
def run_collectors():
    """Trigger collector runs."""
    data = request.get_json() or {}
    collector_type = data.get('collector', 'both')  # 'ninja', 'threatlocker', or 'both'
    run_cross_vendor = data.get('run_cross_vendor', True)
    
    results = {}
    
    try:
        if collector_type in ['ninja', 'both']:
            # Run Ninja collector (passwordless sudo configured)
            result = subprocess.run([
                'sudo', 'systemctl', 'start', 'ninja-collector.service'
            ], capture_output=True, text=True, timeout=300)
            
            results['ninja'] = {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
        
        if collector_type in ['threatlocker', 'both']:
            # Run ThreatLocker collector (passwordless sudo configured)
            result = subprocess.run([
                'sudo', 'systemctl', 'start', 'threatlocker-collector@rene.service'
            ], capture_output=True, text=True, timeout=300)
            
            results['threatlocker'] = {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
        
        # Run cross-vendor checks if requested
        if run_cross_vendor:
            try:
                with get_session() as session:
                    cross_vendor_results = run_cross_vendor_checks(session, date.today())
                    results['cross_vendor'] = {
                        'success': True,
                        'results': cross_vendor_results
                    }
            except Exception as e:
                results['cross_vendor'] = {
                    'success': False,
                    'error': str(e)
                }
        
        return jsonify({
            'success': True,
            'message': 'Collectors triggered successfully',
            'results': results
        })
        
    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'error': 'Collector execution timed out'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/collectors/status', methods=['GET'])
def get_collector_status():
    """Get status of collector services."""
    try:
        # Check systemd service status
        ninja_result = subprocess.run([
            'systemctl', 'is-active', 'ninja-collector.service'
        ], capture_output=True, text=True)
        
        threatlocker_result = subprocess.run([
            'systemctl', 'is-active', 'threatlocker-collector@rene.service'
        ], capture_output=True, text=True)
        
        # Get last run times
        ninja_status = subprocess.run([
            'systemctl', 'show', 'ninja-collector.service', '--property=ActiveEnterTimestamp'
        ], capture_output=True, text=True)
        
        threatlocker_status = subprocess.run([
            'systemctl', 'show', 'threatlocker-collector@rene.service', '--property=ActiveEnterTimestamp'
        ], capture_output=True, text=True)
        
        return jsonify({
            'ninja': {
                'status': ninja_result.stdout.strip(),
                'last_run': ninja_status.stdout.strip().split('=')[1] if '=' in ninja_status.stdout else None
            },
            'threatlocker': {
                'status': threatlocker_result.stdout.strip(),
                'last_run': threatlocker_status.stdout.strip().split('=')[1] if '=' in threatlocker_status.stdout else None
            }
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500

@app.route('/api/exceptions', methods=['GET'])
def get_exceptions():
    """Get exceptions with filtering options."""
    # Parse query parameters
    exception_type = request.args.get('type')
    resolved = request.args.get('resolved')
    limit = int(request.args.get('limit', 100))
    offset = int(request.args.get('offset', 0))
    
    with get_session() as session:
        query = text("""
            SELECT id, date_found, type, hostname, details, resolved
            FROM exceptions
            WHERE 1=1
        """)
        
        params = {}
        
        if exception_type:
            query += " AND type = :exception_type"
            params['exception_type'] = exception_type
        
        if resolved is not None:
            query += " AND resolved = :resolved"
            params['resolved'] = resolved.lower() == 'true'
        
        query += " ORDER BY date_found DESC, type, hostname"
        query += " LIMIT :limit OFFSET :offset"
        params['limit'] = limit
        params['offset'] = offset
        
        exceptions = session.execute(query, params).fetchall()
        
        return jsonify([{
            'id': exc[0],
            'date_found': exc[1].isoformat(),
            'type': exc[2],
            'hostname': exc[3],
            'details': exc[4],
            'resolved': exc[5]
        } for exc in exceptions])

@app.route('/api/exceptions/<int:exception_id>/resolve', methods=['POST'])
def resolve_exception(exception_id: int):
    """Mark an exception as resolved."""
    data = request.get_json() or {}
    resolved_by = data.get('resolved_by', 'api_user')
    notes = data.get('notes', '')
    
    with get_session() as session:
        query = text("""
            UPDATE exceptions
            SET resolved = TRUE, resolved_date = CURRENT_DATE, resolved_by = :resolved_by
            WHERE id = :exception_id
        """)
        
        result = session.execute(query, {
            'exception_id': exception_id,
            'resolved_by': resolved_by
        })
        
        session.commit()
        
        if result.rowcount == 0:
            return jsonify({'error': 'Exception not found'}), 404
        
        return jsonify({'success': True, 'message': 'Exception resolved'})

@app.route('/api/exceptions/<int:exception_id>/mark-manually-fixed', methods=['POST'])
def mark_exception_manually_fixed(exception_id: int):
    """
    Mark an exception as manually fixed by dashboard user.
    
    This endpoint addresses the critical gap where dashboard updates
    ThreatLocker but the database doesn't know about manual fixes.
    """
    data = request.get_json() or {}
    updated_by = data.get('updated_by', 'dashboard_user')
    update_type = data.get('update_type', 'unknown')
    old_value = data.get('old_value', {})
    new_value = data.get('new_value', {})
    notes = data.get('notes', '')
    
    with get_session() as session:
        # First check if exception exists
        check_query = text("SELECT id, hostname, type FROM exceptions WHERE id = :exception_id")
        result = session.execute(check_query, {'exception_id': exception_id}).fetchone()
        
        if not result:
            return jsonify({'error': 'Exception not found'}), 404
        
        # Update exception with manual fix information
        update_query = text("""
            UPDATE exceptions
            SET 
                resolved = TRUE,
                manually_updated_at = CURRENT_TIMESTAMP,
                manually_updated_by = :updated_by,
                update_type = :update_type,
                old_value = :old_value,
                new_value = :new_value,
                variance_status = 'manually_fixed'
            WHERE id = :exception_id
        """)
        
        session.execute(update_query, {
            'exception_id': exception_id,
            'updated_by': updated_by,
            'update_type': update_type,
            'old_value': json.dumps(old_value),
            'new_value': json.dumps(new_value)
        })
        
        session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Exception marked as manually fixed',
            'exception_id': exception_id,
            'hostname': result[1],
            'type': result[2],
            'updated_by': updated_by,
            'updated_at': datetime.now().isoformat()
        })

@app.route('/api/exceptions/mark-fixed-by-hostname', methods=['POST'])
def mark_exception_fixed_by_hostname():
    """
    Mark exceptions as manually fixed by hostname and exception type.
    
    This endpoint allows the dashboard to mark exceptions as fixed when
    they update ThreatLocker display names, without needing to know
    the specific exception ID.
    
    FIXED: Now handles both unresolved and already-resolved exceptions
    to provide proper feedback to the dashboard.
    """
    data = request.get_json() or {}
    hostname = data.get('hostname')
    exception_type = data.get('type', 'DISPLAY_NAME_MISMATCH')
    updated_by = data.get('updated_by', 'dashboard_user')
    update_type = data.get('update_type', 'display_name_update')
    old_value = data.get('old_value', {})
    new_value = data.get('new_value', {})
    notes = data.get('notes', '')
    
    if not hostname:
        return jsonify({'error': 'Hostname is required'}), 400
    
    with get_session() as session:
        # First, check if ANY exceptions exist for this hostname (resolved or unresolved)
        check_query = text("""
            SELECT id, hostname, type, resolved, manually_updated_at, manually_updated_by
            FROM exceptions 
            WHERE hostname = :hostname 
            AND type = :exception_type
            AND date_found = CURRENT_DATE
            ORDER BY id DESC
        """)
        
        all_exceptions = session.execute(check_query, {
            'hostname': hostname,
            'exception_type': exception_type
        }).fetchall()
        
        if not all_exceptions:
            return jsonify({
                'success': False,
                'message': f'No {exception_type} exceptions found for hostname {hostname}',
                'hostname': hostname,
                'type': exception_type,
                'status': 'not_found'
            }), 404
        
        # Check if any are unresolved
        unresolved_exceptions = [exc for exc in all_exceptions if not exc[3]]  # resolved is index 3
        
        if unresolved_exceptions:
            # Update unresolved exceptions
            update_query = text("""
                UPDATE exceptions
                SET 
                    resolved = TRUE,
                    manually_updated_at = CURRENT_TIMESTAMP,
                    manually_updated_by = :updated_by,
                    update_type = :update_type,
                    old_value = :old_value,
                    new_value = :new_value,
                    variance_status = 'manually_fixed'
                WHERE hostname = :hostname 
                AND type = :exception_type
                AND resolved = FALSE
                AND date_found = CURRENT_DATE
            """)
            
            result = session.execute(update_query, {
                'hostname': hostname,
                'exception_type': exception_type,
                'updated_by': updated_by,
                'update_type': update_type,
                'old_value': json.dumps(old_value),
                'new_value': json.dumps(new_value)
            })
            
            session.commit()
            
            return jsonify({
                'success': True,
                'message': f'Marked {result.rowcount} exceptions as manually fixed',
                'hostname': hostname,
                'type': exception_type,
                'exceptions_updated': result.rowcount,
                'updated_by': updated_by,
                'updated_at': datetime.now().isoformat(),
                'status': 'updated'
            })
        else:
            # All exceptions are already resolved - return success with info
            latest_exception = all_exceptions[0]  # Most recent
            return jsonify({
                'success': True,
                'message': f'Exception already resolved for hostname {hostname}',
                'hostname': hostname,
                'type': exception_type,
                'exceptions_updated': 0,
                'status': 'already_resolved',
                'last_updated_by': latest_exception[5],  # manually_updated_by
                'last_updated_at': latest_exception[4].isoformat() if latest_exception[4] else None,  # manually_updated_at
                'updated_at': datetime.now().isoformat()
            })

@app.route('/api/exceptions/bulk-update', methods=['POST'])
def bulk_update_exceptions():
    """
    Perform bulk operations on multiple exceptions.
    
    Supports bulk marking as manually fixed, resolved, or status changes.
    """
    data = request.get_json() or {}
    exception_ids = data.get('exception_ids', [])
    action = data.get('action', 'mark_manually_fixed')
    updated_by = data.get('updated_by', 'dashboard_user')
    notes = data.get('notes', '')
    
    if not exception_ids:
        return jsonify({'error': 'No exception IDs provided'}), 400
    
    if action not in ['mark_manually_fixed', 'resolve', 'reset_status']:
        return jsonify({'error': 'Invalid action'}), 400
    
    with get_session() as session:
        # Build dynamic query based on action
        if action == 'mark_manually_fixed':
            query = text("""
                UPDATE exceptions
                SET 
                    resolved = TRUE,
                    manually_updated_at = CURRENT_TIMESTAMP,
                    manually_updated_by = :updated_by,
                    variance_status = 'manually_fixed'
                WHERE id = ANY(:exception_ids)
            """)
        elif action == 'resolve':
            query = text("""
                UPDATE exceptions
                SET 
                    resolved = TRUE,
                    resolved_date = CURRENT_DATE,
                    resolved_by = :updated_by
                WHERE id = ANY(:exception_ids)
            """)
        elif action == 'reset_status':
            query = text("""
                UPDATE exceptions
                SET 
                    variance_status = 'active',
                    manually_updated_at = NULL,
                    manually_updated_by = NULL
                WHERE id = ANY(:exception_ids)
            """)
        
        result = session.execute(query, {
            'exception_ids': exception_ids,
            'updated_by': updated_by
        })
        
        session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Bulk {action} completed',
            'updated_count': result.rowcount,
            'exception_ids': exception_ids,
            'updated_by': updated_by
        })

@app.route('/api/variance-report/filtered', methods=['GET'])
def get_filtered_variance_report():
    """
    Get filtered variance report for dashboard integration.
    
    This endpoint provides the same data format as the Variances dashboard
    but uses Database AI's filtered exception data (only unresolved exceptions).
    This ensures both systems use the same authoritative data source.
    """
    latest_date = get_latest_matching_date()
    
    if not latest_date:
        return jsonify({
            "error": "No matching data found between vendors",
            "status": "out_of_sync"
        }), 400
    
    with get_session() as session:
        # Get device counts by vendor
        device_counts_query = text("""
            SELECT v.name as vendor, COUNT(*) as count
            FROM device_snapshot ds
            JOIN vendor v ON ds.vendor_id = v.id
            WHERE ds.snapshot_date = :report_date
            GROUP BY v.name
        """)
        
        device_counts = session.execute(device_counts_query, {'report_date': latest_date}).fetchall()
        device_counts_dict = {row[0]: row[1] for row in device_counts}
        
        # Get only unresolved exceptions (filtered data)
        exceptions_query = text("""
            SELECT id, type, hostname, details
            FROM exceptions
            WHERE date_found = :report_date
            AND resolved = FALSE
            ORDER BY type, hostname
        """)
        
        exceptions = session.execute(exceptions_query, {'report_date': latest_date}).fetchall()
        
        # Group exceptions by type and organization
        by_type = {}
        by_organization = {}
        
        for exc in exceptions:
            exc_type = exc[1]
            hostname = exc[2]
            details = exc[3]
            
            # Initialize type group
            if exc_type not in by_type:
                by_type[exc_type] = []
            
            # Get organization from details
            org_name = details.get('tl_org_name', details.get('ninja_org_name', 'Unknown'))
            if org_name not in by_organization:
                by_organization[org_name] = []
            
            # Format exception data for dashboard
            exception_data = {
                "hostname": hostname,
                "details": details,
                "action": _get_action_for_exception_type(exc_type)
            }
            
            # Add type-specific fields
            if exc_type == 'DISPLAY_NAME_MISMATCH':
                exception_data.update({
                    "ninja_display_name": details.get('ninja_display_name', ''),
                    "threatlocker_computer_name": details.get('tl_display_name', ''),
                    "organization": org_name
                })
            elif exc_type == 'MISSING_NINJA':
                exception_data.update({
                    "threatlocker_hostname": details.get('tl_hostname', ''),
                    "organization": org_name
                })
            
            by_type[exc_type].append(exception_data)
            by_organization[org_name].append(exception_data)
        
        # Calculate totals
        total_variances = len(exceptions)
        
        # Build response in dashboard format
        response = {
            "analysis_date": latest_date.isoformat(),
            "total_devices": {
                "ninja": device_counts_dict.get('Ninja', 0),
                "threatlocker": device_counts_dict.get('ThreatLocker', 0)
            },
            "total_variances": total_variances,
            "data_status": get_data_status(),
            "status": "current"
        }
        
        # Add exception data by type
        if 'DISPLAY_NAME_MISMATCH' in by_type:
            response["display_name_mismatches"] = {
                "total_count": len(by_type['DISPLAY_NAME_MISMATCH']),
                "by_organization": _group_by_organization(by_type['DISPLAY_NAME_MISMATCH'])
            }
        
        if 'MISSING_NINJA' in by_type:
            response["missing_in_ninja"] = {
                "total_count": len(by_type['MISSING_NINJA']),
                "by_organization": _group_by_organization(by_type['MISSING_NINJA'])
            }
        
        if 'DUPLICATE_TL' in by_type:
            response["threatlocker_duplicates"] = {
                "total_count": len(by_type['DUPLICATE_TL']),
                "devices": by_type['DUPLICATE_TL']
            }
        
        if 'SPARE_MISMATCH' in by_type:
            response["ninja_duplicates"] = {
                "total_count": len(by_type['SPARE_MISMATCH']),
                "by_organization": _group_by_organization(by_type['SPARE_MISMATCH'])
            }
        
        # Add actionable insights
        response["actionable_insights"] = _generate_actionable_insights(by_type)
        
        # Add collection info with timezone-aware timestamps
        collection_info = _get_collection_timestamps(session, latest_date)
        response["collection_info"] = collection_info
        
        # Add data quality indicators
        response["data_quality"] = {
            "total_exceptions": total_variances,
            "exception_types": list(by_type.keys()),
            "organizations_affected": len(by_organization)
        }
        
        return jsonify(response)

def _get_action_for_exception_type(exc_type: str) -> str:
    """Get recommended action for exception type."""
    actions = {
        'DISPLAY_NAME_MISMATCH': 'Investigate - Reconcile naming differences',
        'MISSING_NINJA': 'Add device to Ninja or remove from ThreatLocker',
        'DUPLICATE_TL': 'Remove duplicate ThreatLocker entries',
        'SPARE_MISMATCH': 'Update billing status or remove from ThreatLocker',
        'SITE_MISMATCH': 'Reconcile site assignments between vendors'
    }
    return actions.get(exc_type, 'Investigate and resolve')

def _group_by_organization(exceptions: list) -> dict:
    """Group exceptions by organization."""
    by_org = {}
    for exc in exceptions:
        org = exc.get('organization', 'Unknown')
        if org not in by_org:
            by_org[org] = []
        by_org[org].append(exc)
    return by_org

def _generate_actionable_insights(by_type: dict) -> dict:
    """Generate actionable insights based on exception data."""
    insights = {
        "priority_actions": [],
        "summary": {}
    }
    
    for exc_type, exceptions in by_type.items():
        count = len(exceptions)
        if count > 0:
            insights["summary"][exc_type] = count
            
            if exc_type == 'DISPLAY_NAME_MISMATCH' and count > 50:
                insights["priority_actions"].append(f"High priority: {count} display name mismatches need attention")
            elif exc_type == 'MISSING_NINJA' and count > 20:
                insights["priority_actions"].append(f"Critical: {count} devices missing from Ninja")
    
    return insights


def _get_collection_timestamps(session, latest_date: date) -> dict:
    """Get timezone-aware collection timestamps from JobRuns table."""
    from sqlalchemy import text
    
    # Query for the most recent successful collection runs
    collection_query = text("""
        SELECT job_name, started_at, ended_at
        FROM job_runs 
        WHERE status = 'completed'
        AND job_name IN ('ninja-collector', 'threatlocker-collector')
        AND DATE(started_at) = :collection_date
        ORDER BY started_at DESC
    """)
    
    results = session.execute(collection_query, {'collection_date': latest_date}).fetchall()
    
    # Initialize timestamps
    ninja_collected = None
    threatlocker_collected = None
    last_collection = None
    
    # Process results
    for job_name, started_at, ended_at in results:
        # Use ended_at if available, otherwise started_at
        timestamp = ended_at if ended_at else started_at
        
        if job_name == 'ninja-collector':
            ninja_collected = timestamp.isoformat() + 'Z'
        elif job_name == 'threatlocker-collector':
            threatlocker_collected = timestamp.isoformat() + 'Z'
    
    # Determine the latest collection time
    timestamps = [t for t in [ninja_collected, threatlocker_collected] if t]
    if timestamps:
        # Parse timestamps and find the latest
        parsed_times = []
        for ts in timestamps:
            try:
                parsed_times.append(datetime.fromisoformat(ts.replace('Z', '+00:00')))
            except:
                continue
        
        if parsed_times:
            last_collection = max(parsed_times).isoformat() + 'Z'
    
    # Fallback to date if no specific timestamps found
    if not last_collection:
        last_collection = latest_date.isoformat()
    
    # Determine data freshness
    today = datetime.now().date()
    days_old = (today - latest_date).days
    data_freshness = "current" if days_old <= 1 else "stale"
    
    return {
        "last_collection": last_collection,
        "ninja_collected": ninja_collected,
        "threatlocker_collected": threatlocker_collected,
        "data_freshness": data_freshness
    }


@app.route('/api/exceptions/count', methods=['GET'])
def get_exceptions_count():
    """
    Get count of unresolved exceptions by type for today.
    
    This endpoint helps the dashboard get accurate counts for display.
    """
    exception_type = request.args.get('type', 'DISPLAY_NAME_MISMATCH')
    
    with get_session() as session:
        count_query = text("""
            SELECT COUNT(*) as total_count
            FROM exceptions 
            WHERE type = :exception_type
            AND resolved = FALSE
            AND date_found = CURRENT_DATE
        """)
        
        total_count = session.execute(count_query, {
            'exception_type': exception_type
        }).scalar()
        
        return jsonify({
            'success': True,
            'type': exception_type,
            'unresolved_count': total_count,
            'date': datetime.now().date().isoformat()
        })

@app.route('/api/exceptions/status-summary', methods=['GET'])
def get_exceptions_status_summary():
    """
    Get summary of exception statuses for dashboard display.
    
    Provides counts by status, type, and recent activity.
    """
    with get_session() as session:
        # Get status summary
        status_query = text("""
            SELECT 
                COALESCE(variance_status, 'active') as status,
                type,
                COUNT(*) as count,
                COUNT(CASE WHEN resolved = true THEN 1 END) as resolved_count
            FROM exceptions
            WHERE date_found >= CURRENT_DATE - INTERVAL '7 days'
            GROUP BY variance_status, type
            ORDER BY status, type
        """)
        
        status_results = session.execute(status_query).fetchall()
        
        # Get recent manual updates
        recent_query = text("""
            SELECT 
                hostname,
                type,
                manually_updated_by,
                manually_updated_at,
                update_type
            FROM exceptions
            WHERE manually_updated_at >= CURRENT_DATE - INTERVAL '24 hours'
            ORDER BY manually_updated_at DESC
            LIMIT 20
        """)
        
        recent_results = session.execute(recent_query).fetchall()
        
        # Format results
        status_summary = {}
        for row in status_results:
            status = row[0]
            exc_type = row[1]
            count = row[2]
            resolved = row[3]
            
            if status not in status_summary:
                status_summary[status] = {}
            
            status_summary[status][exc_type] = {
                'total': count,
                'resolved': resolved,
                'unresolved': count - resolved
            }
        
        recent_updates = [{
            'hostname': row[0],
            'type': row[1],
            'updated_by': row[2],
            'updated_at': row[3].isoformat() if row[3] else None,
            'update_type': row[4]
        } for row in recent_results]
        
        return jsonify({
            'status_summary': status_summary,
            'recent_manual_updates': recent_updates,
            'generated_at': datetime.now().isoformat()
        })

@app.route('/api/devices/search', methods=['GET'])
def search_devices():
    """
    Search for devices across vendors with hostname truncation handling.
    
    This endpoint addresses the critical issue where Ninja truncates hostnames to 15 characters
    while ThreatLocker stores full hostnames, making cross-vendor lookups difficult.
    
    Query parameters:
    - q: Search term (hostname or partial hostname)
    - vendor: Optional vendor filter ('ninja' or 'threatlocker')
    - limit: Maximum results (default 50)
    """
    search_term = request.args.get('q', '').strip()
    vendor_filter = request.args.get('vendor', '').strip().lower()
    limit = int(request.args.get('limit', 50))
    
    if not search_term:
        return jsonify({'error': 'Search term (q) is required'}), 400
    
    if limit > 200:
        limit = 200  # Cap at 200 for performance
    
    with get_session() as session:
        # Build the search query with multiple matching strategies
        query = text("""
            SELECT 
                v.name as vendor,
                ds.hostname,
                ds.display_name,
                ds.organization_name,
                ds.snapshot_date,
                -- Show canonical key for debugging
                CASE 
                    WHEN v.name = 'ThreatLocker' THEN 
                        LOWER(LEFT(SPLIT_PART(SPLIT_PART(ds.hostname,'|',1),'.',1),15))
                    ELSE 
                        LOWER(LEFT(SPLIT_PART(ds.hostname,'.',1),15))
                END as canonical_key,
                -- Indicate if hostname is truncated
                CASE 
                    WHEN LENGTH(ds.hostname) = 15 AND v.name = 'Ninja' THEN true
                    ELSE false
                END as is_truncated
            FROM device_snapshot ds
            JOIN vendor v ON ds.vendor_id = v.id
            WHERE ds.snapshot_date = (
                SELECT MAX(snapshot_date) FROM device_snapshot
            )
            AND ds.hostname IS NOT NULL
        """)
        
        params = {}
        
        # Build the complete query with all conditions
        query_str = str(query)
        
        # Add vendor filter if specified
        if vendor_filter in ['ninja', 'threatlocker']:
            query_str += " AND v.name = :vendor_filter"
            params['vendor_filter'] = vendor_filter.title()
        
        # Add search conditions - multiple strategies to handle truncation
        query_str += """
            AND (
                -- Exact match
                ds.hostname ILIKE :search_term || '%'
                -- Contains match
                OR ds.hostname ILIKE '%' || :search_term || '%'
                -- Canonical key match (handles truncation)
                OR (
                    CASE 
                        WHEN v.name = 'ThreatLocker' THEN 
                            LOWER(LEFT(SPLIT_PART(SPLIT_PART(ds.hostname,'|',1),'.',1),15))
                        ELSE 
                            LOWER(LEFT(SPLIT_PART(ds.hostname,'.',1),15))
                    END = LOWER(LEFT(SPLIT_PART(:search_term,'.',1),15))
                )
                -- Prefix match for truncated hostnames
                OR LEFT(ds.hostname, 15) = LEFT(:search_term, 15)
            )
            ORDER BY v.name, ds.hostname LIMIT :limit
        """
        
        # Create final query
        query = text(query_str)
        params['search_term'] = search_term
        params['limit'] = limit
        
        results = session.execute(query, params).fetchall()
        
        # Group results by canonical key to show cross-vendor matches
        grouped_results = {}
        for row in results:
            canonical_key = row[5]  # canonical_key column
            if canonical_key not in grouped_results:
                grouped_results[canonical_key] = []
            
            grouped_results[canonical_key].append({
                'vendor': row[0],
                'hostname': row[1],
                'display_name': row[2],
                'organization_name': row[3],
                'snapshot_date': row[4].isoformat(),
                'canonical_key': canonical_key,
                'is_truncated': row[6]
            })
        
        # Calculate summary statistics
        total_devices = len(results)
        vendors_found = set(row[0] for row in results)
        truncated_count = sum(1 for row in results if row[6])
        
        return jsonify({
            'search_term': search_term,
            'total_results': total_devices,
            'vendors_found': list(vendors_found),
            'truncated_hostnames': truncated_count,
            'grouped_by_canonical_key': grouped_results,
            'warning': 'Some hostnames may be truncated due to Ninja 15-character limit' if truncated_count > 0 else None
        })

if __name__ == '__main__':
    print("Starting ES Inventory Hub API Server...")
    print("Available endpoints:")
    print("  GET  /api/health - Health check")
    print("  GET  /api/status - System status")
    print("  GET  /api/variance-report/latest - Latest variance report")
    print("  GET  /api/variance-report/{date} - Variance report for specific date")
    print("  GET  /api/variance-report/filtered - Filtered variance report for dashboard")
    print("  POST /api/collectors/run - Trigger collector runs")
    print("  GET  /api/collectors/status - Collector service status")
    print("  GET  /api/exceptions - Get exceptions with filtering")
    print("  POST /api/exceptions/{id}/resolve - Resolve an exception")
    print("  POST /api/exceptions/{id}/mark-manually-fixed - Mark as manually fixed (NEW)")
    print("  POST /api/exceptions/mark-fixed-by-hostname - Mark exceptions fixed by hostname (NEW)")
    print("  POST /api/exceptions/bulk-update - Bulk exception operations (NEW)")
    print("  GET  /api/exceptions/status-summary - Exception status summary (NEW)")
    print("  GET  /api/devices/search?q={hostname} - Search devices (handles hostname truncation)")
    print()
    print("Server will run on http://localhost:5400")
    
    app.run(host='0.0.0.0', port=5400, debug=True)

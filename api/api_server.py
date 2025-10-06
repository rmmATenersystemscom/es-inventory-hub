#!/usr/bin/env python3
"""
ES Inventory Hub API Server

Provides REST API endpoints for:
1. Accessing variance report data
2. Triggering collector runs
3. Checking system status

Usage:
    python3 api_server.py
    # Server runs on https://db-api.enersystems.com:5400
"""

import os
import sys
import json
import subprocess
import csv
import io
from datetime import date, datetime, timedelta
from typing import Dict, List, Any, Optional

from flask import Flask, jsonify, request, Response
from flask_cors import CORS
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Export functionality imports
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

# Add the project root to Python path
sys.path.insert(0, '/opt/es-inventory-hub')

from collectors.checks.cross_vendor import run_cross_vendor_checks

app = Flask(__name__)

def _format_date_string(date_str):
    """Format date string to consistent ISO 8601 format without microseconds"""
    if not date_str or date_str == 'Unknown':
        return 'Unknown'
    
    try:
        # Parse the date string and reformat without microseconds
        if isinstance(date_str, str):
            # Handle various date formats
            if 'T' in date_str:
                # ISO format - remove microseconds and timezone offset
                dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                return dt.replace(microsecond=0).replace(tzinfo=None).isoformat() + 'Z'
            else:
                return date_str
        return date_str
    except (ValueError, TypeError):
        return date_str

# Enable CORS for cross-origin requests with permissive settings for dashboard access
CORS(app, 
     origins=['*'],  # Allow all origins for now - can be restricted later
     methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
     allow_headers=['Content-Type', 'Authorization', 'X-Requested-With'],
     supports_credentials=True)

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

def get_organization_breakdown(session, exceptions, report_date):
    """Get detailed breakdown of exceptions by organization for each variance type."""
    # Get organization data for each exception
    org_query = text("""
        SELECT 
            e.id,
            e.type,
            e.hostname,
            e.details,
            e.resolved,
            COALESCE(
                ds_tl.organization_name,
                ds_ninja.organization_name,
                'Unknown'
            ) as organization_name,
            COALESCE(
                ds_tl.display_name,
                ds_ninja.display_name,
                e.hostname
            ) as display_name,
            COALESCE(
                ds_tl.device_status,
                ds_ninja.device_status,
                'Unknown'
            ) as billing_status,
            CASE 
                WHEN v_tl.name = 'ThreatLocker' THEN 'ThreatLocker'
                WHEN v_ninja.name = 'Ninja' THEN 'Ninja'
                ELSE 'Unknown'
            END as vendor
        FROM exceptions e
        LEFT JOIN device_snapshot ds_tl ON ds_tl.hostname = e.hostname 
            AND ds_tl.snapshot_date = :report_date
            AND ds_tl.vendor_id = (SELECT id FROM vendor WHERE name = 'ThreatLocker')
        LEFT JOIN vendor v_tl ON ds_tl.vendor_id = v_tl.id
        LEFT JOIN device_snapshot ds_ninja ON ds_ninja.hostname = e.hostname 
            AND ds_ninja.snapshot_date = :report_date
            AND ds_ninja.vendor_id = (SELECT id FROM vendor WHERE name = 'Ninja')
        LEFT JOIN vendor v_ninja ON ds_ninja.vendor_id = v_ninja.id
        WHERE e.date_found = :report_date
        ORDER BY e.type, organization_name, e.hostname
    """)
    
    org_results = session.execute(org_query, {'report_date': report_date}).fetchall()
    
    # Group by type and organization
    by_organization = {}
    
    for row in org_results:
        exc_id, exc_type, hostname, details, resolved, org_name, display_name, billing_status, vendor = row
        
        # Map exception types to dashboard format
        dashboard_type = None
        if exc_type == "MISSING_NINJA":
            dashboard_type = "missing_in_ninja"
        elif exc_type == "DUPLICATE_TL":
            dashboard_type = "threatlocker_duplicates"
        elif exc_type == "SPARE_MISMATCH":
            dashboard_type = "ninja_duplicates"
        elif exc_type == "DISPLAY_NAME_MISMATCH":
            dashboard_type = "display_name_mismatches"
        
        if not dashboard_type:
            continue
            
        if dashboard_type not in by_organization:
            by_organization[dashboard_type] = {
                "total_count": 0,
                "by_organization": {}
            }
        
        # For Missing in Ninja, ThreatLocker Duplicates, and Ninja Duplicates, extract organization from details if not found in device_snapshot
        if exc_type in ["MISSING_NINJA", "DUPLICATE_TL", "SPARE_MISMATCH"] and org_name == "Unknown" and details:
            # Extract organization from the details JSONB field
            details_dict = details if isinstance(details, dict) else {}
            
            # For SPARE_MISMATCH (Ninja Duplicates), prefer ninja_org_name over tl_org_name
            if exc_type == "SPARE_MISMATCH":
                ninja_org = details_dict.get('ninja_org_name', '')
                tl_org = details_dict.get('tl_org_name', '')
                
                # Use ninja_org if it exists and is not empty, otherwise use tl_org, otherwise 'Unknown'
                if ninja_org and ninja_org.strip():
                    org_name = ninja_org
                    vendor = 'Ninja'
                elif tl_org and tl_org.strip():
                    org_name = tl_org
                    vendor = 'ThreatLocker'
                else:
                    org_name = 'Unknown'
            else:
                # For MISSING_NINJA and DUPLICATE_TL, use tl_org_name
                org_name = details_dict.get('tl_org_name', 'Unknown')
                if details_dict.get('tl_org_name'):
                    vendor = 'ThreatLocker'
            
            # Update display_name from site information
            if details_dict.get('tl_site_name'):
                display_name = f"{hostname} ({details_dict.get('tl_site_name')})"
            elif details_dict.get('ninja_site'):
                display_name = f"{hostname} ({details_dict.get('ninja_site')})"
        
        # For Display Name Mismatches, extract display name information from details
        if exc_type == "DISPLAY_NAME_MISMATCH" and details:
            details_dict = details if isinstance(details, dict) else {}
            
            # Extract organization from details (prefer ninja_org_name)
            ninja_org = details_dict.get('ninja_org_name', '')
            tl_org = details_dict.get('tl_org_name', '')
            
            if ninja_org and ninja_org.strip():
                org_name = ninja_org
                vendor = 'Ninja'
            elif tl_org and tl_org.strip():
                org_name = tl_org
                vendor = 'ThreatLocker'
            
            # Use the Ninja display name as the primary display name for the modal
            ninja_display = details_dict.get('ninja_display_name', '')
            if ninja_display and ninja_display.strip():
                display_name = ninja_display
        
        if org_name not in by_organization[dashboard_type]["by_organization"]:
            by_organization[dashboard_type]["by_organization"][org_name] = []
        
        # Create device entry
        device_entry = {
            "hostname": hostname,
            "vendor": vendor,
            "display_name": display_name,
            "organization": org_name,
            "billing_status": billing_status,
            "action": "Investigate"
        }
        
        # For Display Name Mismatches, add specific display name information for the modal
        if exc_type == "DISPLAY_NAME_MISMATCH" and details:
            details_dict = details if isinstance(details, dict) else {}
            device_entry.update({
                "ninja_display_name": details_dict.get('ninja_display_name', ''),
                "threatlocker_display_name": details_dict.get('tl_display_name', ''),
                "ninja_hostname": details_dict.get('ninja_hostname', ''),
                "threatlocker_hostname": details_dict.get('tl_hostname', '')
            })
        
        by_organization[dashboard_type]["by_organization"][org_name].append(device_entry)
        by_organization[dashboard_type]["total_count"] += 1
    
    return by_organization

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
        
        # Get detailed organization breakdown
        org_breakdown = get_organization_breakdown(session, exceptions, latest_date)
        
        # Update dashboard format with organization data
        enhanced_dashboard_format = {
            "missing_in_ninja": org_breakdown.get("missing_in_ninja", {
                "total_count": exception_counts.get("MISSING_NINJA", 0),
                "by_organization": {}
            }),
            "threatlocker_duplicates": org_breakdown.get("threatlocker_duplicates", {
                "total_count": exception_counts.get("DUPLICATE_TL", 0),
                "by_organization": {}
            }),
            "ninja_duplicates": org_breakdown.get("ninja_duplicates", {
                "total_count": exception_counts.get("SPARE_MISMATCH", 0),
                "by_organization": {}
            }),
            "display_name_mismatches": org_breakdown.get("display_name_mismatches", {
                "total_count": exception_counts.get("DISPLAY_NAME_MISMATCH", 0),
                "by_organization": {}
            })
        }
        
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
            # Enhanced dashboard-compatible format with organization breakdown
            **enhanced_dashboard_format
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
        
        # Get collection timestamps
        collection_info = _get_collection_timestamps(session, report_date)
        
        return jsonify({
            "report_date": report_date.isoformat(),
            "summary": {
                "total_exceptions": len(exceptions),
                "unresolved_count": sum(1 for exc in exceptions if not exc[5]),
                "resolved_count": sum(1 for exc in exceptions if exc[5])
            },
            "exceptions_by_type": by_type,
            "exception_counts": {exc_type: len(devices) for exc_type, devices in by_type.items()},
            "collection_info": collection_info
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

@app.route('/api/collectors/history', methods=['GET'])
def get_collection_history():
    """
    Get collection history for the last 10 runs.
    
    Returns collection runs with timestamps, status, and duration.
    """
    limit = int(request.args.get('limit', 10))
    
    with get_session() as session:
        # Get recent job runs
        query = text("""
            SELECT 
                job_name,
                started_at,
                ended_at,
                status,
                message,
                CASE 
                    WHEN ended_at IS NOT NULL THEN 
                        EXTRACT(EPOCH FROM (ended_at - started_at))::INTEGER
                    ELSE NULL
                END as duration_seconds
            FROM job_runs
            WHERE job_name IN ('ninja-collector', 'threatlocker-collector')
            ORDER BY started_at DESC
            LIMIT :limit
        """)
        
        results = session.execute(query, {'limit': limit}).fetchall()
        
        # Format results
        history = []
        for row in results:
            job_name, started_at, ended_at, status, message, duration_seconds = row
            
            # Calculate duration
            duration_str = None
            if duration_seconds is not None:
                if duration_seconds < 60:
                    duration_str = f"{duration_seconds}s"
                elif duration_seconds < 3600:
                    minutes = duration_seconds // 60
                    seconds = duration_seconds % 60
                    duration_str = f"{minutes}m {seconds}s"
                else:
                    hours = duration_seconds // 3600
                    minutes = (duration_seconds % 3600) // 60
                    duration_str = f"{hours}h {minutes}m"
            
            history.append({
                'job_name': job_name,
                'started_at': started_at.isoformat() if started_at else None,
                'ended_at': ended_at.isoformat() if ended_at else None,
                'status': status,
                'message': message,
                'duration': duration_str,
                'duration_seconds': duration_seconds
            })
        
        return jsonify({
            'collection_history': history,
            'total_runs': len(history),
            'generated_at': datetime.now().isoformat()
        })

@app.route('/api/collectors/progress', methods=['GET'])
def get_collection_progress():
    """
    Get real-time collection progress if collectors are currently running.
    
    Returns progress information for active collection jobs.
    """
    with get_session() as session:
        # Check for active collections
        query = text("""
            SELECT 
                job_name,
                started_at,
                status,
                message
            FROM job_runs
            WHERE job_name IN ('ninja-collector', 'threatlocker-collector')
            AND status IN ('running', 'started')
            AND started_at >= CURRENT_DATE
            ORDER BY started_at DESC
        """)
        
        results = session.execute(query).fetchall()
        
        # Check systemd service status for additional info
        active_collections = []
        for row in results:
            job_name, started_at, status, message = row
            
            # Get systemd status
            service_name = f"{job_name}.service"
            if job_name == 'threatlocker-collector':
                service_name = "threatlocker-collector@rene.service"
            
            try:
                systemd_result = subprocess.run([
                    'systemctl', 'is-active', service_name
                ], capture_output=True, text=True)
                
                is_active = systemd_result.stdout.strip() == 'active'
            except:
                is_active = False
            
            # Calculate elapsed time
            elapsed_seconds = None
            if started_at:
                elapsed = datetime.now() - started_at
                elapsed_seconds = int(elapsed.total_seconds())
            
            active_collections.append({
                'job_name': job_name,
                'started_at': started_at.isoformat() if started_at else None,
                'status': status,
                'message': message,
                'is_active': is_active,
                'elapsed_seconds': elapsed_seconds,
                'elapsed_time': f"{elapsed_seconds // 60}m {elapsed_seconds % 60}s" if elapsed_seconds else None
            })
        
        return jsonify({
            'active_collections': active_collections,
            'total_active': len(active_collections),
            'generated_at': datetime.now().isoformat()
        })

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
        ORDER BY started_at DESC
    """)
    
    results = session.execute(collection_query).fetchall()
    
    # Initialize timestamps
    ninja_collected = None
    threatlocker_collected = None
    last_collection = None
    
    # Process results - take the most recent for each collector type
    for job_name, started_at, ended_at in results:
        # Use ended_at if available, otherwise started_at
        timestamp = ended_at if ended_at else started_at
        
        # Format timestamp properly (ISO 8601 with Z suffix)
        # Remove any existing timezone info and add Z for UTC
        if timestamp.tzinfo is not None:
            # Convert to UTC and format
            utc_timestamp = timestamp.astimezone().replace(tzinfo=None)
            formatted_timestamp = utc_timestamp.isoformat() + 'Z'
        else:
            # Already UTC, just add Z
            formatted_timestamp = timestamp.isoformat() + 'Z'
        
        # Only set if we haven't found a timestamp for this collector yet
        # (since results are ordered by started_at DESC, first occurrence is most recent)
        if job_name == 'ninja-collector' and ninja_collected is None:
            ninja_collected = formatted_timestamp
        elif job_name == 'threatlocker-collector' and threatlocker_collected is None:
            threatlocker_collected = formatted_timestamp
    
    # Determine the latest collection time
    timestamps = [t for t in [ninja_collected, threatlocker_collected] if t]
    if timestamps:
        # Parse timestamps and find the latest
        parsed_times = []
        for ts in timestamps:
            try:
                # Remove Z suffix and parse as datetime
                clean_ts = ts.replace('Z', '')
                parsed_times.append(datetime.fromisoformat(clean_ts))
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

# Export Endpoints

@app.route('/api/variances/export/csv', methods=['GET'])
def export_variances_csv():
    """
    Export variance data to CSV format.
    
    Query parameters:
    - date: Specific date (YYYY-MM-DD) or 'latest' (default)
    - include_resolved: Include resolved exceptions (default: false)
    - variance_type: Filter by exception type (optional)
    """
    # Get query parameters
    date_param = request.args.get('date', 'latest')
    include_resolved = request.args.get('include_resolved', 'false').lower() == 'true'
    exception_type = request.args.get('variance_type', request.args.get('type', ''))
    
    # Determine report date
    if date_param == 'latest':
        report_date = get_latest_matching_date()
        if not report_date:
            return jsonify({
                "error": "No matching data found between vendors",
                "status": "out_of_sync"
            }), 400
    else:
        try:
            report_date = datetime.strptime(date_param, '%Y-%m-%d').date()
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
                "error": f"Insufficient data for {date_param}. Found {result[0]} vendors, need 2.",
                "status": "insufficient_data"
            }), 400
        
        # Build query for exceptions
        query_str = """
            SELECT 
                e.id,
                e.date_found,
                e.type,
                e.hostname,
                e.details,
                e.resolved,
                e.resolved_date,
                e.resolved_by,
                e.manually_updated_at,
                e.manually_updated_by,
                e.variance_status,
                e.update_type,
                e.old_value,
                e.new_value
            FROM exceptions e
            WHERE e.date_found = :report_date
        """
        
        params = {'report_date': report_date}
        
        # Add filters
        if not include_resolved:
            query_str += " AND e.resolved = FALSE"
        
        if exception_type:
            query_str += " AND e.type = :exception_type"
            params['exception_type'] = exception_type
        
        query_str += " ORDER BY e.type, e.hostname"
        
        query = text(query_str)
        
        exceptions = session.execute(query, params).fetchall()
        
        # Generate CSV content
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'ID', 'Date Found', 'Type', 'Hostname', 'Resolved', 'Resolved Date',
            'Resolved By', 'Manually Updated At', 'Manually Updated By',
            'Variance Status', 'Update Type', 'Organization', 'Details'
        ])
        
        # Write data rows
        for exc in exceptions:
            details = exc[4] if exc[4] else {}
            org_name = details.get('tl_org_name', details.get('ninja_org_name', 'Unknown'))
            
            writer.writerow([
                exc[0],  # ID
                exc[1].isoformat() if exc[1] else '',  # Date Found
                exc[2],  # Type
                exc[3],  # Hostname
                'Yes' if exc[5] else 'No',  # Resolved
                exc[6].isoformat() if exc[6] else '',  # Resolved Date
                exc[7] or '',  # Resolved By
                exc[8].isoformat() if exc[8] else '',  # Manually Updated At
                exc[9] or '',  # Manually Updated By
                exc[10] or 'active',  # Variance Status
                exc[11] or '',  # Update Type
                org_name,  # Organization
                json.dumps(details) if details else ''  # Details
            ])
        
        # Create response
        csv_content = output.getvalue()
        output.close()
        
        # Generate filename
        filename = f"variances-{report_date.isoformat()}.csv"
        if exception_type:
            filename = f"variances-{exception_type.lower()}-{report_date.isoformat()}.csv"
        
        response = Response(
            csv_content,
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename={filename}',
                'Content-Type': 'text/csv; charset=utf-8'
            }
        )
        
        return response

@app.route('/api/variances/available-dates', methods=['GET'])
def get_available_dates():
    """
    Get available analysis dates where both vendors have data.
    
    Returns list of dates with data quality status.
    """
    with get_session() as session:
        # Get dates with both vendors
        query = text("""
            SELECT 
                snapshot_date,
                COUNT(DISTINCT vendor_id) as vendor_count,
                COUNT(DISTINCT CASE WHEN v.name = 'Ninja' THEN ds.vendor_id END) as ninja_count,
                COUNT(DISTINCT CASE WHEN v.name = 'ThreatLocker' THEN ds.vendor_id END) as threatlocker_count
            FROM device_snapshot ds
            JOIN vendor v ON ds.vendor_id = v.id
            WHERE snapshot_date >= CURRENT_DATE - INTERVAL '30 days'
            GROUP BY snapshot_date
            HAVING COUNT(DISTINCT vendor_id) = 2
            ORDER BY snapshot_date DESC
        """)
        
        results = session.execute(query).fetchall()
        
        # Get exception counts for each date
        dates_with_exceptions = []
        for row in results:
            snapshot_date = row[0]
            ninja_count = row[2]
            threatlocker_count = row[3]
            
            # Get exception count for this date
            exception_query = text("""
                SELECT 
                    COUNT(*) as total_exceptions,
                    COUNT(CASE WHEN resolved = FALSE THEN 1 END) as unresolved_exceptions
                FROM exceptions
                WHERE date_found = :snapshot_date
            """)
            
            exception_result = session.execute(exception_query, {'snapshot_date': snapshot_date}).fetchone()
            total_exceptions = exception_result[0] if exception_result else 0
            unresolved_exceptions = exception_result[1] if exception_result else 0
            
            # Determine data quality
            days_old = (date.today() - snapshot_date).days
            if days_old <= 1:
                quality_status = "current"
            elif days_old <= 3:
                quality_status = "recent"
            else:
                quality_status = "stale"
            
            dates_with_exceptions.append({
                'date': snapshot_date.isoformat(),
                'ninja_devices': ninja_count,
                'threatlocker_devices': threatlocker_count,
                'total_exceptions': total_exceptions,
                'unresolved_exceptions': unresolved_exceptions,
                'data_quality': quality_status,
                'days_old': days_old
            })
        
        return jsonify({
            'available_dates': dates_with_exceptions,
            'date_range': {
                'earliest': dates_with_exceptions[-1]['date'] if dates_with_exceptions else None,
                'latest': dates_with_exceptions[0]['date'] if dates_with_exceptions else None
            },
            'total_dates': len(dates_with_exceptions)
        })

@app.route('/api/variances/historical/<date_str>', methods=['GET'])
def get_historical_variance_data(date_str: str):
    """
    Get variance data for a specific historical date.
    
    Same structure as /api/variance-report/latest but for historical date.
    """
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
        
        # Get exceptions for the date
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
        
        # Calculate totals
        total_exceptions = len(exceptions)
        unresolved_count = sum(1 for exc in exceptions if not exc[5])
        
        # Get device counts for this date
        device_query = text("""
            SELECT v.name as vendor, COUNT(*) as count
            FROM device_snapshot ds
            JOIN vendor v ON ds.vendor_id = v.id
            WHERE ds.snapshot_date = :report_date
            GROUP BY v.name
        """)
        
        device_counts = {row[0]: row[1] for row in session.execute(device_query, {'report_date': report_date}).fetchall()}
        
        # Get detailed organization breakdown
        org_breakdown = get_organization_breakdown(session, exceptions, report_date)
        
        # Create enhanced format with organization data
        enhanced_format = {
            "missing_in_ninja": org_breakdown.get("missing_in_ninja", {
                "total_count": 0,
                "by_organization": {}
            }),
            "threatlocker_duplicates": org_breakdown.get("threatlocker_duplicates", {
                "total_count": 0,
                "by_organization": {}
            }),
            "ninja_duplicates": org_breakdown.get("ninja_duplicates", {
                "total_count": 0,
                "by_organization": {}
            }),
            "display_name_mismatches": org_breakdown.get("display_name_mismatches", {
                "total_count": 0,
                "by_organization": {}
            })
        }
        
        return jsonify({
            "report_date": report_date.isoformat(),
            "summary": {
                "total_exceptions": total_exceptions,
                "unresolved_count": unresolved_count,
                "resolved_count": total_exceptions - unresolved_count
            },
            "exceptions_by_type": by_type,
            "exception_counts": {exc_type: len(devices) for exc_type, devices in by_type.items()},
            "device_counts": device_counts,
            "data_status": {
                "status": "historical",
                "message": f"Historical data for {date_str}",
                "latest_date": report_date.isoformat()
            },
            # Enhanced format with organization breakdown
            **enhanced_format
        })

@app.route('/api/variances/trends', methods=['GET'])
def get_variance_trends():
    """
    Get trend analysis for variance data over time.
    
    Query parameters:
    - start_date: Start date (YYYY-MM-DD)
    - end_date: End date (YYYY-MM-DD)
    - type: Exception type filter (optional)
    """
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    exception_type = request.args.get('type', '')
    
    if not start_date_str or not end_date_str:
        return jsonify({"error": "start_date and end_date are required"}), 400
    
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
    
    if start_date > end_date:
        return jsonify({"error": "start_date must be before end_date"}), 400
    
    with get_session() as session:
        # Build trend query
        query = text("""
            SELECT 
                date_found,
                type,
                COUNT(*) as total_count,
                COUNT(CASE WHEN resolved = FALSE THEN 1 END) as unresolved_count,
                COUNT(CASE WHEN resolved = TRUE THEN 1 END) as resolved_count
            FROM exceptions
            WHERE date_found BETWEEN :start_date AND :end_date
        """)
        
        params = {'start_date': start_date, 'end_date': end_date}
        
        if exception_type:
            query += " AND type = :exception_type"
            params['exception_type'] = exception_type
        
        query += """
            GROUP BY date_found, type
            ORDER BY date_found DESC, type
        """
        
        results = session.execute(query, params).fetchall()
        
        # Group by date and type
        trends_by_date = {}
        trends_by_type = {}
        
        for row in results:
            date_found = row[0]
            exc_type = row[1]
            total_count = row[2]
            unresolved_count = row[3]
            resolved_count = row[4]
            
            # Group by date
            if date_found not in trends_by_date:
                trends_by_date[date_found] = {}
            trends_by_date[date_found][exc_type] = {
                'total': total_count,
                'unresolved': unresolved_count,
                'resolved': resolved_count
            }
            
            # Group by type
            if exc_type not in trends_by_type:
                trends_by_type[exc_type] = []
            trends_by_type[exc_type].append({
                'date': date_found.isoformat(),
                'total': total_count,
                'unresolved': unresolved_count,
                'resolved': resolved_count
            })
        
        # Calculate summary statistics
        total_exceptions = sum(row[2] for row in results)
        total_unresolved = sum(row[3] for row in results)
        total_resolved = sum(row[4] for row in results)
        
        # Get unique dates and types
        unique_dates = sorted(set(row[0] for row in results), reverse=True)
        unique_types = sorted(set(row[1] for row in results))
        
        return jsonify({
            'trends_by_date': {date.isoformat(): data for date, data in trends_by_date.items()},
            'trends_by_type': trends_by_type,
            'summary': {
                'total_exceptions': total_exceptions,
                'total_unresolved': total_unresolved,
                'total_resolved': total_resolved,
                'date_range': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'unique_dates': len(unique_dates),
                'unique_types': unique_types
            },
            'date_range': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'days': (end_date - start_date).days + 1
            }
        })

# Enhanced Export Endpoints

@app.route('/api/variances/export/pdf', methods=['GET'])
def export_variances_pdf():
    """
    Export variance data to PDF format.
    
    Query parameters:
    - date: Specific date (YYYY-MM-DD) or 'latest' (default)
    - include_resolved: Include resolved exceptions (default: false)
    - variance_type: Filter by exception type (optional)
    """
    if not REPORTLAB_AVAILABLE:
        return jsonify({
            "error": "PDF export not available. Install reportlab: pip install reportlab"
        }), 500
    
    # Get query parameters
    date_param = request.args.get('date', 'latest')
    include_resolved = request.args.get('include_resolved', 'false').lower() == 'true'
    exception_type = request.args.get('variance_type', request.args.get('type', ''))
    
    # Determine report date
    if date_param == 'latest':
        report_date = get_latest_matching_date()
        if not report_date:
            return jsonify({
                "error": "No matching data found between vendors",
                "status": "out_of_sync"
            }), 400
    else:
        try:
            report_date = datetime.strptime(date_param, '%Y-%m-%d').date()
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
                "error": f"Insufficient data for {date_param}. Found {result[0]} vendors, need 2.",
                "status": "insufficient_data"
            }), 400
        
        # Get exceptions data
        query_str = """
            SELECT 
                e.id,
                e.date_found,
                e.type,
                e.hostname,
                e.details,
                e.resolved,
                e.resolved_date,
                e.resolved_by,
                e.manually_updated_at,
                e.manually_updated_by,
                e.variance_status
            FROM exceptions e
            WHERE e.date_found = :report_date
        """
        
        params = {'report_date': report_date}
        
        # Add filters
        if not include_resolved:
            query_str += " AND e.resolved = FALSE"
        
        if exception_type:
            query_str += " AND e.type = :exception_type"
            params['exception_type'] = exception_type
        
        query_str += " ORDER BY e.type, e.hostname"
        
        query = text(query_str)
        
        exceptions = session.execute(query, params).fetchall()
        
        # Generate PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=30,
            alignment=1  # Center
        )
        story.append(Paragraph(f"Variance Report - {report_date.isoformat()}", title_style))
        story.append(Spacer(1, 12))
        
        # Summary
        total_exceptions = len(exceptions)
        unresolved_count = sum(1 for exc in exceptions if not exc[5])
        resolved_count = total_exceptions - unresolved_count
        
        summary_data = [
            ['Total Exceptions', str(total_exceptions)],
            ['Unresolved', str(unresolved_count)],
            ['Resolved', str(resolved_count)],
            ['Report Date', report_date.isoformat()],
            ['Generated', datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        ]
        
        summary_table = Table(summary_data, colWidths=[2*inch, 1.5*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(Paragraph("Summary", styles['Heading2']))
        story.append(summary_table)
        story.append(Spacer(1, 20))
        
        # Exceptions table
        if exceptions:
            story.append(Paragraph("Exception Details", styles['Heading2']))
            
            # Prepare table data
            table_data = [['ID', 'Type', 'Hostname', 'Status', 'Organization']]
            
            for exc in exceptions:
                details = exc[4] if exc[4] else {}
                org_name = details.get('tl_org_name', details.get('ninja_org_name', 'Unknown'))
                status = 'Resolved' if exc[5] else 'Active'
                
                table_data.append([
                    str(exc[0]),
                    exc[2],
                    exc[3],
                    status,
                    org_name
                ])
            
            # Create table
            exceptions_table = Table(table_data, colWidths=[0.5*inch, 1.2*inch, 1.5*inch, 0.8*inch, 1.5*inch])
            exceptions_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.beige, colors.white])
            ]))
            
            story.append(exceptions_table)
        else:
            story.append(Paragraph("No exceptions found for the specified criteria.", styles['Normal']))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        # Generate filename
        filename = f"variances-{report_date.isoformat()}.pdf"
        if exception_type:
            filename = f"variances-{exception_type.lower()}-{report_date.isoformat()}.pdf"
        
        return Response(
            buffer.getvalue(),
            mimetype='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename={filename}',
                'Content-Type': 'application/pdf'
            }
        )

@app.route('/api/variances/export/excel', methods=['GET'])
def export_variances_excel():
    """
    Export variance data to Excel format with multiple sheets.
    
    Query parameters:
    - date: Specific date (YYYY-MM-DD) or 'latest' (default)
    - include_resolved: Include resolved exceptions (default: false)
    - variance_type: Filter by exception type (optional)
    """
    if not OPENPYXL_AVAILABLE:
        return jsonify({
            "error": "Excel export not available. Install openpyxl: pip install openpyxl"
        }), 500
    
    # Get query parameters
    date_param = request.args.get('date', 'latest')
    include_resolved = request.args.get('include_resolved', 'false').lower() == 'true'
    exception_type = request.args.get('variance_type', request.args.get('type', ''))
    
    # Determine report date
    if date_param == 'latest':
        report_date = get_latest_matching_date()
        if not report_date:
            return jsonify({
                "error": "No matching data found between vendors",
                "status": "out_of_sync"
            }), 400
    else:
        try:
            report_date = datetime.strptime(date_param, '%Y-%m-%d').date()
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
                "error": f"Insufficient data for {date_param}. Found {result[0]} vendors, need 2.",
                "status": "insufficient_data"
            }), 400
        
        # Get exceptions data
        query_str = """
            SELECT 
                e.id,
                e.date_found,
                e.type,
                e.hostname,
                e.details,
                e.resolved,
                e.resolved_date,
                e.resolved_by,
                e.manually_updated_at,
                e.manually_updated_by,
                e.variance_status,
                e.update_type
            FROM exceptions e
            WHERE e.date_found = :report_date
        """
        
        params = {'report_date': report_date}
        
        # Add filters
        if not include_resolved:
            query_str += " AND e.resolved = FALSE"
        
        if exception_type:
            query_str += " AND e.type = :exception_type"
            params['exception_type'] = exception_type
        
        query_str += " ORDER BY e.type, e.hostname"
        
        query = text(query_str)
        
        exceptions = session.execute(query, params).fetchall()
        
        # Create Excel workbook
        wb = openpyxl.Workbook()
        
        # Remove default sheet
        wb.remove(wb.active)
        
        # Create Summary sheet
        summary_ws = wb.create_sheet("Summary")
        summary_ws.title = "Summary"
        
        # Summary data
        total_exceptions = len(exceptions)
        unresolved_count = sum(1 for exc in exceptions if not exc[5])
        resolved_count = total_exceptions - unresolved_count
        
        summary_data = [
            ['Variance Report Summary'],
            [''],
            ['Report Date', report_date.isoformat()],
            ['Generated', datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
            [''],
            ['Total Exceptions', total_exceptions],
            ['Unresolved', unresolved_count],
            ['Resolved', resolved_count],
            [''],
            ['Exception Types:']
        ]
        
        # Add exception type breakdown
        type_counts = {}
        for exc in exceptions:
            exc_type = exc[2]
            type_counts[exc_type] = type_counts.get(exc_type, 0) + 1
        
        for exc_type, count in sorted(type_counts.items()):
            summary_data.append([exc_type, count])
        
        # Write summary data
        for row_idx, row_data in enumerate(summary_data, 1):
            for col_idx, cell_value in enumerate(row_data, 1):
                cell = summary_ws.cell(row=row_idx, column=col_idx, value=cell_value)
                if row_idx == 1:  # Title
                    cell.font = Font(bold=True, size=14)
                elif row_idx in [3, 4, 6, 7, 8]:  # Data rows
                    cell.font = Font(bold=True)
        
        # Create detailed exceptions sheet
        details_ws = wb.create_sheet("Exceptions")
        details_ws.title = "Exceptions"
        
        # Headers
        headers = [
            'ID', 'Date Found', 'Type', 'Hostname', 'Resolved',
            'Resolved Date', 'Resolved By', 'Manually Updated At',
            'Manually Updated By', 'Variance Status', 'Update Type', 'Organization'
        ]
        
        for col_idx, header in enumerate(headers, 1):
            cell = details_ws.cell(row=1, column=col_idx, value=header)
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="CCCCCC", end_color="CCCCCC", fill_type="solid")
        
        # Data rows
        for row_idx, exc in enumerate(exceptions, 2):
            details = exc[4] if exc[4] else {}
            org_name = details.get('tl_org_name', details.get('ninja_org_name', 'Unknown'))
            
            row_data = [
                exc[0],  # ID
                exc[1].isoformat() if exc[1] else '',  # Date Found
                exc[2],  # Type
                exc[3],  # Hostname
                'Yes' if exc[5] else 'No',  # Resolved
                exc[6].isoformat() if exc[6] else '',  # Resolved Date
                exc[7] or '',  # Resolved By
                exc[8].isoformat() if exc[8] else '',  # Manually Updated At
                exc[9] or '',  # Manually Updated By
                exc[10] or 'active',  # Variance Status
                exc[11] or '',  # Update Type
                org_name  # Organization
            ]
            
            for col_idx, value in enumerate(row_data, 1):
                details_ws.cell(row=row_idx, column=col_idx, value=value)
        
        # Auto-adjust column widths
        for ws in [summary_ws, details_ws]:
            for column in ws.columns:
                max_length = 0
                column_letter = get_column_letter(column[0].column)
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                ws.column_dimensions[column_letter].width = adjusted_width
        
        # Save to buffer
        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        
        # Generate filename
        filename = f"variances-{report_date.isoformat()}.xlsx"
        if exception_type:
            filename = f"variances-{exception_type.lower()}-{report_date.isoformat()}.xlsx"
        
        return Response(
            buffer.getvalue(),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={
                'Content-Disposition': f'attachment; filename={filename}',
                'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            }
        )


# Windows 11 24H2 Assessment Endpoints
@app.route('/api/windows-11-24h2/status', methods=['GET'])
def get_windows_11_24h2_status():
    """Get Windows 11 24H2 compatibility status summary"""
    try:
        with get_session() as session:
            # Query database for Windows 11 24H2 assessment results with enhanced status breakdown
            query = text("""
            SELECT 
                COUNT(*) as total_windows_devices,
                COUNT(CASE WHEN windows_11_24h2_capable = true THEN 1 END) as total_compatible_devices,
                COUNT(CASE WHEN windows_11_24h2_capable = false THEN 1 END) as incompatible_devices,
                COUNT(CASE WHEN windows_11_24h2_capable IS NULL THEN 1 END) as not_assessed_devices,
                COUNT(CASE WHEN windows_11_24h2_capable = true 
                          AND jsonb_extract_path_text(windows_11_24h2_deficiencies, 'passed_requirements') LIKE '%Windows 11 24H2 Already Installed%' 
                          THEN 1 END) as already_compatible_devices,
                COUNT(CASE WHEN windows_11_24h2_capable = true 
                          AND (jsonb_extract_path_text(windows_11_24h2_deficiencies, 'passed_requirements') NOT LIKE '%Windows 11 24H2 Already Installed%' 
                               OR jsonb_extract_path_text(windows_11_24h2_deficiencies, 'passed_requirements') IS NULL)
                          THEN 1 END) as compatible_for_upgrade_devices
            FROM device_snapshot ds
            JOIN vendor v ON ds.vendor_id = v.id
            WHERE v.name = 'Ninja' 
            AND ds.snapshot_date = (
                SELECT MAX(snapshot_date)
                FROM device_snapshot ds2
                JOIN vendor v2 ON ds2.vendor_id = v2.id
                WHERE v2.name = 'Ninja'
            )
            AND ds.os_name ILIKE '%windows%'
            AND ds.os_name NOT ILIKE '%server%'
            AND (ds.device_type_id IN (SELECT id FROM device_type WHERE code IN ('workstation')))
            AND ds.windows_11_24h2_capable IS NOT NULL
            """)
            
            result = session.execute(query).fetchone()
            
            # Get last assessment date
            last_assessment_query = text("""
            SELECT MAX(assessment_date) as last_assessment
            FROM (
                SELECT jsonb_extract_path_text(windows_11_24h2_deficiencies, 'assessment_date') as assessment_date
                FROM device_snapshot 
                WHERE windows_11_24h2_deficiencies IS NOT NULL 
                AND windows_11_24h2_deficiencies != '{}'
            ) as assessments
            """)
            
            last_assessment_result = session.execute(last_assessment_query).fetchone()
            last_assessment = last_assessment_result.last_assessment if last_assessment_result else None
            
            return jsonify({
                "total_windows_devices": result.total_windows_devices,
                "total_compatible_devices": result.total_compatible_devices,
                "already_compatible_devices": result.already_compatible_devices,
                "compatible_for_upgrade_devices": result.compatible_for_upgrade_devices,
                "incompatible_devices": result.incompatible_devices,
                "not_assessed_devices": result.not_assessed_devices,
                "compatibility_rate": round((result.total_compatible_devices / result.total_windows_devices * 100), 1) if result.total_windows_devices > 0 else 0,
                "last_assessment": last_assessment
            })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/windows-11-24h2/incompatible', methods=['GET'])
def get_incompatible_devices():
    """Get list of devices that are incompatible with Windows 11 24H2"""
    try:
        with get_session() as session:
            query = text("""
            SELECT 
                ds.hostname,
                ds.display_name,
                ds.organization_name,
                ds.location_name,
                ds.device_type_name,
                ds.billable_status_name,
                ds.os_name,
                ds.os_build,
                ds.os_release_id,
                ds.memory_gib,
                ds.memory_bytes,
                ds.cpu_model,
                ds.last_online,
                ds.created_at,
                ds.windows_11_24h2_deficiencies
            FROM device_snapshot ds
            JOIN vendor v ON ds.vendor_id = v.id
            WHERE v.name = 'Ninja'
            AND ds.snapshot_date = (
                SELECT MAX(snapshot_date)
                FROM device_snapshot ds2
                JOIN vendor v2 ON ds2.vendor_id = v2.id
                WHERE v2.name = 'Ninja'
            )
            AND ds.os_name ILIKE '%windows%'
            AND ds.os_name NOT ILIKE '%server%'
            AND ds.windows_11_24h2_capable IS NOT NULL
            AND ds.windows_11_24h2_capable = false
            AND (ds.device_type_id IN (SELECT id FROM device_type WHERE code IN ('workstation')))
            ORDER BY ds.organization_name, ds.hostname
            """)
            
            results = session.execute(query).fetchall()
            
            devices = []
            for row in results:
                deficiencies = row.windows_11_24h2_deficiencies if row.windows_11_24h2_deficiencies else {}
                
                devices.append({
                    # Modal column mapping - using database fields
                    "organization": row.organization_name if row.organization_name and row.organization_name.strip() else "Unknown",
                    "location": row.location_name or "Main Office",
                    "system_name": row.hostname,  # System hostname/identifier
                    "display_name": row.display_name or row.hostname,  # User-friendly device name
                    "device_type": row.device_type_name or "Desktop",  # Physical device type
                    "billable_status": row.billable_status_name or "Active",  # Billing status
                    "status": "Incompatible",  # Clear status
                    
                    # Additional fields for reference
                    "hostname": row.hostname,
                    "os_name": row.os_name,
                    "os_version": row.os_release_id,  # Use os_release_id as version
                    "os_build": row.os_build,
                    "deficiencies": deficiencies.get('deficiencies', []),
                    "assessment_date": _format_date_string(deficiencies.get('assessment_date', 'Unknown')),
                    
                    # New fields requested by Dashboard AI
                    "last_update": row.created_at.replace(microsecond=0).replace(tzinfo=None).isoformat() + 'Z' if row.created_at else None,
                    "last_contact": row.last_online.replace(microsecond=0).replace(tzinfo=None).isoformat() + 'Z' if row.last_online else None,
                    "cpu_model": row.cpu_model or "Unknown",
                    "memory_gib": float(row.memory_gib) if row.memory_gib else None,
                    "memory_bytes": int(row.memory_bytes) if row.memory_bytes else None,
                    "system_manufacturer": "Not Available",  # Not available in database
                    "system_model": "Not Available"  # Not available in database
                })
            
            return jsonify({
                "incompatible_devices": devices,
                "total_count": len(devices),
                "data_source": "Database (NinjaRMM fields populated)",
                "last_updated": datetime.utcnow().isoformat() + 'Z'
            })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/windows-11-24h2/compatible', methods=['GET'])
def get_compatible_devices():
    """Get list of devices that are compatible with Windows 11 24H2"""
    try:
        
        with get_session() as session:
            # Get compatible devices from database
            query = text("""
            SELECT 
                ds.hostname,
                ds.display_name,
                ds.organization_name,
                ds.location_name,
                ds.device_type_name,
                ds.billable_status_name,
                ds.os_name,
                ds.os_build,
                ds.os_release_id,
                ds.memory_gib,
                ds.memory_bytes,
                ds.cpu_model,
                ds.last_online,
                ds.created_at,
                ds.windows_11_24h2_deficiencies
            FROM device_snapshot ds
            JOIN vendor v ON ds.vendor_id = v.id
            WHERE v.name = 'Ninja'
            AND ds.snapshot_date = (
                SELECT MAX(snapshot_date)
                FROM device_snapshot ds2
                JOIN vendor v2 ON ds2.vendor_id = v2.id
                WHERE v2.name = 'Ninja'
            )
            AND ds.os_name ILIKE '%windows%'
            AND ds.os_name NOT ILIKE '%server%'
            AND ds.windows_11_24h2_capable IS NOT NULL
            AND ds.windows_11_24h2_capable = true
            AND (jsonb_extract_path_text(ds.windows_11_24h2_deficiencies, 'passed_requirements') NOT LIKE '%Windows 11 24H2 Already Installed%' 
                 OR jsonb_extract_path_text(ds.windows_11_24h2_deficiencies, 'passed_requirements') IS NULL)
            AND (ds.device_type_id IN (SELECT id FROM device_type WHERE code IN ('workstation')))
            ORDER BY ds.organization_name, ds.hostname
            """)
            
            results = session.execute(query).fetchall()
            
            devices = []
            for row in results:
                assessment_data = row.windows_11_24h2_deficiencies if row.windows_11_24h2_deficiencies else {}
                
                devices.append({
                    # Modal column mapping - using database fields
                    "organization": row.organization_name if row.organization_name and row.organization_name.strip() else "Unknown",
                    "location": row.location_name or "Main Office",
                    "system_name": row.hostname,  # System hostname/identifier
                    "display_name": row.display_name or row.hostname,  # User-friendly device name
                    "device_type": row.device_type_name or "Desktop",  # Physical device type
                    "billable_status": row.billable_status_name or "Active",  # Billing status
                    "status": "Compatible for Upgrade",  # Clear status
                    
                    # Additional fields for reference
                    "hostname": row.hostname,
                    "os_name": row.os_name,
                    "os_version": row.os_release_id,  # Use os_release_id as version
                    "os_build": row.os_build,
                    "passed_requirements": assessment_data.get('passed_requirements', []),
                    "assessment_date": _format_date_string(assessment_data.get('assessment_date', 'Unknown')),
                    
                    # New fields requested by Dashboard AI
                    "last_update": row.created_at.replace(microsecond=0).replace(tzinfo=None).isoformat() + 'Z' if row.created_at else None,
                    "last_contact": row.last_online.replace(microsecond=0).replace(tzinfo=None).isoformat() + 'Z' if row.last_online else None,
                    "cpu_model": row.cpu_model or "Unknown",
                    "memory_gib": float(row.memory_gib) if row.memory_gib else None,
                    "memory_bytes": int(row.memory_bytes) if row.memory_bytes else None,
                    "system_manufacturer": "Not Available",  # Not available in database
                    "system_model": "Not Available"  # Not available in database
                })
            
            return jsonify({
                "compatible_devices": devices,
                "total_count": len(devices),
                "data_source": "Database (NinjaRMM fields populated)",
                "last_updated": datetime.utcnow().isoformat() + 'Z'
            })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/windows-11-24h2/run', methods=['POST'])
def run_windows_11_24h2_assessment():
    """Manually trigger Windows 11 24H2 assessment"""
    try:
        import subprocess
        import os
        
        # Run the assessment script
        script_path = '/opt/es-inventory-hub/collectors/assessments/windows_11_24h2_assessment.py'
        
        if not os.path.exists(script_path):
            return jsonify({"error": "Assessment script not found"}), 404
        
        # Execute the assessment script
        result = subprocess.run([
            '/opt/es-inventory-hub/.venv/bin/python3',
            script_path
        ], capture_output=True, text=True, cwd='/opt/es-inventory-hub')
        
        if result.returncode == 0:
            return jsonify({
                "status": "success",
                "message": "Windows 11 24H2 assessment completed successfully",
                "output": result.stdout,
                "timestamp": datetime.utcnow().isoformat() + 'Z'
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Assessment failed",
                "error": result.stderr,
                "output": result.stdout
            }), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Documentation endpoints
@app.route('/api/docs', methods=['GET'])
def get_documentation():
    """Serve the main integration guide"""
    try:
        from flask import send_from_directory
        docs_dir = '/opt/es-inventory-hub/docs'
        return send_from_directory(docs_dir, 'HOW_TO_INTEGRATE_TO_DATABASE_GUIDE.md')
    except Exception as e:
        return jsonify({"error": f"Documentation not available: {str(e)}"}), 404

@app.route('/api/docs/<filename>', methods=['GET'])
def get_doc_file(filename):
    """Serve specific documentation files"""
    try:
        from flask import send_from_directory
        docs_dir = '/opt/es-inventory-hub/docs'
        return send_from_directory(docs_dir, filename)
    except Exception as e:
        return jsonify({"error": f"Documentation file '{filename}' not available: {str(e)}"}), 404


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
    print("  GET  /api/collectors/history - Collection history (last 10 runs)")
    print("  GET  /api/collectors/progress - Real-time collection progress")
    print("  GET  /api/exceptions - Get exceptions with filtering")
    print("  POST /api/exceptions/{id}/resolve - Resolve an exception")
    print("  POST /api/exceptions/{id}/mark-manually-fixed - Mark as manually fixed (NEW)")
    print("  POST /api/exceptions/mark-fixed-by-hostname - Mark exceptions fixed by hostname (NEW)")
    print("  POST /api/exceptions/bulk-update - Bulk exception operations (NEW)")
    print("  GET  /api/exceptions/status-summary - Exception status summary (NEW)")
    print("  GET  /api/devices/search?q={hostname} - Search devices (handles hostname truncation)")
    print()
    print("NEW EXPORT ENDPOINTS:")
    print("  GET  /api/variances/export/csv - Export variance data to CSV")
    print("  GET  /api/variances/export/pdf - Export variance data to PDF")
    print("  GET  /api/variances/export/excel - Export variance data to Excel")
    print("  GET  /api/variances/available-dates - Get available analysis dates")
    print("  GET  /api/variances/historical/{date} - Get historical variance data")
    print("  GET  /api/variances/trends - Get variance trends over time")
    print()
    print("WINDOWS 11 24H2 ASSESSMENT ENDPOINTS:")
    print("  GET  /api/windows-11-24h2/status - Windows 11 24H2 compatibility status summary")
    print("  GET  /api/windows-11-24h2/incompatible - List of incompatible devices")
    print("  GET  /api/windows-11-24h2/compatible - List of compatible devices")
    print("  POST /api/windows-11-24h2/run - Manually trigger Windows 11 24H2 assessment")
    print()
    print("DOCUMENTATION ENDPOINTS:")
    print("  GET  /api/docs - Main integration documentation")
    print("  GET  /api/docs/<filename> - Specific documentation files")
    print()
    print("Server will run on:")
    print("  HTTP:  http://localhost:5400 (development only)")
    print("  HTTPS: https://db-api.enersystems.com:5400 (production)")
    
    # Check for SSL certificates
    ssl_cert = '/opt/es-inventory-hub/ssl/api.crt'
    ssl_key = '/opt/es-inventory-hub/ssl/api.key'
    
    if os.path.exists(ssl_cert) and os.path.exists(ssl_key):
        print(f"SSL certificates found. Starting HTTPS server...")
        app.run(host='0.0.0.0', port=5400, debug=True, ssl_context=(ssl_cert, ssl_key))
    else:
        print(f"SSL certificates not found. Starting HTTP server...")
        print(f"To enable HTTPS, place SSL certificates at:")
        print(f"  Certificate: {ssl_cert}")
        print(f"  Private Key: {ssl_key}")
        app.run(host='0.0.0.0', port=5400, debug=True)

#!/usr/bin/env python3
"""
ES Inventory Hub API Server

Provides REST API endpoints for:
1. Accessing variance report data
2. Triggering collector runs
3. Checking system status

Usage:
    python3 api_server.py
    # Server runs on http://localhost:5500
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
DSN = 'postgresql://postgres:Xat162gT2Qsg4WDlO5r@localhost:5432/es_inventory_hub'
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
    latest_date = get_latest_matching_date()
    
    if not latest_date:
        return jsonify({
            "error": "No matching data found between vendors",
            "status": "out_of_sync"
        }), 400
    
    with get_session() as session:
        # Get exceptions for the latest date
        query = text("""
            SELECT id, date_found, type, hostname, details, resolved
            FROM exceptions
            WHERE date_found = :report_date
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
        
        return jsonify({
            "report_date": latest_date.isoformat(),
            "data_status": get_data_status(),
            "summary": {
                "total_exceptions": total_exceptions,
                "unresolved_count": unresolved_count,
                "resolved_count": total_exceptions - unresolved_count
            },
            "exceptions_by_type": by_type,
            "exception_counts": {exc_type: len(devices) for exc_type, devices in by_type.items()}
        })

@app.route('/api/variance-report/<date_str>', methods=['GET'])
def get_variance_report_by_date(date_str: str):
    """Get variance report for a specific date."""
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
        query = text("""
            SELECT id, date_found, type, hostname, details, resolved
            FROM exceptions
            WHERE date_found = :report_date
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
            # Run Ninja collector
            result = subprocess.run([
                'sudo', 'systemctl', 'start', 'ninja-collector.service'
            ], capture_output=True, text=True, timeout=300)
            
            results['ninja'] = {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
        
        if collector_type in ['threatlocker', 'both']:
            # Run ThreatLocker collector
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

if __name__ == '__main__':
    print("Starting ES Inventory Hub API Server...")
    print("Available endpoints:")
    print("  GET  /api/health - Health check")
    print("  GET  /api/status - System status")
    print("  GET  /api/variance-report/latest - Latest variance report")
    print("  GET  /api/variance-report/{date} - Variance report for specific date")
    print("  POST /api/collectors/run - Trigger collector runs")
    print("  GET  /api/collectors/status - Collector service status")
    print("  GET  /api/exceptions - Get exceptions with filtering")
    print("  POST /api/exceptions/{id}/resolve - Resolve an exception")
    print()
    print("Server will run on http://localhost:5500")
    
    app.run(host='0.0.0.0', port=5500, debug=True)

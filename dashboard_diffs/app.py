#!/usr/bin/env python3
"""
Flask dashboard application for es-inventory-hub
"""
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add the parent directory to the path
sys.path.append(str(Path(__file__).parent.parent))

from flask import Flask, jsonify, request, render_template
from sqlalchemy import func, and_, desc
from sqlalchemy.orm import Session

from common.config import config
from common.db import get_db_session
from common.logging import setup_logging, get_logger
from storage.models import Site, Device, DeviceSnapshot, DailyCounts, MonthEndCounts

logger = get_logger(__name__)

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False


def get_today_date() -> datetime:
    """Get today's date at midnight UTC"""
    return datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)


def get_last_month_end() -> datetime:
    """Get the last month-end date"""
    today = get_today_date()
    # Go to first day of current month, then subtract one day
    first_day_current_month = today.replace(day=1)
    last_month_end = first_day_current_month - timedelta(days=1)
    return last_month_end.replace(hour=0, minute=0, second=0, microsecond=0)


@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')


@app.route('/api/dashboard/today')
def get_today_summary():
    """Get today's inventory summary"""
    try:
        with get_db_session() as db:
            today = get_today_date()
            
            # Get today's daily counts for all sites
            today_counts = db.query(DailyCounts).filter(
                func.date(DailyCounts.count_date) == today.date()
            ).all()
            
            # Calculate totals
            totals = {
                'total_devices': sum(count.total_devices for count in today_counts),
                'servers': sum(count.servers for count in today_counts),
                'workstations': sum(count.workstations for count in today_counts),
                'spare_devices': sum(count.spare_devices for count in today_counts),
                'billable_devices': sum(count.billable_devices for count in today_counts),
                'ninja_devices': sum(count.ninja_devices for count in today_counts),
                'threatlocker_devices': sum(count.threatlocker_devices for count in today_counts)
            }
            
            # Get site breakdown
            sites_data = []
            for count in today_counts:
                site = db.query(Site).filter(Site.id == count.site_id).first()
                if site:
                    sites_data.append({
                        'site_name': site.name,
                        'total_devices': count.total_devices,
                        'servers': count.servers,
                        'workstations': count.workstations,
                        'spare_devices': count.spare_devices,
                        'billable_devices': count.billable_devices,
                        'ninja_devices': count.ninja_devices,
                        'threatlocker_devices': count.threatlocker_devices
                    })
            
            return jsonify({
                'date': today.isoformat(),
                'totals': totals,
                'sites': sites_data,
                'site_count': len(sites_data)
            })
            
    except Exception as e:
        logger.error(f"Failed to get today's summary: {e}")
        return jsonify({'error': 'Failed to retrieve today\'s summary'}), 500


@app.route('/api/dashboard/comparison')
def get_comparison():
    """Get comparison between today and last month-end"""
    try:
        with get_db_session() as db:
            today = get_today_date()
            last_month_end = get_last_month_end()
            
            # Get today's data
            today_counts = db.query(DailyCounts).filter(
                func.date(DailyCounts.count_date) == today.date()
            ).all()
            
            # Get last month-end data
            last_month_counts = db.query(MonthEndCounts).filter(
                func.date(MonthEndCounts.month_end_date) == last_month_end.date()
            ).all()
            
            # Calculate today's totals
            today_totals = {
                'total_devices': sum(count.total_devices for count in today_counts),
                'servers': sum(count.servers for count in today_counts),
                'workstations': sum(count.workstations for count in today_counts),
                'spare_devices': sum(count.spare_devices for count in today_counts),
                'billable_devices': sum(count.billable_devices for count in today_counts),
                'ninja_devices': sum(count.ninja_devices for count in today_counts),
                'threatlocker_devices': sum(count.threatlocker_devices for count in today_counts)
            }
            
            # Calculate last month-end totals
            last_month_totals = {
                'total_devices': sum(count.total_devices for count in last_month_counts),
                'servers': sum(count.servers for count in last_month_counts),
                'workstations': sum(count.workstations for count in last_month_counts),
                'spare_devices': sum(count.spare_devices for count in last_month_counts),
                'billable_devices': sum(count.billable_devices for count in last_month_counts),
                'ninja_devices': sum(count.ninja_devices for count in last_month_counts),
                'threatlocker_devices': sum(count.threatlocker_devices for count in last_month_counts)
            }
            
            # Calculate changes
            changes = {}
            for key in today_totals.keys():
                current = today_totals[key]
                previous = last_month_totals[key]
                change = current - previous
                change_percent = (change / previous * 100) if previous > 0 else 0
                
                changes[key] = {
                    'current': current,
                    'previous': previous,
                    'change': change,
                    'change_percent': round(change_percent, 1)
                }
            
            return jsonify({
                'today_date': today.isoformat(),
                'last_month_end_date': last_month_end.isoformat(),
                'today_totals': today_totals,
                'last_month_totals': last_month_totals,
                'changes': changes
            })
            
    except Exception as e:
        logger.error(f"Failed to get comparison: {e}")
        return jsonify({'error': 'Failed to retrieve comparison data'}), 500


@app.route('/api/dashboard/sites')
def get_sites_breakdown():
    """Get site-wise breakdown"""
    try:
        with get_db_session() as db:
            today = get_today_date()
            last_month_end = get_last_month_end()
            
            # Get all sites with their current counts
            sites = db.query(Site).all()
            sites_data = []
            
            for site in sites:
                # Get today's count for this site
                today_count = db.query(DailyCounts).filter(
                    and_(
                        DailyCounts.site_id == site.id,
                        func.date(DailyCounts.count_date) == today.date()
                    )
                ).first()
                
                # Get last month-end count for this site
                last_month_count = db.query(MonthEndCounts).filter(
                    and_(
                        MonthEndCounts.site_id == site.id,
                        func.date(MonthEndCounts.month_end_date) == last_month_end.date()
                    )
                ).first()
                
                site_data = {
                    'site_name': site.name,
                    'today': {
                        'total_devices': today_count.total_devices if today_count else 0,
                        'servers': today_count.servers if today_count else 0,
                        'workstations': today_count.workstations if today_count else 0,
                        'spare_devices': today_count.spare_devices if today_count else 0,
                        'billable_devices': today_count.billable_devices if today_count else 0
                    },
                    'last_month_end': {
                        'total_devices': last_month_count.total_devices if last_month_count else 0,
                        'servers': last_month_count.servers if last_month_count else 0,
                        'workstations': last_month_count.workstations if last_month_count else 0,
                        'spare_devices': last_month_count.spare_devices if last_month_count else 0,
                        'billable_devices': last_month_count.billable_devices if last_month_count else 0
                    }
                }
                
                # Calculate changes
                site_data['changes'] = {}
                for key in ['total_devices', 'servers', 'workstations', 'spare_devices', 'billable_devices']:
                    current = site_data['today'][key]
                    previous = site_data['last_month_end'][key]
                    change = current - previous
                    change_percent = (change / previous * 100) if previous > 0 else 0
                    
                    site_data['changes'][key] = {
                        'change': change,
                        'change_percent': round(change_percent, 1)
                    }
                
                sites_data.append(site_data)
            
            return jsonify({
                'sites': sites_data,
                'site_count': len(sites_data)
            })
            
    except Exception as e:
        logger.error(f"Failed to get sites breakdown: {e}")
        return jsonify({'error': 'Failed to retrieve sites breakdown'}), 500


@app.route('/api/dashboard/devices')
def get_devices():
    """Get device details with filtering"""
    try:
        with get_db_session() as db:
            # Get query parameters
            site_id = request.args.get('site_id', type=int)
            device_type = request.args.get('device_type')  # 'server', 'workstation', 'spare'
            source_system = request.args.get('source_system')  # 'ninja', 'threatlocker'
            limit = request.args.get('limit', 100, type=int)
            offset = request.args.get('offset', 0, type=int)
            
            # Build query
            query = db.query(Device).join(Site)
            
            if site_id:
                query = query.filter(Device.site_id == site_id)
            
            if device_type:
                if device_type == 'server':
                    query = query.filter(Device.is_server == True)
                elif device_type == 'workstation':
                    query = query.filter(Device.is_server == False)
                elif device_type == 'spare':
                    query = query.filter(Device.is_spare == True)
            
            if source_system:
                query = query.filter(Device.source_system == source_system)
            
            # Get total count
            total_count = query.count()
            
            # Apply pagination
            devices = query.offset(offset).limit(limit).all()
            
            # Format response
            devices_data = []
            for device in devices:
                device_data = {
                    'id': device.id,
                    'hostname': device.hostname,
                    'display_name': device.display_name,
                    'location': device.location,
                    'site_name': device.site.name,
                    'is_server': device.is_server,
                    'is_spare': device.is_spare,
                    'is_billable': device.is_billable,
                    'source_system': device.source_system,
                    'created_at': device.created_at.isoformat() if device.created_at else None,
                    'updated_at': device.updated_at.isoformat() if device.updated_at else None
                }
                devices_data.append(device_data)
            
            return jsonify({
                'devices': devices_data,
                'total_count': total_count,
                'limit': limit,
                'offset': offset,
                'has_more': (offset + limit) < total_count
            })
            
    except Exception as e:
        logger.error(f"Failed to get devices: {e}")
        return jsonify({'error': 'Failed to retrieve devices'}), 500


@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    try:
        with get_db_session() as db:
            # Test database connection
            db.execute("SELECT 1")
            
            # Get basic stats
            site_count = db.query(Site).count()
            device_count = db.query(Device).count()
            snapshot_count = db.query(DeviceSnapshot).count()
            
            return jsonify({
                'status': 'healthy',
                'database': 'connected',
                'stats': {
                    'sites': site_count,
                    'devices': device_count,
                    'snapshots': snapshot_count
                },
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 500


@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500


def main():
    """Main entry point"""
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Setup logging
    setup_logging()
    
    # Validate configuration
    try:
        config.validate()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    
    # Run Flask app
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('DASHBOARD_PORT', 5000)),
        debug=os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    )


if __name__ == "__main__":
    main()

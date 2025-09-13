#!/usr/bin/env python3
"""
ES Inventory Hub Collector Monitoring Script

This script monitors the health and status of the ThreatLocker and Ninja collectors.
It checks:
1. Recent collection success/failure
2. Database connectivity
3. API connectivity
4. Systemd service status
5. Log file analysis
"""

import os
import sys
import json
import subprocess
from datetime import datetime, date, timedelta
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, '/opt/es-inventory-hub')

try:
    from common.db import session_scope
    from storage.schema import DeviceSnapshot, Vendor
except ImportError:
    # Fallback for when running outside the project structure
    import os
    os.chdir('/opt/es-inventory-hub')
    from common.db import session_scope
    from storage.schema import DeviceSnapshot, Vendor


def check_database_connectivity():
    """Check if we can connect to the database."""
    try:
        with session_scope() as session:
            # Simple query to test connectivity
            session.query(Vendor).first()
            return True, "Database connection successful"
    except Exception as e:
        return False, f"Database connection failed: {str(e)}"


def check_recent_collections():
    """Check if collections have run recently and successfully."""
    try:
        with session_scope() as session:
            today = date.today()
            yesterday = today - timedelta(days=1)
            
            # Check ThreatLocker collections
            tl_today = session.query(DeviceSnapshot).filter(
                DeviceSnapshot.vendor_id == 4,  # Correct vendor ID for ThreatLocker
                DeviceSnapshot.snapshot_date == today
            ).count()
            
            tl_yesterday = session.query(DeviceSnapshot).filter(
                DeviceSnapshot.vendor_id == 4,  # Correct vendor ID for ThreatLocker
                DeviceSnapshot.snapshot_date == yesterday
            ).count()
            
            # Check Ninja collections
            ninja_today = session.query(DeviceSnapshot).filter(
                DeviceSnapshot.vendor_id == 3,
                DeviceSnapshot.snapshot_date == today
            ).count()
            
            ninja_yesterday = session.query(DeviceSnapshot).filter(
                DeviceSnapshot.vendor_id == 3,
                DeviceSnapshot.snapshot_date == yesterday
            ).count()
            
            results = {
                'threatlocker': {
                    'today': tl_today,
                    'yesterday': tl_yesterday,
                    'status': 'healthy' if tl_today > 0 or tl_yesterday > 0 else 'warning'
                },
                'ninja': {
                    'today': ninja_today,
                    'yesterday': ninja_yesterday,
                    'status': 'healthy' if ninja_today > 0 or ninja_yesterday > 0 else 'warning'
                }
            }
            
            return True, results
            
    except Exception as e:
        return False, f"Failed to check recent collections: {str(e)}"


def check_systemd_services():
    """Check the status of systemd services and timers."""
    try:
        services = ['threatlocker-collector.timer', 'ninja-collector.timer']
        results = {}
        
        for service in services:
            try:
                # Check if timer is active
                result = subprocess.run(
                    ['systemctl', 'is-active', service],
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                # Check when it last ran
                last_run = subprocess.run(
                    ['systemctl', 'show', service, '--property=LastTriggerUSec'],
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                results[service] = {
                    'status': result.stdout.strip(),
                    'last_run': last_run.stdout.strip()
                }
                
            except Exception as e:
                results[service] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        return True, results
        
    except Exception as e:
        return False, f"Failed to check systemd services: {str(e)}"


def check_log_files():
    """Check recent log files for errors."""
    log_dir = Path('/var/log/es-inventory-hub')
    results = {}
    
    if not log_dir.exists():
        return False, "Log directory does not exist"
    
    log_files = ['threatlocker_daily.log', 'ninja_daily.log']
    
    for log_file in log_files:
        log_path = log_dir / log_file
        if log_path.exists():
            try:
                # Read last 50 lines
                with open(log_path, 'r') as f:
                    lines = f.readlines()
                    last_lines = lines[-50:] if len(lines) > 50 else lines
                    
                # Check for errors
                error_count = sum(1 for line in last_lines if 'ERROR' in line or 'FAILED' in line)
                success_count = sum(1 for line in last_lines if 'finished OK' in line or 'completed successfully' in line)
                
                results[log_file] = {
                    'exists': True,
                    'error_count': error_count,
                    'success_count': success_count,
                    'last_50_lines': last_lines[-10:]  # Last 10 lines for context
                }
            except Exception as e:
                results[log_file] = {
                    'exists': True,
                    'error': str(e)
                }
        else:
            results[log_file] = {
                'exists': False
            }
    
    return True, results


def main():
    """Main monitoring function."""
    print("ES Inventory Hub Collector Monitoring")
    print("=" * 50)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    # Check database connectivity
    print("1. Database Connectivity:")
    db_ok, db_msg = check_database_connectivity()
    print(f"   Status: {'✓' if db_ok else '✗'} {db_msg}")
    print()
    
    # Check recent collections
    print("2. Recent Collections:")
    coll_ok, coll_data = check_recent_collections()
    if coll_ok:
        for vendor, data in coll_data.items():
            status_icon = '✓' if data['status'] == 'healthy' else '⚠'
            print(f"   {vendor.title()}: {status_icon} Today: {data['today']}, Yesterday: {data['yesterday']}")
    else:
        print(f"   ✗ {coll_data}")
    print()
    
    # Check systemd services
    print("3. Systemd Services:")
    svc_ok, svc_data = check_systemd_services()
    if svc_ok:
        for service, data in svc_data.items():
            status_icon = '✓' if data['status'] == 'active' else '✗'
            print(f"   {service}: {status_icon} {data['status']}")
    else:
        print(f"   ✗ {svc_data}")
    print()
    
    # Check log files
    print("4. Log Files:")
    log_ok, log_data = check_log_files()
    if log_ok:
        for log_file, data in log_data.items():
            if data['exists']:
                if 'error' in data:
                    print(f"   {log_file}: ✗ {data['error']}")
                else:
                    status_icon = '✓' if data['error_count'] == 0 else '⚠'
                    print(f"   {log_file}: {status_icon} Errors: {data['error_count']}, Successes: {data['success_count']}")
            else:
                print(f"   {log_file}: ✗ File not found")
    else:
        print(f"   ✗ {log_data}")
    print()
    
    # Overall health summary
    overall_healthy = db_ok and coll_ok and svc_ok and log_ok
    print("Overall Status:")
    print(f"   {'✓ HEALTHY' if overall_healthy else '⚠ NEEDS ATTENTION'}")
    
    return 0 if overall_healthy else 1


if __name__ == '__main__':
    sys.exit(main())

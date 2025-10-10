#!/usr/bin/env python3
"""
Real-time job monitoring script with accurate time tracking.
Uses database timestamps instead of manual calculations.
"""

import requests
import json
import time
from datetime import datetime

def get_job_status():
    """Get current job status from API."""
    try:
        response = requests.get(
            "https://localhost:5400/api/collectors/runs/latest",
            verify=False,
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        else:
            print(f"API Error: {response.status_code}")
            return None
    except Exception as e:
        print(f"Connection Error: {e}")
        return None

def format_duration(seconds):
    """Format duration in human-readable format."""
    if seconds is None:
        return "N/A"
    
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        return f"{minutes}m {remaining_seconds}s"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"

def monitor_jobs():
    """Monitor jobs with accurate time tracking."""
    print("🔍 ES Inventory Hub Job Monitor")
    print("=" * 50)
    
    while True:
        try:
            data = get_job_status()
            if not data:
                print("❌ Unable to connect to API")
                time.sleep(5)
                continue
            
            print(f"\n📊 Status Update - {datetime.now().strftime('%H:%M:%S')}")
            print("-" * 30)
            
            for job in data.get('latest_runs', []):
                job_name = job.get('job_name', 'Unknown')
                status = job.get('status', 'Unknown')
                progress = job.get('progress_percent', 'N/A')
                message = job.get('message', 'No message')
                started_at = job.get('started_at', 'N/A')
                ended_at = job.get('ended_at', 'N/A')
                duration = job.get('duration_seconds', 'N/A')
                
                # Status emoji
                status_emoji = {
                    'completed': '✅',
                    'running': '🔄',
                    'queued': '⏳',
                    'failed': '❌',
                    'cancelled': '⏹️'
                }.get(status, '❓')
                
                print(f"{status_emoji} {job_name}:")
                print(f"   Status: {status}")
                print(f"   Progress: {progress}%")
                print(f"   Message: {message}")
                print(f"   Started: {started_at}")
                if ended_at != 'N/A':
                    print(f"   Ended: {ended_at}")
                    print(f"   Duration: {format_duration(duration)}")
                else:
                    print(f"   Duration: Running...")
                print()
            
            # Check if all jobs are completed
            all_completed = all(
                job.get('status') == 'completed' 
                for job in data.get('latest_runs', [])
            )
            
            if all_completed:
                print("🎉 ALL JOBS COMPLETED SUCCESSFULLY!")
                break
            
            time.sleep(10)  # Check every 10 seconds
            
        except KeyboardInterrupt:
            print("\n👋 Monitoring stopped by user")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    monitor_jobs()

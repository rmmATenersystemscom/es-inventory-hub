#!/usr/bin/env python3

import os
import sys
sys.path.append('/opt/es-inventory-hub')

from common.database import get_session
from sqlalchemy import text

def debug_windows_11_query():
    """Debug the Windows 11 24H2 query to see what's happening"""
    
    with get_session() as session:
        print("=== Debugging Windows 11 24H2 Query ===")
        
        # Check total devices
        query = text("SELECT COUNT(*) FROM device_snapshot")
        result = session.execute(query).fetchone()
        print(f"Total devices in database: {result[0]}")
        
        # Check Windows devices
        query = text("SELECT COUNT(*) FROM device_snapshot WHERE os_name ILIKE '%windows%'")
        result = session.execute(query).fetchone()
        print(f"Windows devices: {result[0]}")
        
        # Check devices with 24H2 assessment
        query = text("SELECT COUNT(*) FROM device_snapshot WHERE windows_11_24h2_capable IS NOT NULL")
        result = session.execute(query).fetchone()
        print(f"Devices with 24H2 assessment: {result[0]}")
        
        # Check compatible devices
        query = text("SELECT COUNT(*) FROM device_snapshot WHERE windows_11_24h2_capable = true")
        result = session.execute(query).fetchone()
        print(f"Compatible devices: {result[0]}")
        
        # Check incompatible devices
        query = text("SELECT COUNT(*) FROM device_snapshot WHERE windows_11_24h2_capable = false")
        result = session.execute(query).fetchone()
        print(f"Incompatible devices: {result[0]}")
        
        # Check the exact query from the API
        query = text("""
        SELECT 
            COUNT(*) as total_windows_devices,
            COUNT(CASE WHEN windows_11_24h2_capable = true THEN 1 END) as compatible_devices,
            COUNT(CASE WHEN windows_11_24h2_capable = false THEN 1 END) as incompatible_devices,
            COUNT(CASE WHEN windows_11_24h2_capable IS NULL THEN 1 END) as not_assessed_devices
        FROM device_snapshot ds
        JOIN vendor v ON ds.vendor_id = v.id
        WHERE v.name = 'Ninja' 
        AND ds.os_name ILIKE '%windows%'
        AND (ds.device_type_id IN (SELECT id FROM device_type WHERE name IN ('Desktop', 'Laptop')))
        AND ds.windows_11_24h2_capable IS NOT NULL
        """)
        
        result = session.execute(query).fetchone()
        print(f"\nAPI Query Results:")
        print(f"  Total Windows devices: {result.total_windows_devices}")
        print(f"  Compatible devices: {result.compatible_devices}")
        print(f"  Incompatible devices: {result.incompatible_devices}")
        print(f"  Not assessed devices: {result.not_assessed_devices}")
        
        # Check a few sample devices
        query = text("""
        SELECT hostname, windows_11_24h2_capable, os_name 
        FROM device_snapshot 
        WHERE windows_11_24h2_capable IS NOT NULL 
        LIMIT 5
        """)
        
        results = session.execute(query).fetchall()
        print(f"\nSample devices with 24H2 assessment:")
        for row in results:
            print(f"  {row.hostname}: {row.windows_11_24h2_capable} ({row.os_name})")

if __name__ == "__main__":
    debug_windows_11_query()

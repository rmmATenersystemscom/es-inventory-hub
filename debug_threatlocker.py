#!/usr/bin/env python3
"""Debug script for ThreatLocker collection issues."""

import sys
import traceback
from datetime import date

# Add the project root to the path
sys.path.insert(0, '/opt/es-inventory-hub')

from collectors.threatlocker.api import fetch_devices
from collectors.threatlocker.mapping import normalize_threatlocker_device
from common.util import insert_snapshot, upsert_device_identity
from common.db import session_scope
from storage.schema import Vendor

def debug_threatlocker():
    """Debug the ThreatLocker collection process."""
    print("=== ThreatLocker Debug Script ===")
    
    try:
        # Step 1: Fetch devices
        print("Step 1: Fetching devices from API...")
        devices = fetch_devices(limit=1)
        print(f"✓ Fetched {len(devices)} devices")
        
        if not devices:
            print("❌ No devices fetched")
            return
        
        device = devices[0]
        print(f"✓ Sample device: {device.get('computerName', 'Unknown')}")
        
        # Step 2: Test normalization
        print("\nStep 2: Testing normalization...")
        try:
            normalized = normalize_threatlocker_device(device)
            print("✓ Normalization successful")
            print(f"✓ Normalized fields: {list(normalized.keys())}")
            print(f"✓ organization_id: {normalized.get('organization_id')} (type: {type(normalized.get('organization_id'))})")
        except Exception as e:
            print(f"❌ Normalization failed: {e}")
            traceback.print_exc()
            return
        
        # Step 3: Test database operations
        print("\nStep 3: Testing database operations...")
        with session_scope() as session:
            # Get vendor
            vendor = session.query(Vendor).filter_by(name='ThreatLocker').first()
            if not vendor:
                vendor = Vendor(name='ThreatLocker')
                session.add(vendor)
                session.flush()
            
            vendor_id = vendor.id
            print(f"✓ Vendor ID: {vendor_id}")
            
            # Test device identity creation
            print("Testing device identity creation...")
            device_identity_id = upsert_device_identity(
                session=session,
                vendor_id=vendor_id,
                vendor_device_key=normalized['vendor_device_key'],
                first_seen_date=date.today()
            )
            print(f"✓ Device identity ID: {device_identity_id}")
            
            # Test snapshot insertion
            print("Testing snapshot insertion...")
            try:
                insert_snapshot(
                    session=session,
                    snapshot_date=date.today(),
                    vendor_id=vendor_id,
                    device_identity_id=device_identity_id,
                    normalized=normalized
                )
                print("✓ Snapshot insertion successful")
            except Exception as e:
                print(f"❌ Snapshot insertion failed: {e}")
                traceback.print_exc()
                return
        
        print("\n✅ All tests passed!")
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    debug_threatlocker()

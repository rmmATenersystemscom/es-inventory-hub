#!/usr/bin/env python3
"""Debug SQLAlchemy statement creation."""

import sys
sys.path.insert(0, '/opt/es-inventory-hub')

from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert
from storage.schema import DeviceSnapshot
from common.db import session_scope

def debug_sqlalchemy():
    """Debug SQLAlchemy statement creation."""
    print("=== SQLAlchemy Debug ===")
    
    # Sample normalized data
    normalized = {
        'vendor_device_key': 'test-device',
        'hostname': 'test-hostname',
        'os_name': 'Windows 11',
        'organization_name': 'Test Org',
        'display_name': 'Test Device',
        'device_status': 'active',
        'last_online': '2025-09-12T22:00:00',
        'agent_install_timestamp': None,
        'organization_id': 'test-org-id',
        'computer_group': 'Test Group',
        'security_mode': 'Secure',
        'deny_count_1d': 5,
        'deny_count_3d': 15,
        'deny_count_7d': 35,
        'install_date': None,
        'is_locked_out': False,
        'is_isolated': False,
        'agent_version': '10.5.2',
        'has_checked_in': True
    }
    
    # Create values dictionary like in insert_snapshot
    values = {
        'snapshot_date': '2025-09-12',
        'vendor_id': 1,
        'device_identity_id': 1,
        'site_id': None,
        'device_type_id': None,
        'billing_status_id': None,
        'hostname': normalized.get('hostname'),
        'os_name': normalized.get('os_name'),
        'created_at': '2025-09-12T22:00:00',
        'organization_name': normalized.get('organization_name'),
        'display_name': normalized.get('display_name'),
        'device_status': normalized.get('device_status'),
        'last_online': normalized.get('last_online'),
        'agent_install_timestamp': normalized.get('agent_install_timestamp'),
        'organization_id': normalized.get('organization_id'),
        'computer_group': normalized.get('computer_group'),
        'security_mode': normalized.get('security_mode'),
        'deny_count_1d': normalized.get('deny_count_1d'),
        'deny_count_3d': normalized.get('deny_count_3d'),
        'deny_count_7d': normalized.get('deny_count_7d'),
        'install_date': normalized.get('install_date'),
        'is_locked_out': normalized.get('is_locked_out'),
        'is_isolated': normalized.get('is_isolated'),
        'agent_version': normalized.get('agent_version'),
        'has_checked_in': normalized.get('has_checked_in'),
    }
    
    print("Values dictionary keys:")
    for key in sorted(values.keys()):
        print(f"  {key}: {type(values[key])}")
    
    # Create the statement
    stmt = pg_insert(DeviceSnapshot.__table__).values(values)
    
    print("\nTesting stmt.excluded access:")
    try:
        print(f"  organization_id: {stmt.excluded.organization_id}")
        print("✓ organization_id access successful")
    except Exception as e:
        print(f"❌ organization_id access failed: {e}")
    
    try:
        print(f"  computer_group: {stmt.excluded.computer_group}")
        print("✓ computer_group access successful")
    except Exception as e:
        print(f"❌ computer_group access failed: {e}")
    
    # Test update_values creation
    print("\nTesting update_values creation:")
    try:
        update_values = {
            'organization_id': stmt.excluded.organization_id,
            'computer_group': stmt.excluded.computer_group,
        }
        print("✓ update_values creation successful")
    except Exception as e:
        print(f"❌ update_values creation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_sqlalchemy()

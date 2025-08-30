"""
NinjaRMM device mapping and business logic
"""
import json
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any

from common.logging import get_logger
from storage.models import Device, DeviceSnapshot, Site

logger = get_logger(__name__)


class NinjaDeviceMapper:
    """Map NinjaRMM device data to our database models"""
    
    @staticmethod
    def is_spare_device(device_data: Dict[str, Any]) -> bool:
        """
        Determine if a device is spare based on business rules:
        - Display Name contains "spare" (case-insensitive)
        - Location contains "spare" (case-insensitive)  
        - Node Class equals "VMWARE_VM_GUEST"
        """
        display_name = device_data.get('displayName', '').lower()
        node_class = device_data.get('nodeClass', '').upper()
        
        # Get location name from nested object or string
        location_name = ""
        if isinstance(device_data.get('location'), dict):
            location_name = device_data.get('location', {}).get('name', '').lower()
        else:
            location_name = str(device_data.get('location', '')).lower()
        
        is_spare = (
            'spare' in display_name or
            'spare' in location_name or
            node_class == 'VMWARE_VM_GUEST'
        )
        
        if is_spare:
            logger.debug(f"Device classified as spare", extra={
                'device_id': device_data.get('id'),
                'display_name': device_data.get('displayName'),
                'location_name': location_name,
                'node_class': node_class
            })
        
        return is_spare
    
    @staticmethod
    def is_server_device(device_data: Dict[str, Any]) -> bool:
        """
        Determine if a device is a server based on various indicators
        """
        # Get device information
        platform = device_data.get('platform', '').lower()
        os_name = (device_data.get('os') or {}).get('name', '').lower()
        system_name = (device_data.get('hostname') or device_data.get('deviceName') or device_data.get('systemName', '')).lower()
        device_type = device_data.get('deviceType', '').lower()
        
        # Check for virtualization devices first
        if device_type == 'vmhost':
            return True  # VM Hosts are servers
        
        # Define specific device types
        server_types = [
            'windows server', 'linux server', 'virtual server',
            'server', 'srv', 'dc', 'domain controller'
        ]
        
        # Check platform field first (most reliable)
        if any(server_type in platform for server_type in server_types):
            return True
        
        # Check OS information
        if any(server_os in os_name for server_os in ['windows server', 'linux server', 'server']):
            return True
        
        # Check system name patterns as fallback
        if any(server_pattern in system_name for server_pattern in ['server', 'srv', 'dc', 'sql', 'web', 'app']):
            return True
        
        return False
    
    @staticmethod
    def is_billable_device(device_data: Dict[str, Any]) -> bool:
        """
        Determine if a device is billable
        Spare devices are typically not billable
        """
        is_spare = NinjaDeviceMapper.is_spare_device(device_data)
        return not is_spare
    
    @staticmethod
    def map_to_device(device_data: Dict[str, Any], site: Site) -> Device:
        """Map NinjaRMM device data to Device model"""
        
        # Apply business rules
        is_spare = NinjaDeviceMapper.is_spare_device(device_data)
        is_server = NinjaDeviceMapper.is_server_device(device_data)
        is_billable = NinjaDeviceMapper.is_billable_device(device_data)
        
        # Get location name from nested object or string
        location_name = ""
        if isinstance(device_data.get('location'), dict):
            location_name = device_data.get('location', {}).get('name', '')
        else:
            location_name = str(device_data.get('location', ''))
        
        device = Device(
            site=site,
            ninja_device_id=str(device_data.get('id')),
            hostname=device_data.get('systemName') or device_data.get('hostname'),
            display_name=device_data.get('displayName'),
            location=location_name,
            node_class=device_data.get('deviceType'),
            is_spare=is_spare,
            is_server=is_server,
            is_billable=is_billable,
            source_system='ninja'
        )
        
        logger.debug(f"Mapped device", extra={
            'device_id': device.ninja_device_id,
            'hostname': device.hostname,
            'is_spare': is_spare,
            'is_server': is_server,
            'is_billable': is_billable
        })
        
        return device
    
    @staticmethod
    def map_to_snapshot(device_data: Dict[str, Any], device: Device, snapshot_date: datetime) -> DeviceSnapshot:
        """Map NinjaRMM device data to DeviceSnapshot model"""
        
        # Create full data payload
        full_data = json.dumps(device_data, sort_keys=True)
        data_hash = hashlib.sha256(full_data.encode()).hexdigest()
        
        # Parse last seen date
        last_seen = None
        if device_data.get('lastContact'):
            try:
                # Handle Unix timestamps (float/int)
                if isinstance(device_data['lastContact'], (int, float)):
                    last_seen = datetime.fromtimestamp(device_data['lastContact'])
                else:
                    # Handle ISO string format
                    last_seen = datetime.fromisoformat(device_data['lastContact'].replace('Z', '+00:00'))
            except (ValueError, TypeError):
                logger.warning(f"Could not parse lastContact date", extra={
                    'device_id': device.ninja_device_id,
                    'last_contact': device_data.get('lastContact')
                })
        
        # Get location name from nested object or string
        location_name = ""
        if isinstance(device_data.get('location'), dict):
            location_name = device_data.get('location', {}).get('name', '')
        else:
            location_name = str(device_data.get('location', ''))
        
        # Get OS information from nested object
        os_obj = device_data.get('os') or {}
        
        # Apply business rules for snapshot
        is_spare = NinjaDeviceMapper.is_spare_device(device_data)
        is_server = NinjaDeviceMapper.is_server_device(device_data)
        is_billable = NinjaDeviceMapper.is_billable_device(device_data)
        
        snapshot = DeviceSnapshot(
            device=device,
            snapshot_date=snapshot_date,
            data_hash=data_hash,
            source_system='ninja',
            ninja_data=full_data,
            hostname=device_data.get('systemName') or device_data.get('hostname'),
            display_name=device_data.get('displayName'),
            location=location_name,
            node_class=device_data.get('deviceType'),
            os_name=os_obj.get('name'),
            os_version=os_obj.get('buildNumber'),
            last_seen=last_seen,
            is_spare=is_spare,
            is_server=is_server,
            is_billable=is_billable
        )
        
        logger.debug(f"Created snapshot", extra={
            'device_id': device.ninja_device_id,
            'snapshot_date': snapshot_date.isoformat(),
            'data_hash': data_hash[:8]  # First 8 chars for logging
        })
        
        return snapshot
    
    @staticmethod
    def map_site_data(site_data: Dict[str, Any]) -> Site:
        """Map NinjaRMM site data to Site model"""
        
        site = Site(
            name=site_data.get('name', 'Unknown Site')
        )
        
        logger.debug(f"Mapped site", extra={
            'site_name': site.name,
            'ninja_site_id': str(site_data.get('id'))
        })
        
        return site

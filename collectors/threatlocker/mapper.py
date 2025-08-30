"""
ThreatLocker device mapping and business logic
"""
import json
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any

from common.logging import get_logger
from storage.models import Device, DeviceSnapshot, Site, SiteAlias

logger = get_logger(__name__)


class ThreatLockerDeviceMapper:
    """Map ThreatLocker device data to our database models"""
    
    @staticmethod
    def is_spare_device(device_data: Dict[str, Any]) -> bool:
        """
        Determine if a device is spare based on business rules:
        - Display Name contains "spare" (case-insensitive)
        - Location contains "spare" (case-insensitive)  
        - Device Type indicates virtualization
        """
        display_name = device_data.get('displayName', '').lower()
        computer_name = device_data.get('computerName', '').lower()
        location = device_data.get('location', '').lower()
        device_type = device_data.get('deviceType', '').lower()
        
        is_spare = (
            'spare' in display_name or
            'spare' in computer_name or
            'spare' in location or
            device_type in ['vm', 'virtual', 'guest']
        )
        
        if is_spare:
            logger.debug(f"Device classified as spare", extra={
                'device_id': device_data.get('id'),
                'display_name': device_data.get('displayName'),
                'computer_name': device_data.get('computerName'),
                'location': location,
                'device_type': device_type
            })
        
        return is_spare
    
    @staticmethod
    def is_server_device(device_data: Dict[str, Any]) -> bool:
        """
        Determine if a device is a server based on various indicators
        """
        # Get device information
        computer_name = device_data.get('computerName', '').lower()
        display_name = device_data.get('displayName', '').lower()
        os_name = device_data.get('operatingSystem', '').lower()
        device_type = device_data.get('deviceType', '').lower()
        
        # Check for virtualization devices first
        if device_type in ['vmhost', 'hypervisor']:
            return True  # VM Hosts are servers
        
        # Define specific device types
        server_types = [
            'windows server', 'linux server', 'virtual server',
            'server', 'srv', 'dc', 'domain controller'
        ]
        
        # Check computer name patterns
        if any(server_type in computer_name for server_type in server_types):
            return True
        
        # Check display name patterns
        if any(server_type in display_name for server_type in server_types):
            return True
        
        # Check OS information
        if any(server_os in os_name for server_os in ['windows server', 'linux server', 'server']):
            return True
        
        # Check for specific server patterns
        if any(server_pattern in computer_name for server_pattern in ['server', 'srv', 'dc', 'sql', 'web', 'app']):
            return True
        
        return False
    
    @staticmethod
    def is_billable_device(device_data: Dict[str, Any]) -> bool:
        """
        Determine if a device is billable
        Spare devices are typically not billable
        """
        is_spare = ThreatLockerDeviceMapper.is_spare_device(device_data)
        return not is_spare
    
    @staticmethod
    def map_to_device(device_data: Dict[str, Any], site: Site) -> Device:
        """Map ThreatLocker device data to Device model"""
        
        # Apply business rules
        is_spare = ThreatLockerDeviceMapper.is_spare_device(device_data)
        is_server = ThreatLockerDeviceMapper.is_server_device(device_data)
        is_billable = ThreatLockerDeviceMapper.is_billable_device(device_data)
        
        device = Device(
            site=site,
            threatlocker_device_id=str(device_data.get('id')),
            hostname=device_data.get('computerName') or device_data.get('displayName'),
            display_name=device_data.get('displayName'),
            location=device_data.get('location'),
            node_class=device_data.get('deviceType'),
            is_spare=is_spare,
            is_server=is_server,
            is_billable=is_billable,
            source_system='threatlocker'
        )
        
        logger.debug(f"Mapped device", extra={
            'device_id': device.threatlocker_device_id,
            'hostname': device.hostname,
            'is_spare': is_spare,
            'is_server': is_server,
            'is_billable': is_billable
        })
        
        return device
    
    @staticmethod
    def map_to_snapshot(device_data: Dict[str, Any], device: Device, snapshot_date: datetime) -> DeviceSnapshot:
        """Map ThreatLocker device data to DeviceSnapshot model"""
        
        # Create full data payload
        full_data = json.dumps(device_data, sort_keys=True)
        data_hash = hashlib.sha256(full_data.encode()).hexdigest()
        
        # Parse last seen date
        last_seen = None
        if device_data.get('lastCheckIn'):
            try:
                # Handle Unix timestamps (float/int)
                if isinstance(device_data['lastCheckIn'], (int, float)):
                    last_seen = datetime.fromtimestamp(device_data['lastCheckIn'])
                else:
                    # Handle ISO string format
                    last_seen = datetime.fromisoformat(device_data['lastCheckIn'].replace('Z', '+00:00'))
            except (ValueError, TypeError):
                logger.warning(f"Could not parse lastCheckIn date", extra={
                    'device_id': device.threatlocker_device_id,
                    'last_check_in': device_data.get('lastCheckIn')
                })
        
        # Apply business rules for snapshot
        is_spare = ThreatLockerDeviceMapper.is_spare_device(device_data)
        is_server = ThreatLockerDeviceMapper.is_server_device(device_data)
        is_billable = ThreatLockerDeviceMapper.is_billable_device(device_data)
        
        snapshot = DeviceSnapshot(
            device=device,
            snapshot_date=snapshot_date,
            data_hash=data_hash,
            source_system='threatlocker',
            threatlocker_data=full_data,
            hostname=device_data.get('computerName') or device_data.get('displayName'),
            display_name=device_data.get('displayName'),
            location=device_data.get('location'),
            node_class=device_data.get('deviceType'),
            os_name=device_data.get('operatingSystem'),
            os_version=device_data.get('osVersion'),
            last_seen=last_seen,
            is_spare=is_spare,
            is_server=is_server,
            is_billable=is_billable
        )
        
        logger.debug(f"Created snapshot", extra={
            'device_id': device.threatlocker_device_id,
            'snapshot_date': snapshot_date.isoformat(),
            'data_hash': data_hash[:8]  # First 8 chars for logging
        })
        
        return snapshot
    
    @staticmethod
    def map_site_data(site_data: Dict[str, Any]) -> Site:
        """Map ThreatLocker organization data to Site model"""
        
        site = Site(
            name=site_data.get('name', 'Unknown Organization')
        )
        
        logger.debug(f"Mapped site", extra={
            'site_name': site.name,
            'threatlocker_tenant_id': str(site_data.get('id'))
        })
        
        return site

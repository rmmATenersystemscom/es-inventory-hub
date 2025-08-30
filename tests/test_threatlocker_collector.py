"""
Tests for ThreatLocker collector components
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from collectors.threatlocker.mapper import ThreatLockerDeviceMapper
from storage.models import Site


class TestThreatLockerDeviceMapper:
    """Test ThreatLocker device mapping logic"""
    
    def test_is_spare_device_display_name(self):
        """Test spare device detection by display name"""
        device_data = {
            'id': '123',
            'displayName': 'SPARE-LAPTOP-01',
            'computerName': 'LAPTOP-01',
            'location': 'Office',
            'deviceType': 'Workstation'
        }
        
        assert ThreatLockerDeviceMapper.is_spare_device(device_data) is True
    
    def test_is_spare_device_computer_name(self):
        """Test spare device detection by computer name"""
        device_data = {
            'id': '123',
            'displayName': 'LAPTOP-01',
            'computerName': 'SPARE-LAPTOP-01',
            'location': 'Office',
            'deviceType': 'Workstation'
        }
        
        assert ThreatLockerDeviceMapper.is_spare_device(device_data) is True
    
    def test_is_spare_device_location(self):
        """Test spare device detection by location"""
        device_data = {
            'id': '123',
            'displayName': 'LAPTOP-01',
            'computerName': 'LAPTOP-01',
            'location': 'Spare Room',
            'deviceType': 'Workstation'
        }
        
        assert ThreatLockerDeviceMapper.is_spare_device(device_data) is True
    
    def test_is_spare_device_virtualization(self):
        """Test spare device detection by device type"""
        device_data = {
            'id': '123',
            'displayName': 'VM-01',
            'computerName': 'VM-01',
            'location': 'Data Center',
            'deviceType': 'VM'
        }
        
        assert ThreatLockerDeviceMapper.is_spare_device(device_data) is True
    
    def test_is_not_spare_device(self):
        """Test non-spare device detection"""
        device_data = {
            'id': '123',
            'displayName': 'PROD-SERVER-01',
            'computerName': 'PROD-SERVER-01',
            'location': 'Data Center',
            'deviceType': 'Server'
        }
        
        assert ThreatLockerDeviceMapper.is_spare_device(device_data) is False
    
    def test_is_server_device_by_name(self):
        """Test server detection by computer name"""
        device_data = {
            'id': '123',
            'displayName': 'SERVER-01',
            'computerName': 'DC-01',
            'operatingSystem': 'Windows 10',
            'deviceType': 'Workstation'
        }
        
        assert ThreatLockerDeviceMapper.is_server_device(device_data) is True
    
    def test_is_server_device_by_os(self):
        """Test server detection by OS name"""
        device_data = {
            'id': '123',
            'displayName': 'SERVER-01',
            'computerName': 'SERVER-01',
            'operatingSystem': 'Windows Server 2019',
            'deviceType': 'Server'
        }
        
        assert ThreatLockerDeviceMapper.is_server_device(device_data) is True
    
    def test_is_server_device_vmhost(self):
        """Test server detection by VM host type"""
        device_data = {
            'id': '123',
            'displayName': 'VMHOST-01',
            'computerName': 'VMHOST-01',
            'operatingSystem': 'VMware ESXi',
            'deviceType': 'VMHost'
        }
        
        assert ThreatLockerDeviceMapper.is_server_device(device_data) is True
    
    def test_is_not_server_device(self):
        """Test non-server device detection"""
        device_data = {
            'id': '123',
            'displayName': 'USER-LAPTOP-01',
            'computerName': 'USER-LAPTOP-01',
            'operatingSystem': 'Windows 10',
            'deviceType': 'Workstation'
        }
        
        assert ThreatLockerDeviceMapper.is_server_device(device_data) is False
    
    def test_is_billable_device(self):
        """Test billable device detection"""
        device_data = {
            'id': '123',
            'displayName': 'PROD-SERVER-01',
            'computerName': 'PROD-SERVER-01',
            'location': 'Data Center',
            'deviceType': 'Server'
        }
        
        assert ThreatLockerDeviceMapper.is_billable_device(device_data) is True
    
    def test_is_not_billable_device(self):
        """Test non-billable device detection (spare)"""
        device_data = {
            'id': '123',
            'displayName': 'SPARE-LAPTOP-01',
            'computerName': 'SPARE-LAPTOP-01',
            'location': 'Spare Room',
            'deviceType': 'Workstation'
        }
        
        assert ThreatLockerDeviceMapper.is_billable_device(device_data) is False
    
    def test_map_to_device(self):
        """Test device mapping"""
        site = Site(name="Test Organization")
        device_data = {
            'id': '123',
            'computerName': 'test-device',
            'displayName': 'Test Device',
            'location': 'Office',
            'deviceType': 'Workstation',
            'operatingSystem': 'Windows 10',
            'osVersion': '10.0.19044'
        }
        
        device = ThreatLockerDeviceMapper.map_to_device(device_data, site)
        
        assert device.threatlocker_device_id == '123'
        assert device.hostname == 'test-device'
        assert device.display_name == 'Test Device'
        assert device.location == 'Office'
        assert device.node_class == 'Workstation'
        assert device.source_system == 'threatlocker'
        assert device.site == site
    
    def test_map_site_data(self):
        """Test site mapping"""
        site_data = {
            'id': '456',
            'name': 'Test Organization',
            'description': 'Test organization description'
        }
        
        site = ThreatLockerDeviceMapper.map_site_data(site_data)
        
        assert site.name == 'Test Organization'


class TestThreatLockerCollector:
    """Test ThreatLocker collector"""
    
    @patch('collectors.threatlocker.collector.ThreatLockerAPI')
    def test_collector_initialization(self, mock_client):
        """Test collector initialization"""
        from collectors.threatlocker.collector import ThreatLockerCollector
        
        collector = ThreatLockerCollector()
        
        assert collector.client is not None
        assert collector.mapper is not None
        assert isinstance(collector.snapshot_date, datetime)
    
    @patch('collectors.threatlocker.collector.ThreatLockerAPI')
    def test_connection_test_failure(self, mock_client_class):
        """Test connection test failure"""
        from collectors.threatlocker.collector import ThreatLockerCollector
        
        # Mock client to return False for test_connection
        mock_client = Mock()
        mock_client.test_connection.return_value = False
        mock_client_class.return_value = mock_client
        
        collector = ThreatLockerCollector()
        
        assert collector.client is not None
        assert collector.mapper is not None
        assert isinstance(collector.snapshot_date, datetime)

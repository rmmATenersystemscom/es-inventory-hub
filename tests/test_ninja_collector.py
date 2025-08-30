"""
Tests for NinjaRMM collector components
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from collectors.ninja.mapper import NinjaDeviceMapper
from storage.models import Site


class TestNinjaDeviceMapper:
    """Test NinjaRMM device mapping logic"""
    
    def test_is_spare_device_display_name(self):
        """Test spare device detection by display name"""
        device_data = {
            'id': '123',
            'displayName': 'SPARE-LAPTOP-01',
            'location': 'Office',
            'nodeClass': 'WORKSTATION'
        }
        
        assert NinjaDeviceMapper.is_spare_device(device_data) is True
    
    def test_is_spare_device_location(self):
        """Test spare device detection by location"""
        device_data = {
            'id': '123',
            'displayName': 'LAPTOP-01',
            'location': 'Spare Room',
            'nodeClass': 'WORKSTATION'
        }
        
        assert NinjaDeviceMapper.is_spare_device(device_data) is True
    
    def test_is_spare_device_node_class(self):
        """Test spare device detection by node class"""
        device_data = {
            'id': '123',
            'displayName': 'VM-01',
            'location': 'Data Center',
            'nodeClass': 'VMWARE_VM_GUEST'
        }
        
        assert NinjaDeviceMapper.is_spare_device(device_data) is True
    
    def test_is_not_spare_device(self):
        """Test non-spare device detection"""
        device_data = {
            'id': '123',
            'displayName': 'PROD-SERVER-01',
            'location': 'Data Center',
            'nodeClass': 'SERVER'
        }
        
        assert NinjaDeviceMapper.is_spare_device(device_data) is False
    
    def test_is_server_device_by_os(self):
        """Test server detection by OS name"""
        device_data = {
            'id': '123',
            'displayName': 'SERVER-01',
            'os': {'name': 'Windows Server 2019'},
            'platform': 'Windows Server 2019',
            'nodeClass': 'SERVER'
        }
        
        assert NinjaDeviceMapper.is_server_device(device_data) is True
    
    def test_is_server_device_by_name(self):
        """Test server detection by system name"""
        device_data = {
            'id': '123',
            'displayName': 'DC-01',
            'systemName': 'DC-01',
            'os': {'name': 'Windows 10'},
            'platform': 'Windows 10',
            'nodeClass': 'WORKSTATION'
        }
        
        # DC-01 should be detected as a server (domain controller)
        assert NinjaDeviceMapper.is_server_device(device_data) is True
    
    def test_is_not_server_device(self):
        """Test non-server device detection"""
        device_data = {
            'id': '123',
            'displayName': 'USER-LAPTOP-01',
            'osName': 'Windows 10',
            'nodeClass': 'WORKSTATION'
        }
        
        assert NinjaDeviceMapper.is_server_device(device_data) is False
    
    def test_is_billable_device(self):
        """Test billable device detection"""
        device_data = {
            'id': '123',
            'displayName': 'PROD-SERVER-01',
            'location': 'Data Center',
            'nodeClass': 'SERVER'
        }
        
        assert NinjaDeviceMapper.is_billable_device(device_data) is True
    
    def test_is_not_billable_device(self):
        """Test non-billable device detection (spare)"""
        device_data = {
            'id': '123',
            'displayName': 'SPARE-LAPTOP-01',
            'location': 'Spare Room',
            'nodeClass': 'WORKSTATION'
        }
        
        assert NinjaDeviceMapper.is_billable_device(device_data) is False
    
    def test_map_to_device(self):
        """Test device mapping"""
        site = Site(name="Test Site")
        device_data = {
            'id': '123',
            'hostname': 'test-device',
            'displayName': 'Test Device',
            'location': 'Office',
            'deviceType': 'WORKSTATION',
            'osName': 'Windows 10',
            'osVersion': '10.0.19044'
        }
        
        device = NinjaDeviceMapper.map_to_device(device_data, site)
        
        assert device.ninja_device_id == '123'
        assert device.hostname == 'test-device'
        assert device.display_name == 'Test Device'
        assert device.location == 'Office'
        assert device.node_class == 'WORKSTATION'
        assert device.source_system == 'ninja'
        assert device.site == site
    
    def test_map_site_data(self):
        """Test site mapping"""
        site_data = {
            'id': '456',
            'name': 'Test Organization',
            'description': 'Test organization description'
        }
        
        site = NinjaDeviceMapper.map_site_data(site_data)
        
        assert site.name == 'Test Organization'


class TestNinjaCollector:
    """Test NinjaRMM collector"""
    
    @patch('collectors.ninja.collector.NinjaRMMAPI')
    def test_collector_initialization(self, mock_client):
        """Test collector initialization"""
        from collectors.ninja.collector import NinjaCollector
        
        collector = NinjaCollector()
        
        assert collector.client is not None
        assert collector.mapper is not None
        assert isinstance(collector.snapshot_date, datetime)
    
    @patch('collectors.ninja.collector.NinjaRMMAPI')
    def test_connection_test_failure(self, mock_client_class):
        """Test connection test failure"""
        from collectors.ninja.collector import NinjaCollector
        
        # Mock client to return False for test_connection
        mock_client = Mock()
        mock_client.test_connection.return_value = False
        mock_client_class.return_value = mock_client
        
        collector = NinjaCollector()
        
        # This should raise SystemExit
        with pytest.raises(SystemExit):
            collector.run()

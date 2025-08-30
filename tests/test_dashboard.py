#!/usr/bin/env python3
"""
Tests for Flask dashboard application
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch
from flask import Flask

from dashboard_diffs.app import app, get_today_date, get_last_month_end


@pytest.fixture
def client():
    """Create a test client for the Flask app"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


class TestDashboardApp:
    """Test dashboard application functionality"""
    
    def test_get_today_date(self):
        """Test today's date calculation"""
        today = get_today_date()
        
        # Should be today at midnight UTC
        now = datetime.now(timezone.utc)
        expected = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        assert today.date() == expected.date()
        assert today.hour == 0
        assert today.minute == 0
        assert today.second == 0
        assert today.microsecond == 0
    
    def test_get_last_month_end(self):
        """Test last month-end date calculation"""
        # Test with a known date
        with patch('dashboard_diffs.app.get_today_date') as mock_today:
            # Set today to March 15, 2024
            mock_today.return_value = datetime(2024, 3, 15, tzinfo=timezone.utc)
            
            last_month_end = get_last_month_end()
            
            # Should be February 29, 2024 (leap year)
            assert last_month_end == datetime(2024, 2, 29, tzinfo=timezone.utc)
    
    def test_index_route(self, client):
        """Test main dashboard page"""
        response = client.get('/')
        
        assert response.status_code == 200
        assert b'ES Inventory Hub' in response.data
        assert b'Device Inventory Dashboard' in response.data
    
    def test_health_check_success(self, client):
        """Test health check endpoint with successful database connection"""
        with patch('dashboard_diffs.app.get_db_session') as mock_session:
            mock_db = Mock()
            mock_session.return_value.__enter__.return_value = mock_db
            
            # Mock database queries
            mock_db.execute.return_value = None
            mock_db.query.return_value.count.return_value = 5
            
            response = client.get('/api/health')
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['status'] == 'healthy'
            assert data['database'] == 'connected'
            assert 'stats' in data
            assert 'timestamp' in data
    
    def test_health_check_failure(self, client):
        """Test health check endpoint with database failure"""
        with patch('dashboard_diffs.app.get_db_session') as mock_session:
            mock_session.side_effect = Exception("Database connection failed")
            
            response = client.get('/api/health')
            
            assert response.status_code == 500
            data = response.get_json()
            assert data['status'] == 'unhealthy'
            assert 'error' in data
    
    def test_get_today_summary_success(self, client):
        """Test today's summary endpoint with data"""
        with patch('dashboard_diffs.app.get_db_session') as mock_session:
            mock_db = Mock()
            mock_session.return_value.__enter__.return_value = mock_db
            
            # Mock today's date
            today = datetime(2024, 3, 15, tzinfo=timezone.utc)
            
            # Mock daily counts
            mock_count = Mock()
            mock_count.total_devices = 100
            mock_count.servers = 20
            mock_count.workstations = 80
            mock_count.spare_devices = 5
            mock_count.billable_devices = 95
            mock_count.ninja_devices = 60
            mock_count.threatlocker_devices = 40
            mock_count.site_id = 1
            
            # Mock site
            mock_site = Mock()
            mock_site.name = "Test Site"
            
            # Setup query chain
            mock_db.query.return_value.filter.return_value.all.return_value = [mock_count]
            mock_db.query.return_value.filter.return_value.first.return_value = mock_site
            
            with patch('dashboard_diffs.app.get_today_date', return_value=today):
                response = client.get('/api/dashboard/today')
                
                assert response.status_code == 200
                data = response.get_json()
                assert data['date'] == today.isoformat()
                assert data['totals']['total_devices'] == 100
                assert data['totals']['servers'] == 20
                assert data['totals']['workstations'] == 80
                assert len(data['sites']) == 1
                assert data['sites'][0]['site_name'] == "Test Site"
    
    def test_get_today_summary_no_data(self, client):
        """Test today's summary endpoint with no data"""
        with patch('dashboard_diffs.app.get_db_session') as mock_session:
            mock_db = Mock()
            mock_session.return_value.__enter__.return_value = mock_db
            
            # Mock empty results
            mock_db.query.return_value.filter.return_value.all.return_value = []
            
            with patch('dashboard_diffs.app.get_today_date', return_value=datetime(2024, 3, 15, tzinfo=timezone.utc)):
                response = client.get('/api/dashboard/today')
                
                assert response.status_code == 200
                data = response.get_json()
                assert data['totals']['total_devices'] == 0
                assert len(data['sites']) == 0
    
    def test_get_comparison_success(self, client):
        """Test comparison endpoint with data"""
        with patch('dashboard_diffs.app.get_db_session') as mock_session:
            mock_db = Mock()
            mock_session.return_value.__enter__.return_value = mock_db
            
            # Mock dates
            today = datetime(2024, 3, 15, tzinfo=timezone.utc)
            last_month_end = datetime(2024, 2, 29, tzinfo=timezone.utc)
            
            # Mock today's counts
            mock_today_count = Mock()
            mock_today_count.total_devices = 100
            mock_today_count.servers = 20
            mock_today_count.workstations = 80
            mock_today_count.spare_devices = 5
            mock_today_count.billable_devices = 95
            mock_today_count.ninja_devices = 60
            mock_today_count.threatlocker_devices = 40
            
            # Mock last month's counts
            mock_last_month_count = Mock()
            mock_last_month_count.total_devices = 90
            mock_last_month_count.servers = 18
            mock_last_month_count.workstations = 72
            mock_last_month_count.spare_devices = 4
            mock_last_month_count.billable_devices = 86
            mock_last_month_count.ninja_devices = 55
            mock_last_month_count.threatlocker_devices = 35
            
            # Setup query chain
            mock_db.query.return_value.filter.return_value.all.side_effect = [
                [mock_today_count],  # Today's counts
                [mock_last_month_count]  # Last month's counts
            ]
            
            with patch('dashboard_diffs.app.get_today_date', return_value=today), \
                 patch('dashboard_diffs.app.get_last_month_end', return_value=last_month_end):
                
                response = client.get('/api/dashboard/comparison')
                
                assert response.status_code == 200
                data = response.get_json()
                assert data['today_date'] == today.isoformat()
                assert data['last_month_end_date'] == last_month_end.isoformat()
                assert data['today_totals']['total_devices'] == 100
                assert data['last_month_totals']['total_devices'] == 90
                assert data['changes']['total_devices']['change'] == 10
                assert data['changes']['total_devices']['change_percent'] == 11.1
    
    def test_get_sites_breakdown_success(self, client):
        """Test sites breakdown endpoint"""
        with patch('dashboard_diffs.app.get_db_session') as mock_session:
            mock_db = Mock()
            mock_session.return_value.__enter__.return_value = mock_db
            
            # Mock dates
            today = datetime(2024, 3, 15, tzinfo=timezone.utc)
            last_month_end = datetime(2024, 2, 29, tzinfo=timezone.utc)
            
            # Mock site
            mock_site = Mock()
            mock_site.id = 1
            mock_site.name = "Test Site"
            
            # Mock today's count
            mock_today_count = Mock()
            mock_today_count.total_devices = 50
            mock_today_count.servers = 10
            mock_today_count.workstations = 40
            mock_today_count.spare_devices = 2
            mock_today_count.billable_devices = 48
            
            # Mock last month's count
            mock_last_month_count = Mock()
            mock_last_month_count.total_devices = 45
            mock_last_month_count.servers = 9
            mock_last_month_count.workstations = 36
            mock_last_month_count.spare_devices = 1
            mock_last_month_count.billable_devices = 44
            
            # Setup query chain
            mock_db.query.return_value.all.return_value = [mock_site]
            mock_db.query.return_value.filter.return_value.first.side_effect = [
                mock_today_count,  # Today's count for site
                mock_last_month_count  # Last month's count for site
            ]
            
            with patch('dashboard_diffs.app.get_today_date', return_value=today), \
                 patch('dashboard_diffs.app.get_last_month_end', return_value=last_month_end):
                
                response = client.get('/api/dashboard/sites')
                
                assert response.status_code == 200
                data = response.get_json()
                assert len(data['sites']) == 1
                assert data['sites'][0]['site_name'] == "Test Site"
                assert data['sites'][0]['today']['total_devices'] == 50
                assert data['sites'][0]['last_month_end']['total_devices'] == 45
                assert data['sites'][0]['changes']['total_devices']['change'] == 5
    
    def test_get_devices_success(self, client):
        """Test devices endpoint with filtering"""
        with patch('dashboard_diffs.app.get_db_session') as mock_session:
            mock_db = Mock()
            mock_session.return_value.__enter__.return_value = mock_db
            
            # Mock site
            mock_site = Mock()
            mock_site.name = "Test Site"
            
            # Mock device
            mock_device = Mock()
            mock_device.id = 1
            mock_device.hostname = "test-server"
            mock_device.display_name = "Test Server"
            mock_device.location = "Data Center"
            mock_device.is_server = True
            mock_device.is_spare = False
            mock_device.is_billable = True
            mock_device.source_system = "ninja"
            mock_device.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
            mock_device.updated_at = datetime(2024, 3, 15, tzinfo=timezone.utc)
            mock_device.site = mock_site
            
            # Setup query chain
            mock_query = Mock()
            mock_query.join.return_value = mock_query
            mock_query.filter.return_value = mock_query
            mock_query.count.return_value = 1
            mock_query.offset.return_value = mock_query
            mock_query.limit.return_value = mock_query
            mock_query.all.return_value = [mock_device]
            
            mock_db.query.return_value = mock_query
            
            response = client.get('/api/dashboard/devices?device_type=server&source_system=ninja&limit=10&offset=0')
            
            assert response.status_code == 200
            data = response.get_json()
            assert len(data['devices']) == 1
            assert data['devices'][0]['hostname'] == "test-server"
            assert data['devices'][0]['is_server'] == True
            assert data['devices'][0]['source_system'] == "ninja"
            assert data['total_count'] == 1
            assert data['limit'] == 10
            assert data['offset'] == 0
    
    def test_get_devices_no_filters(self, client):
        """Test devices endpoint without filters"""
        with patch('dashboard_diffs.app.get_db_session') as mock_session:
            mock_db = Mock()
            mock_session.return_value.__enter__.return_value = mock_db
            
            # Setup empty query
            mock_query = Mock()
            mock_query.join.return_value = mock_query
            mock_query.filter.return_value = mock_query
            mock_query.count.return_value = 0
            mock_query.offset.return_value = mock_query
            mock_query.limit.return_value = mock_query
            mock_query.all.return_value = []
            
            mock_db.query.return_value = mock_query
            
            response = client.get('/api/dashboard/devices')
            
            assert response.status_code == 200
            data = response.get_json()
            assert len(data['devices']) == 0
            assert data['total_count'] == 0
    
    def test_error_handlers(self, client):
        """Test error handlers"""
        # Test 404 handler
        response = client.get('/nonexistent-endpoint')
        assert response.status_code == 404
        data = response.get_json()
        assert data['error'] == 'Not found'
    
    def test_database_error_handling(self, client):
        """Test database error handling"""
        with patch('dashboard_diffs.app.get_db_session') as mock_session:
            mock_session.side_effect = Exception("Database error")
            
            response = client.get('/api/dashboard/today')
            
            assert response.status_code == 500
            data = response.get_json()
            assert data['error'] == 'Failed to retrieve today\'s summary'


class TestDashboardIntegration:
    """Integration tests for dashboard functionality"""
    
    def test_dashboard_initialization(self):
        """Test dashboard app initialization"""
        assert app is not None
        assert isinstance(app, Flask)
        assert app.config['JSON_SORT_KEYS'] == False
    
    def test_date_calculations_edge_cases(self):
        """Test date calculation edge cases"""
        # Test year boundary
        with patch('dashboard_diffs.app.get_today_date') as mock_today:
            mock_today.return_value = datetime(2024, 1, 1, tzinfo=timezone.utc)
            last_month_end = get_last_month_end()
            assert last_month_end == datetime(2023, 12, 31, tzinfo=timezone.utc)
        
        # Test leap year
        with patch('dashboard_diffs.app.get_today_date') as mock_today:
            mock_today.return_value = datetime(2024, 3, 1, tzinfo=timezone.utc)
            last_month_end = get_last_month_end()
            assert last_month_end == datetime(2024, 2, 29, tzinfo=timezone.utc)

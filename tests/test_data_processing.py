#!/usr/bin/env python3
"""
Tests for data processing and rollup generation
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from storage.rollups import DataProcessor
from storage.models import Site, Device, DeviceSnapshot, DailyCounts, MonthEndCounts


class TestDataProcessor:
    """Test data processing functionality"""
    
    @pytest.fixture
    def processor(self):
        """Create a data processor instance"""
        return DataProcessor()
    
    @pytest.fixture
    def sample_site(self):
        """Create a sample site"""
        return Site(
            id=1,
            name="Test Site"
        )
    
    @pytest.fixture
    def sample_device(self, sample_site):
        """Create a sample device"""
        return Device(
            id=1,
            site_id=sample_site.id,
            ninja_device_id="ninja-device-123",
            hostname="test-server",
            display_name="Test Server",
            is_spare=False,
            is_server=True,
            is_billable=True,
            source_system="ninja"
        )
    
    @pytest.fixture
    def sample_snapshots(self, sample_device):
        """Create sample device snapshots"""
        base_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        
        return [
            DeviceSnapshot(
                id=1,
                device_id=sample_device.id,
                snapshot_date=base_date,
                data_hash="abc123",
                source_system="ninja",
                hostname="test-server",
                display_name="Test Server",
                is_spare=False,
                is_server=True,
                is_billable=True
            ),
            DeviceSnapshot(
                id=2,
                device_id=sample_device.id,
                snapshot_date=base_date,
                data_hash="def456",
                source_system="threatlocker",
                hostname="test-workstation",
                display_name="Test Workstation",
                is_spare=True,
                is_server=False,
                is_billable=False
            )
        ]
    
    def test_calculate_device_counts(self, processor, sample_snapshots):
        """Test device count calculation"""
        counts = processor._calculate_device_counts(sample_snapshots)
        
        assert counts['total_devices'] == 2
        assert counts['servers'] == 1
        assert counts['workstations'] == 1
        assert counts['spare_devices'] == 1
        assert counts['billable_devices'] == 1
        assert counts['ninja_devices'] == 1
        assert counts['threatlocker_devices'] == 1
    
    def test_generate_daily_rollups_new_count(self, processor, sample_site, sample_device, sample_snapshots):
        """Test creating new daily rollup counts"""
        mock_db = Mock(spec=Session)
        
        # Mock database queries
        mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = sample_snapshots
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Mock site query
        mock_db.query.return_value.all.return_value = [sample_site]
        
        stats = processor.generate_daily_rollups(mock_db)
        
        assert stats['sites_processed'] == 1
        assert stats['rollups_created'] == 1
        assert stats['rollups_updated'] == 0
        assert stats['errors'] == 0
        
        # Verify daily count was added
        mock_db.add.assert_called_once()
        added_count = mock_db.add.call_args[0][0]
        assert isinstance(added_count, DailyCounts)
        assert added_count.site_id == sample_site.id
        assert added_count.total_devices == 2
    
    def test_generate_daily_rollups_update_existing(self, processor, sample_site, sample_device, sample_snapshots):
        """Test updating existing daily rollup counts"""
        mock_db = Mock(spec=Session)
        
        # Create existing daily count
        existing_count = DailyCounts(
            id=1,
            count_date=datetime.now(timezone.utc),
            site_id=sample_site.id,
            total_devices=0
        )
        
        # Mock database queries
        mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = sample_snapshots
        mock_db.query.return_value.filter.return_value.first.return_value = existing_count
        mock_db.query.return_value.all.return_value = [sample_site]
        
        stats = processor.generate_daily_rollups(mock_db)
        
        assert stats['sites_processed'] == 1
        assert stats['rollups_created'] == 0
        assert stats['rollups_updated'] == 1
        assert stats['errors'] == 0
        
        # Verify existing count was updated
        assert existing_count.total_devices == 2
        assert existing_count.servers == 1
        assert existing_count.workstations == 1
    
    def test_generate_month_end_snapshots_not_month_end(self, processor):
        """Test month-end snapshot generation when not month-end"""
        mock_db = Mock(spec=Session)
        
        # Set date to middle of month
        processor.snapshot_date = datetime(2024, 1, 15, tzinfo=timezone.utc)
        
        stats = processor.generate_month_end_snapshots(mock_db)
        
        assert stats['month_end_snapshots_created'] == 0
        assert stats['month_end_snapshots_updated'] == 0
        
        # Verify no database operations were performed
        mock_db.query.assert_not_called()
        mock_db.add.assert_not_called()
    
    def test_generate_month_end_snapshots_month_end(self, processor, sample_site, sample_device, sample_snapshots):
        """Test month-end snapshot generation on month-end"""
        mock_db = Mock(spec=Session)
        
        # Set date to last day of month
        processor.snapshot_date = datetime(2024, 1, 31, tzinfo=timezone.utc)
        
        # Update snapshot dates to match
        for snapshot in sample_snapshots:
            snapshot.snapshot_date = processor.snapshot_date
        
        # Mock database queries
        mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = sample_snapshots
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db.query.return_value.all.return_value = [sample_site]
        
        stats = processor.generate_month_end_snapshots(mock_db)
        
        assert stats['month_end_snapshots_created'] == 1
        assert stats['month_end_snapshots_updated'] == 0
        assert stats['errors'] == 0
        
        # Verify month-end count was added
        mock_db.add.assert_called_once()
        added_count = mock_db.add.call_args[0][0]
        assert isinstance(added_count, MonthEndCounts)
        assert added_count.site_id == sample_site.id
        assert added_count.total_devices == 2
    
    def test_enforce_retention_policy(self, processor):
        """Test retention policy enforcement"""
        mock_db = Mock(spec=Session)
        
        # Create old snapshots and counts
        old_date = datetime.now(timezone.utc) - timedelta(days=70)
        old_snapshots = [
            DeviceSnapshot(id=1, snapshot_date=old_date),
            DeviceSnapshot(id=2, snapshot_date=old_date)
        ]
        old_daily_counts = [
            DailyCounts(id=1, count_date=old_date),
            DailyCounts(id=2, count_date=old_date)
        ]
        
        # Mock database queries
        mock_db.query.return_value.filter.return_value.all.side_effect = [
            old_snapshots,  # For snapshots
            old_daily_counts,  # For daily counts
            []  # For month-end counts (empty)
        ]
        
        stats = processor.enforce_retention_policy(mock_db)
        
        assert stats['old_snapshots_deleted'] == 2
        assert stats['old_daily_counts_deleted'] == 2
        assert stats['month_end_counts_preserved'] == 0
        
        # Verify deletions were called
        assert mock_db.delete.call_count == 4
    
    def test_update_daily_count(self, processor):
        """Test updating existing daily count"""
        daily_count = DailyCounts(
            id=1,
            count_date=datetime.now(timezone.utc),
            site_id=1,
            total_devices=0
        )
        
        counts = {
            'total_devices': 5,
            'servers': 2,
            'workstations': 3,
            'spare_devices': 1,
            'billable_devices': 4,
            'ninja_devices': 3,
            'threatlocker_devices': 2
        }
        
        processor._update_daily_count(daily_count, counts)
        
        assert daily_count.total_devices == 5
        assert daily_count.servers == 2
        assert daily_count.workstations == 3
        assert daily_count.spare_devices == 1
        assert daily_count.billable_devices == 4
        assert daily_count.ninja_devices == 3
        assert daily_count.threatlocker_devices == 2
        assert daily_count.updated_at is not None
    
    def test_update_month_end_count(self, processor):
        """Test updating existing month-end count"""
        month_end_count = MonthEndCounts(
            id=1,
            month_end_date=datetime.now(timezone.utc),
            site_id=1,
            total_devices=0
        )
        
        counts = {
            'total_devices': 10,
            'servers': 4,
            'workstations': 6,
            'spare_devices': 2,
            'billable_devices': 8,
            'ninja_devices': 6,
            'threatlocker_devices': 4
        }
        
        processor._update_month_end_count(month_end_count, counts)
        
        assert month_end_count.total_devices == 10
        assert month_end_count.servers == 4
        assert month_end_count.workstations == 6
        assert month_end_count.spare_devices == 2
        assert month_end_count.billable_devices == 8
        assert month_end_count.ninja_devices == 6
        assert month_end_count.threatlocker_devices == 4


class TestDataProcessorIntegration:
    """Integration tests for data processing"""
    
    def test_full_processing_pipeline(self):
        """Test the complete data processing pipeline"""
        # This would require a real database connection
        # For now, we'll test the main function structure
        with patch('storage.rollups.get_db_session') as mock_session:
            mock_db = Mock(spec=Session)
            mock_session.return_value.__enter__.return_value = mock_db
            
            # Mock all the database operations properly
            mock_db.query.return_value.all.return_value = []
            mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = []
            mock_db.query.return_value.filter.return_value.first.return_value = None
            
            # Mock the retention policy queries specifically
            mock_db.query.return_value.filter.return_value.all.side_effect = [[], [], []]
            
            # Import and call the main function
            from storage.rollups import main
            main()
            
            # Verify database session was used
            mock_session.assert_called_once()

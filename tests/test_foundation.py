"""
Test foundation components
"""
import pytest
import os
from unittest.mock import patch

from common.config import config, DatabaseConfig, NinjaConfig, ThreatLockerConfig
from common.logging import setup_logging, get_logger


class TestConfig:
    """Test configuration management"""
    
    def test_database_config(self):
        """Test database configuration"""
        assert isinstance(config.database, DatabaseConfig)
        assert config.database.host == "localhost"
        assert config.database.port == 5432
        assert config.database.database == "es_inventory_db"
    
    def test_ninja_config(self):
        """Test NinjaRMM configuration"""
        assert isinstance(config.ninja, NinjaConfig)
        assert config.ninja.base_url == "https://app.ninjarmm.com"
        assert config.ninja.timeout == 30
    
    def test_threatlocker_config(self):
        """Test ThreatLocker configuration"""
        assert isinstance(config.threatlocker, ThreatLockerConfig)
        assert config.threatlocker.base_url == "https://portalapi.g.threatlocker.com"
        assert config.threatlocker.timeout == 30
    
    @patch.dict(os.environ, {
        'NINJA_CLIENT_ID': 'test_key',
        'NINJA_CLIENT_SECRET': 'test_secret',
        'THREATLOCKER_API_KEY': 'test_key',
        'THREATLOCKER_ORGANIZATION_ID': 'test_org',
        'DB_PASSWORD': 'test_password'
    })
    def test_config_validation(self):
        """Test configuration validation"""
        # Reload config with new environment variables
        from common.config import Config
        test_config = Config()
        # Should not raise an exception
        test_config.validate()
    
    def test_config_validation_missing_keys(self):
        """Test configuration validation with missing keys"""
        with pytest.raises(ValueError, match="NINJA_CLIENT_ID is required"):
            config.validate()


class TestLogging:
    """Test logging setup"""
    
    def test_logging_setup(self):
        """Test logging setup"""
        setup_logging()
        logger = get_logger("test")
        assert logger is not None
        
        # Test logging works
        logger.info("Test message")


class TestDatabaseModels:
    """Test database models"""
    
    def test_site_model(self):
        """Test Site model"""
        from storage.models import Site, SiteAlias
        
        site = Site(name="Test Site")
        
        # Create site aliases
        ninja_alias = SiteAlias(
            site=site,
            alias_name="Test Site",
            alias_type="ninja_site",
            external_id="ninja123"
        )
        
        threatlocker_alias = SiteAlias(
            site=site,
            alias_name="Test Site",
            alias_type="threatlocker_tenant",
            external_id="tl456"
        )
        
        assert site.name == "Test Site"
        assert ninja_alias.external_id == "ninja123"
        assert threatlocker_alias.external_id == "tl456"
    
    def test_device_model(self):
        """Test Device model"""
        from storage.models import Device, Site
        
        site = Site(name="Test Site")
        device = Device(
            site=site,
            hostname="test-device",
            display_name="Test Device",
            source_system="ninja",
            is_spare=False,
            is_server=True,
            is_billable=True
        )
        
        assert device.hostname == "test-device"
        assert device.display_name == "Test Device"
        assert device.source_system == "ninja"
        assert device.is_spare is False
        assert device.is_server is True
        assert device.is_billable is True

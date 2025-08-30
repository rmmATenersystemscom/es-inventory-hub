"""
Configuration management for es-inventory-hub
"""
import os
from typing import Optional
from dataclasses import dataclass


@dataclass
class DatabaseConfig:
    """Database configuration"""
    url: str
    host: str
    port: int
    database: str
    username: str
    password: str


@dataclass
class NinjaConfig:
    """NinjaRMM API configuration"""
    api_key: str
    base_url: str = "https://eu.ninjarmm.com"
    timeout: int = 30


@dataclass
class ThreatLockerConfig:
    """ThreatLocker API configuration"""
    api_key: str
    base_url: str = "https://api.threatlocker.com"
    timeout: int = 30


@dataclass
class AppConfig:
    """Application configuration"""
    debug: bool = False
    log_level: str = "INFO"
    timezone: str = "UTC"
    
    # Retention settings
    daily_retention_days: int = 65
    month_end_retention_years: int = 2
    
    # Dashboard settings
    dashboard_host: str = "0.0.0.0"
    dashboard_port: int = 5000


class Config:
    """Main configuration class"""
    
    def __init__(self):
        self.database = DatabaseConfig(
            url=os.getenv("DATABASE_URL", "postgresql://es_inventory_user:password@localhost/es_inventory_db"),
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            database=os.getenv("DB_NAME", "es_inventory_db"),
            username=os.getenv("DB_USER", "es_inventory_user"),
            password=os.getenv("DB_PASSWORD", "password"),
        )
        
        self.ninja = NinjaConfig(
            api_key=os.getenv("NINJA_CLIENT_ID", ""),
            base_url=os.getenv("NINJA_BASE_URL", "https://app.ninjarmm.com"),
            timeout=int(os.getenv("NINJA_TIMEOUT", "30")),
        )
        
        self.threatlocker = ThreatLockerConfig(
            api_key=os.getenv("THREATLOCKER_API_KEY", ""),
            base_url=os.getenv("THREATLOCKER_API_BASE_URL", "https://portalapi.g.threatlocker.com"),
            timeout=int(os.getenv("THREATLOCKER_TIMEOUT", "30")),
        )
        
        self.app = AppConfig(
            debug=os.getenv("DEBUG", "false").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            timezone=os.getenv("TIMEZONE", "UTC"),
            daily_retention_days=int(os.getenv("DAILY_RETENTION_DAYS", "65")),
            month_end_retention_years=int(os.getenv("MONTH_END_RETENTION_YEARS", "2")),
            dashboard_host=os.getenv("DASHBOARD_HOST", "0.0.0.0"),
            dashboard_port=int(os.getenv("DASHBOARD_PORT", "5000")),
        )
    
    def validate(self) -> None:
        """Validate required configuration"""
        if not self.ninja.api_key:
            raise ValueError("NINJA_CLIENT_ID is required")
        
        # Check for Ninja API secret
        if not os.getenv("NINJA_CLIENT_SECRET"):
            raise ValueError("NINJA_CLIENT_SECRET is required")
        
        if not self.threatlocker.api_key:
            raise ValueError("THREATLOCKER_API_KEY is required")
        
        # Check for ThreatLocker organization ID
        if not os.getenv("THREATLOCKER_ORGANIZATION_ID"):
            raise ValueError("THREATLOCKER_ORGANIZATION_ID is required")
        
        if not self.database.password:
            raise ValueError("DB_PASSWORD is required")


# Global config instance
config = Config()

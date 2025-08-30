#!/usr/bin/env python3
"""
ThreatLocker data collector for es-inventory-hub
"""
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

# Add the parent directory to the path
sys.path.append(str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
from sqlalchemy.orm import Session

from common.config import config
from common.db import get_db_session
from common.logging import setup_logging, get_logger
from storage.models import Site, SiteAlias, Device, DeviceSnapshot
from storage.rollups import DataProcessor

from .api import ThreatLockerAPI
from .mapper import ThreatLockerDeviceMapper

logger = get_logger(__name__)


class ThreatLockerCollector:
    """ThreatLocker data collector"""
    
    def __init__(self):
        self.client = ThreatLockerAPI()
        self.mapper = ThreatLockerDeviceMapper()
        self.snapshot_date = datetime.now(timezone.utc)
    
    def collect_sites(self, db: Session) -> Dict[str, Site]:
        """Collect and store sites (organizations) from ThreatLocker"""
        logger.info("Starting site collection")
        
        try:
            # Get sites from API
            sites_data = self.client.get_organizations()
            logger.info(f"Retrieved {len(sites_data)} organizations from ThreatLocker")
            
            # Map and store sites
            sites_map = {}
            for site_data in sites_data:
                site = self.mapper.map_site_data(site_data)
                threatlocker_tenant_id = str(site_data.get('id'))
                
                # Check if site alias already exists
                existing_alias = db.query(SiteAlias).filter(
                    SiteAlias.alias_type == 'threatlocker_tenant',
                    SiteAlias.external_id == threatlocker_tenant_id
                ).first()
                
                if existing_alias:
                    # Get existing site
                    existing_site = existing_alias.site
                    existing_site.name = site.name
                    existing_site.updated_at = datetime.now(timezone.utc)
                    sites_map[threatlocker_tenant_id] = existing_site
                    logger.debug(f"Updated existing site: {site.name}")
                else:
                    # Create new site and alias
                    db.add(site)
                    db.flush()  # Get the site ID
                    
                    site_alias = SiteAlias(
                        site=site,
                        alias_name=site.name,
                        alias_type='threatlocker_tenant',
                        external_id=threatlocker_tenant_id
                    )
                    db.add(site_alias)
                    sites_map[threatlocker_tenant_id] = site
                    logger.debug(f"Created new site: {site.name}")
            
            db.commit()
            logger.info(f"Successfully processed {len(sites_map)} sites")
            return sites_map
            
        except Exception as e:
            logger.error(f"Failed to collect sites: {e}")
            db.rollback()
            raise
    
    def collect_devices(self, db: Session, sites_map: Dict[str, Site]) -> List[Device]:
        """Collect and store devices from ThreatLocker"""
        logger.info("Starting device collection")
        
        try:
            devices_processed = []
            
            # Get devices for each site
            for site_id, site in sites_map.items():
                logger.info(f"Collecting devices for site: {site.name}")
                
                try:
                    devices_data = self.client.get_devices(site_id)
                    logger.info(f"Retrieved {len(devices_data)} devices for site {site.name}")
                    
                    for device_data in devices_data:
                        try:
                            # Map device data
                            device = self.mapper.map_to_device(device_data, site)
                            
                            # Check if device already exists
                            existing_device = db.query(Device).filter(
                                Device.threatlocker_device_id == device.threatlocker_device_id
                            ).first()
                            
                            if existing_device:
                                # Update existing device
                                existing_device.hostname = device.hostname
                                existing_device.display_name = device.display_name
                                existing_device.location = device.location
                                existing_device.node_class = device.node_class
                                existing_device.is_spare = device.is_spare
                                existing_device.is_server = device.is_server
                                existing_device.is_billable = device.is_billable
                                existing_device.updated_at = datetime.now(timezone.utc)
                                devices_processed.append(existing_device)
                                logger.debug(f"Updated existing device: {device.hostname}")
                            else:
                                # Create new device
                                db.add(device)
                                devices_processed.append(device)
                                logger.debug(f"Created new device: {device.hostname}")
                            
                        except Exception as e:
                            logger.error(f"Failed to process device {device_data.get('id')}: {e}")
                            continue
                    
                except Exception as e:
                    logger.error(f"Failed to collect devices for site {site.name}: {e}")
                    continue
            
            db.commit()
            logger.info(f"Successfully processed {len(devices_processed)} devices")
            return devices_processed
            
        except Exception as e:
            logger.error(f"Failed to collect devices: {e}")
            db.rollback()
            raise
    
    def create_snapshots(self, db: Session, devices: List[Device]) -> List[DeviceSnapshot]:
        """Create snapshots for all devices"""
        logger.info("Creating device snapshots")
        
        try:
            snapshots_created = []
            
            for device in devices:
                try:
                    # Get detailed device data for snapshot
                    device_data = self.client.get_device_details(device.threatlocker_device_id)
                    
                    # Check if snapshot already exists for today
                    existing_snapshot = db.query(DeviceSnapshot).filter(
                        DeviceSnapshot.device_id == device.id,
                        DeviceSnapshot.snapshot_date >= self.snapshot_date.replace(hour=0, minute=0, second=0, microsecond=0),
                        DeviceSnapshot.source_system == 'threatlocker'
                    ).first()
                    
                    if existing_snapshot:
                        logger.debug(f"Snapshot already exists for device {device.hostname} today")
                        continue
                    
                    # Create new snapshot
                    snapshot = self.mapper.map_to_snapshot(device_data, device, self.snapshot_date)
                    db.add(snapshot)
                    snapshots_created.append(snapshot)
                    logger.debug(f"Created snapshot for device: {device.hostname}")
                    
                except Exception as e:
                    logger.error(f"Failed to create snapshot for device {device.hostname}: {e}")
                    continue
            
            db.commit()
            logger.info(f"Successfully created {len(snapshots_created)} snapshots")
            return snapshots_created
            
        except Exception as e:
            logger.error(f"Failed to create snapshots: {e}")
            db.rollback()
            raise
    
    def run(self) -> None:
        """Run the complete collection process"""
        logger.info("Starting ThreatLocker data collection")
        
        try:
            # Test connection
            if not self.client.test_connection():
                logger.error("Failed to connect to ThreatLocker API")
                sys.exit(1)
            
            logger.info("Successfully connected to ThreatLocker API")
            
            with get_db_session() as db:
                # Collect sites
                sites_map = self.collect_sites(db)
                
                # Collect devices
                devices = self.collect_devices(db, sites_map)
                
                # Create snapshots
                snapshots = self.create_snapshots(db, devices)
                
                # Generate daily rollups and process data
                processor = DataProcessor()
                daily_stats = processor.generate_daily_rollups(db)
                month_end_stats = processor.generate_month_end_snapshots(db)
                retention_stats = processor.enforce_retention_policy(db)
                
                logger.info(f"Collection completed successfully", extra={
                    'sites_processed': len(sites_map),
                    'devices_processed': len(devices),
                    'snapshots_created': len(snapshots),
                    'snapshot_date': self.snapshot_date.isoformat(),
                    'daily_rollups': daily_stats,
                    'month_end_snapshots': month_end_stats,
                    'retention_cleanup': retention_stats
                })
                
        except Exception as e:
            logger.error(f"Collection failed: {e}")
            sys.exit(1)


def main():
    """Main entry point"""
    # Load environment variables
    load_dotenv()
    
    # Setup logging
    setup_logging()
    
    # Validate configuration
    try:
        config.validate()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    
    # Run collector
    collector = ThreatLockerCollector()
    collector.run()


if __name__ == "__main__":
    main()

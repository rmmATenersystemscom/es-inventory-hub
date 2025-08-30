#!/usr/bin/env python3
"""
ThreatLocker Collector Main Entry Point
"""

import sys
import os
import argparse
from datetime import datetime, timezone
from sqlalchemy.orm import Session

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from common.config import Config
from common.logging import get_logger
from storage.database import get_db_session
from collectors.threatlocker.collector import ThreatLockerCollector
from collectors.threatlocker.api import ThreatLockerAPI

logger = get_logger(__name__)


def main():
    """Main entry point for ThreatLocker collector"""
    parser = argparse.ArgumentParser(description='ThreatLocker Collector')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Fetch up to 1 device and log normalized record without DB writes')
    args = parser.parse_args()
    
    try:
        # Load configuration
        config = Config()
        config.validate()
        
        logger.info("Starting ThreatLocker collector")
        
        # Test API connection first
        api = ThreatLockerAPI()
        if not api.test_connection():
            logger.error("Failed to connect to ThreatLocker API")
            sys.exit(1)
        
        if args.dry_run:
            # Dry run mode: fetch up to 1 device and log normalized record
            logger.info("DRY RUN MODE: Fetching up to 1 device for testing...")
            try:
                devices = api.get_all_computers_with_child_organizations()
                if devices:
                    device = devices[0]
                    logger.info("DRY RUN - Sample device normalized record:")
                    logger.info(f"  ID: {device.get('id')}")
                    logger.info(f"  Computer Name: {device.get('computerName')}")
                    logger.info(f"  Display Name: {device.get('displayName')}")
                    logger.info(f"  Operating System: {device.get('operatingSystem')}")
                    logger.info(f"  OS Version: {device.get('osVersion')}")
                    logger.info(f"  Status: {device.get('status')}")
                    logger.info(f"  Organization ID: {device.get('organizationId')}")
                    logger.info(f"  Location: {device.get('location')}")
                    logger.info(f"  Last Check In: {device.get('lastCheckIn')}")
                    logger.info(f"  IP Address: {device.get('ipAddress')}")
                    logger.info(f"  MAC Address: {device.get('macAddress')}")
                    logger.info("DRY RUN COMPLETE - No database writes performed")
                else:
                    logger.warning("DRY RUN: No devices found")
            except Exception as e:
                logger.error(f"DRY RUN failed: {e}")
            return
        
        # Quick self-check: list 1 device to confirm parity
        logger.info("Performing self-check: listing 1 device...")
        try:
            devices = api.get_all_computers_with_child_organizations()
            if devices:
                device = devices[0]
                logger.info(f"Self-check successful - Sample device: {device.get('computerName', 'Unknown')} "
                          f"({device.get('operatingSystem', 'Unknown')}) - {device.get('status', 'Unknown')}")
            else:
                logger.warning("Self-check: No devices found")
        except Exception as e:
            logger.error(f"Self-check failed: {e}")
        
        # Initialize collector
        collector = ThreatLockerCollector()
        
        # Get database session
        db: Session = next(get_db_session())
        
        try:
            # Run the collector
            collector.run()
            logger.info("ThreatLocker collection completed successfully")
            
        except Exception as e:
            logger.error(f"Collection failed: {e}")
            raise
            
    except Exception as e:
        logger.error(f"ThreatLocker collector failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

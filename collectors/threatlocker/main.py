#!/usr/bin/env python3
"""
ThreatLocker Collector Main Entry Point
"""

import sys
import os
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

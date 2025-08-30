#!/usr/bin/env python3
"""
NinjaRMM Collector Main Entry Point
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
from collectors.ninja.collector import NinjaCollector
from collectors.ninja.api import NinjaRMMAPI

logger = get_logger(__name__)


def main():
    """Main entry point for NinjaRMM collector"""
    try:
        # Load configuration
        config = Config()
        config.validate()
        
        logger.info("Starting NinjaRMM collector")
        
        # Test API connection first
        api = NinjaRMMAPI()
        if not api.test_connection():
            logger.error("Failed to connect to NinjaRMM API")
            sys.exit(1)
        
        # Quick self-check: list 1 device to confirm parity
        logger.info("Performing self-check: listing 1 device...")
        try:
            organizations = api.get_organizations()
            if organizations:
                org_id = organizations[0]['id']
                devices = api.get_devices(org_id)
                if devices:
                    device = devices[0]
                    logger.info(f"Self-check successful - Sample device: {device.get('systemName', 'Unknown')} "
                              f"({device.get('deviceType', 'Unknown')}) - {device.get('status', 'Unknown')}")
                else:
                    logger.warning("Self-check: No devices found in first organization")
            else:
                logger.warning("Self-check: No organizations found")
        except Exception as e:
            logger.error(f"Self-check failed: {e}")
        
        # Initialize collector
        collector = NinjaCollector()
        
        # Get database session
        db: Session = next(get_db_session())
        
        try:
            # Run the collector
            collector.run()
            logger.info("NinjaRMM collection completed successfully")
            
        except Exception as e:
            logger.error(f"Collection failed: {e}")
            raise
            
    except Exception as e:
        logger.error(f"NinjaRMM collector failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

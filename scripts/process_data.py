#!/usr/bin/env python3
"""
Standalone data processing script for es-inventory-hub
"""
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add the parent directory to the path
sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from common.config import config
from common.logging import setup_logging, get_logger
from storage.rollups import DataProcessor

logger = get_logger(__name__)


def main():
    """Main entry point for standalone data processing"""
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
    
    logger.info("Starting standalone data processing")
    
    try:
        processor = DataProcessor()
        processor.main()
        logger.info("Data processing completed successfully")
        
    except Exception as e:
        logger.error(f"Data processing failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

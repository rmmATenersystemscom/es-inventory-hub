#!/usr/bin/env python3
"""
Database initialization script for es-inventory-hub
"""
import os
import sys
from pathlib import Path

# Add the parent directory to the path
sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from common.config import config
from common.db import init_db, check_db_connection
from common.logging import setup_logging, get_logger

def main():
    """Initialize the database"""
    # Load environment variables
    load_dotenv()
    
    # Setup logging
    setup_logging()
    logger = get_logger(__name__)
    
    try:
        # Validate configuration
        config.validate()
        logger.info("Configuration validated successfully")
        
        # Check database connection
        if not check_db_connection():
            logger.error("Database connection failed")
            sys.exit(1)
        
        logger.info("Database connection successful")
        
        # Initialize database tables
        init_db()
        logger.info("Database tables created successfully")
        
        print("✅ Database initialized successfully!")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        print(f"❌ Database initialization failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

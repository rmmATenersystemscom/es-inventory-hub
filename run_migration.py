#!/usr/bin/env python3
"""
Script to run the database migration for ES Inventory Hub.
This script will prompt for the postgres password and run the migration.
"""

import os
import getpass
import sys
from alembic.config import Config
from alembic import command

def main():
    print("ES Inventory Hub - Database Migration")
    print("=" * 40)
    
    # Get password from user
    password = getpass.getpass('Enter postgres password: ')
    
    # Set up database connection string
    dsn = f'postgresql://postgres:{password}@localhost:5432/es_inventory_hub'
    os.environ['DB_DSN'] = dsn
    
    print(f"Connecting to database: postgresql://postgres:***@localhost:5432/es_inventory_hub")
    
    try:
        # Load Alembic configuration
        config = Config('alembic.ini')
        
        # Check current version
        print("\nChecking current migration version...")
        from alembic.runtime.migration import MigrationContext
        from sqlalchemy import create_engine
        
        engine = create_engine(dsn)
        with engine.connect() as connection:
            context = MigrationContext.configure(connection)
            current_version = context.get_current_revision()
            print(f"Current version: {current_version}")
        
        # Run migration
        print("\nRunning migration to add Ninja modal fields...")
        command.upgrade(config, 'head')
        
        print("\n✅ Migration completed successfully!")
        print("The database schema has been updated with all 42 Ninja modal fields.")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

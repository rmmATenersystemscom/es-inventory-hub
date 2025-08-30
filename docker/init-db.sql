-- Database initialization script for ES Inventory Hub
-- This script runs when the PostgreSQL container starts

-- Create database and user (if they don't exist)
DO $$
BEGIN
    -- Create user if it doesn't exist
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'es_inventory_user') THEN
        CREATE USER es_inventory_user WITH PASSWORD 'es_inventory_password';
    END IF;
    
    -- Create database if it doesn't exist
    IF NOT EXISTS (SELECT FROM pg_database WHERE datname = 'es_inventory_db') THEN
        CREATE DATABASE es_inventory_db OWNER es_inventory_user;
    END IF;
END
$$;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE es_inventory_db TO es_inventory_user;
GRANT ALL ON SCHEMA public TO es_inventory_user;

-- Set default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO es_inventory_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO es_inventory_user;

-- Migration: Add Variance Tracking to Exceptions Table
-- Purpose: Enable tracking of manual fixes and variance status management
-- Date: 2025-09-23
-- Author: Database AI

-- Add variance tracking columns to exceptions table
ALTER TABLE exceptions 
ADD COLUMN IF NOT EXISTS manually_updated_at TIMESTAMP NULL,
ADD COLUMN IF NOT EXISTS manually_updated_by VARCHAR(255) NULL,
ADD COLUMN IF NOT EXISTS update_type VARCHAR(100) NULL,
ADD COLUMN IF NOT EXISTS old_value JSONB NULL,
ADD COLUMN IF NOT EXISTS new_value JSONB NULL,
ADD COLUMN IF NOT EXISTS variance_status VARCHAR(50) DEFAULT 'active';

-- Add check constraint for variance_status
ALTER TABLE exceptions 
ADD CONSTRAINT chk_variance_status 
CHECK (variance_status IN ('active', 'manually_fixed', 'collector_verified', 'stale'));

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_exceptions_variance_status ON exceptions(variance_status);
CREATE INDEX IF NOT EXISTS idx_exceptions_manually_updated ON exceptions(manually_updated_at);
CREATE INDEX IF NOT EXISTS idx_exceptions_updated_by ON exceptions(manually_updated_by);
CREATE INDEX IF NOT EXISTS idx_exceptions_status_date_type ON exceptions(variance_status, date_found, type);
CREATE INDEX IF NOT EXISTS idx_exceptions_hostname_status ON exceptions(hostname, variance_status);

-- Create partial index for active exceptions only (performance optimization)
CREATE INDEX IF NOT EXISTS idx_exceptions_active ON exceptions(date_found, type) 
WHERE variance_status = 'active';

-- Add comments for documentation
COMMENT ON COLUMN exceptions.manually_updated_at IS 'Timestamp when exception was manually fixed by dashboard user';
COMMENT ON COLUMN exceptions.manually_updated_by IS 'Username of person who manually fixed the exception';
COMMENT ON COLUMN exceptions.update_type IS 'Type of update performed (display_name, hostname, organization, etc.)';
COMMENT ON COLUMN exceptions.old_value IS 'JSON object containing old values before manual fix';
COMMENT ON COLUMN exceptions.new_value IS 'JSON object containing new values after manual fix';
COMMENT ON COLUMN exceptions.variance_status IS 'Current status of variance: active, manually_fixed, collector_verified, stale';

-- Update existing resolved exceptions to have proper variance_status
UPDATE exceptions 
SET variance_status = 'collector_verified' 
WHERE resolved = true AND variance_status = 'active';

-- Verify the migration
SELECT 
    column_name, 
    data_type, 
    is_nullable, 
    column_default
FROM information_schema.columns 
WHERE table_name = 'exceptions' 
AND column_name IN ('manually_updated_at', 'manually_updated_by', 'update_type', 'old_value', 'new_value', 'variance_status')
ORDER BY column_name;

-- Show index information
SELECT 
    indexname, 
    indexdef 
FROM pg_indexes 
WHERE tablename = 'exceptions' 
AND indexname LIKE 'idx_exceptions_%'
ORDER BY indexname;

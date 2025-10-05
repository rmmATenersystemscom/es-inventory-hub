-- Add Windows 11 24H2 capability fields to device_snapshot table
-- Migration: Add Windows 11 24H2 Assessment Fields

BEGIN;

-- Add new columns to device_snapshot table
ALTER TABLE device_snapshot 
ADD COLUMN windows_11_24h2_capable BOOLEAN DEFAULT NULL,
ADD COLUMN windows_11_24h2_deficiencies JSONB DEFAULT '{}';

-- Add index for performance
CREATE INDEX idx_device_snapshot_windows_11_24h2_capable 
ON device_snapshot(windows_11_24h2_capable) 
WHERE windows_11_24h2_capable IS NOT NULL;

-- Add index for JSONB queries
CREATE INDEX idx_device_snapshot_windows_11_24h2_deficiencies 
ON device_snapshot USING GIN (windows_11_24h2_deficiencies);

COMMIT;

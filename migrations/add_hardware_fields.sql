-- Add hardware fields to device_snapshot table for Windows 11 24H2 assessment
-- These fields are needed for CPU, memory, storage, and OS architecture assessment

BEGIN;

-- OS Information
ALTER TABLE device_snapshot ADD COLUMN IF NOT EXISTS os_architecture VARCHAR(100);
ALTER TABLE device_snapshot ADD COLUMN IF NOT EXISTS os_build VARCHAR(100);
ALTER TABLE device_snapshot ADD COLUMN IF NOT EXISTS os_release_id VARCHAR(100);

-- Hardware Information
ALTER TABLE device_snapshot ADD COLUMN IF NOT EXISTS cpu_model VARCHAR(255);
ALTER TABLE device_snapshot ADD COLUMN IF NOT EXISTS cpu_cores INTEGER;
ALTER TABLE device_snapshot ADD COLUMN IF NOT EXISTS cpu_threads INTEGER;
ALTER TABLE device_snapshot ADD COLUMN IF NOT EXISTS cpu_speed_mhz INTEGER;
ALTER TABLE device_snapshot ADD COLUMN IF NOT EXISTS memory_gib NUMERIC(10, 2);
ALTER TABLE device_snapshot ADD COLUMN IF NOT EXISTS memory_bytes BIGINT;
ALTER TABLE device_snapshot ADD COLUMN IF NOT EXISTS volumes TEXT;

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_device_snapshot_cpu_model ON device_snapshot(cpu_model);
CREATE INDEX IF NOT EXISTS idx_device_snapshot_memory_gib ON device_snapshot(memory_gib);
CREATE INDEX IF NOT EXISTS idx_device_snapshot_os_architecture ON device_snapshot(os_architecture);

COMMIT;

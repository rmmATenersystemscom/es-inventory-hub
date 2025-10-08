# Database Schema Guide

**Complete database reference for ES Inventory Hub schema, tables, and queries.**

**Last Updated**: October 8, 2025  
**ES Inventory Hub Version**: v1.19.2  
**Status**: ✅ **FULLY OPERATIONAL**

---

## 🗄️ **DATABASE OVERVIEW**

### **Connection Details**
```
Host: your_database_host_here
Port: 5432
Database: your_database_name_here
Username: your_database_username_here
Password: your_database_password_here
```

### **⚠️ IMPORTANT FOR DASHBOARD AI**
- **Your Server**: your_dashboard_server_ip_here (Dashboard AI)
- **Database AI Server**: your_database_server_ip_here (API Server)
- **YOU MUST use**: `https://your-api-domain.com:5400` (HTTPS API server)
- **YOU MUST NOT use**: Port 5432 (direct database access)
- **HTTPS Required**: Mixed content security requires HTTPS for dashboard integration

---

## 🔄 **DAILY DATA COLLECTION BEHAVIOR**

### **Multiple Runs Per Day Support**

The ES Inventory Hub collectors are designed to handle **multiple runs per day** while maintaining **one dataset per day**. This ensures data accuracy and prevents duplicates.

#### **Daily Data Update Logic**

**For each day, the system follows this pattern:**

1. **Delete Existing Data**: Before collecting new data, all existing snapshots for the current day are deleted
2. **Insert Fresh Data**: New snapshots are inserted representing the current state
3. **Result**: Each day has exactly one set of data representing the end-of-day state

#### **Example Scenario**

**October 7th, 2025 - Multiple Ninja Collector Runs:**

- **Run 1 (9 AM)**: Deletes existing Oct 7th snapshots → Inserts 717 new snapshots
- **Run 2 (2 PM)**: Deletes existing Oct 7th snapshots → Inserts 720 new snapshots (3 new devices)
- **Run 3 (6 PM)**: Deletes existing Oct 7th snapshots → Inserts 715 new snapshots (5 devices deleted)

**Final Result**: Only 715 snapshots exist for October 7th (representing the final state)

#### **Device Deletion Handling**

- **Current Day**: Deleted devices are removed from the current day's data
- **Historical Days**: Previous days' data remains completely untouched
- **Data Integrity**: Each day represents the actual state at the end of that day

#### **Benefits of This Approach**

- ✅ **No Duplicates**: Each device has exactly one snapshot per day
- ✅ **Current Accuracy**: Data reflects the actual end-of-day state
- ✅ **Historical Preservation**: Previous days' data is never modified
- ✅ **Clean Database**: No "ghost" devices from deleted systems
- ✅ **Multiple Runs Safe**: Can run collectors as many times as needed per day

---

## 📊 **PRIMARY TABLES FOR DASHBOARD**

### **`exceptions` Table (Enhanced)**
```sql
CREATE TABLE exceptions (
    id BIGSERIAL PRIMARY KEY,
    date_found DATE NOT NULL DEFAULT CURRENT_DATE,
    type VARCHAR(64) NOT NULL,  -- MISSING_NINJA, DUPLICATE_TL, SITE_MISMATCH, SPARE_MISMATCH, DISPLAY_NAME_MISMATCH
    hostname VARCHAR(255) NOT NULL,
    details JSONB NOT NULL DEFAULT '{}',
    resolved BOOLEAN NOT NULL DEFAULT FALSE,
    resolved_date DATE,
    resolved_by VARCHAR(255),
    
    -- NEW: Enhanced variance tracking
    manually_updated_at TIMESTAMP WITH TIME ZONE,
    manually_updated_by VARCHAR(255),
    update_type VARCHAR(100),
    old_value JSONB,
    new_value JSONB,
    variance_status VARCHAR(50) DEFAULT 'active'
);
```

**Key Fields:**
- `type`: Exception type (MISSING_NINJA, DUPLICATE_TL, etc.)
- `hostname`: Device hostname
- `details`: JSONB field containing device information and organization data
- `resolved`: Whether the exception has been resolved
- `variance_status`: Current status of the variance (active, resolved, etc.)

### **`device_snapshot` Table**
```sql
CREATE TABLE device_snapshot (
    id BIGSERIAL PRIMARY KEY,
    snapshot_date DATE NOT NULL,
    vendor_id INTEGER NOT NULL REFERENCES vendor(id),
    device_identity_id BIGINT NOT NULL REFERENCES device_identity(id),
    hostname VARCHAR(255),
    organization_name VARCHAR(255),
    display_name VARCHAR(255),
    device_status VARCHAR(100),
    os_name VARCHAR(255),
    os_version VARCHAR(255),
    last_boot TIMESTAMP WITH TIME ZONE,
    last_contact TIMESTAMP WITH TIME ZONE,
    is_online BOOLEAN DEFAULT FALSE,
    is_server BOOLEAN DEFAULT FALSE,
    device_type_id INTEGER REFERENCES device_type(id),
    billing_status VARCHAR(100),
    
    -- TPM Information
    has_tpm BOOLEAN DEFAULT NULL,
    tpm_enabled BOOLEAN DEFAULT NULL,
    tpm_version VARCHAR(50) DEFAULT NULL,
    
    -- Secure Boot Information
    secure_boot_available BOOLEAN DEFAULT NULL,
    secure_boot_enabled BOOLEAN DEFAULT NULL,
    
    -- Hardware Information (Ninja-specific)
    os_architecture VARCHAR(100) DEFAULT NULL,
    cpu_model VARCHAR(255) DEFAULT NULL,
    system_manufacturer VARCHAR(255) DEFAULT NULL,
    system_model VARCHAR(255) DEFAULT NULL,
    memory_gib NUMERIC(10, 2) DEFAULT NULL,
    volumes TEXT DEFAULT NULL,
    
    -- Windows 11 24H2 Assessment Fields
    windows_11_24h2_capable BOOLEAN DEFAULT NULL,
    windows_11_24h2_deficiencies JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

**Key Fields:**
- `snapshot_date`: Date of the snapshot
- `vendor_id`: Reference to vendor table (Ninja, ThreatLocker)
- `hostname`: Device hostname
- `organization_name`: Organization name
- `display_name`: Display name
- `os_name`: Operating system name
- `os_version`: Operating system version
- `is_online`: Whether device is online
- `is_server`: Whether device is a server
- `device_type_id`: Reference to device type table
- `billing_status`: Billing status
- `windows_11_24h2_capable`: Windows 11 24H2 compatibility
- `windows_11_24h2_deficiencies`: Detailed deficiency information

### **`vendor` Table**
```sql
CREATE TABLE vendor (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    api_endpoint VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

**Values:**
- `Ninja`: NinjaRMM vendor
- `ThreatLocker`: ThreatLocker vendor

### **`device_type` Table**
```sql
CREATE TABLE device_type (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    code VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

**Values:**
- `Desktop`: Desktop computers
- `Laptop`: Laptop computers
- `workstation`: Workstation computers
- `Server`: Server computers

### **`device_identity` Table**
```sql
CREATE TABLE device_identity (
    id BIGSERIAL PRIMARY KEY,
    canonical_key VARCHAR(255) NOT NULL UNIQUE,
    hostname VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

**Purpose**: Links devices across vendors using canonical keys

---

## 🔍 **ESSENTIAL DATABASE QUERIES**

### **Get Latest Variance Report**
```sql
SELECT * FROM exceptions 
WHERE date_found = (
    SELECT MAX(date_found) FROM exceptions
) 
ORDER BY type, hostname;
```

### **Get Exception Counts by Type**
```sql
SELECT type, COUNT(*) as count 
FROM exceptions 
WHERE resolved = FALSE 
GROUP BY type;
```

### **Get Device Counts by Vendor**
```sql
SELECT v.name as vendor, COUNT(*) as count
FROM device_snapshot ds
JOIN vendor v ON ds.vendor_id = v.id
WHERE ds.snapshot_date = CURRENT_DATE
GROUP BY v.name;
```

### **Get Variance Status Summary**
```sql
SELECT 
    COALESCE(variance_status, 'active') as status,
    type,
    COUNT(*) as count,
    COUNT(CASE WHEN resolved = true THEN 1 END) as resolved_count
FROM exceptions
WHERE date_found >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY variance_status, type
ORDER BY status, type;
```

### **Get Windows 11 24H2 Compatibility Status**
```sql
SELECT
    COUNT(*) as total_windows_devices,
    COUNT(CASE WHEN windows_11_24h2_capable = true THEN 1 END) as compatible_devices,
    COUNT(CASE WHEN windows_11_24h2_capable = false THEN 1 END) as incompatible_devices,
    COUNT(CASE WHEN windows_11_24h2_capable IS NULL THEN 1 END) as not_assessed_devices
FROM device_snapshot ds
JOIN vendor v ON ds.vendor_id = v.id
WHERE v.name = 'Ninja'
AND ds.snapshot_date = CURRENT_DATE
AND ds.os_name ILIKE '%windows%'
AND (ds.device_type_id IN (SELECT id FROM device_type WHERE name IN ('Desktop', 'Laptop', 'workstation')));
```

### **Get Incompatible Windows 11 24H2 Devices**
```sql
SELECT
    ds.hostname,
    ds.display_name,
    ds.organization_name,
    ds.os_name,
    ds.windows_11_24h2_deficiencies
FROM device_snapshot ds
JOIN vendor v ON ds.vendor_id = v.id
WHERE v.name = 'Ninja'
AND ds.snapshot_date = CURRENT_DATE
AND ds.windows_11_24h2_capable = false
AND (ds.device_type_id IN (SELECT id FROM device_type WHERE name IN ('Desktop', 'Laptop', 'workstation')))
ORDER BY ds.organization_name, ds.hostname;
```

### **Get Compatible Windows 11 24H2 Devices**
```sql
SELECT
    ds.hostname,
    ds.display_name,
    ds.organization_name,
    ds.os_name,
    ds.cpu_model,
    ds.system_manufacturer,
    ds.system_model,
    ds.memory_gib,
    ds.volumes
FROM device_snapshot ds
JOIN vendor v ON ds.vendor_id = v.id
WHERE v.name = 'Ninja'
AND ds.snapshot_date = CURRENT_DATE
AND ds.windows_11_24h2_capable = true
AND (ds.device_type_id IN (SELECT id FROM device_type WHERE name IN ('Desktop', 'Laptop', 'workstation')))
ORDER BY ds.organization_name, ds.hostname;
```

---

## 📈 **PERFORMANCE INDEXES**

### **Primary Indexes**
```sql
-- Device snapshot indexes
CREATE INDEX idx_device_snapshot_date ON device_snapshot(snapshot_date);
CREATE INDEX idx_device_snapshot_vendor ON device_snapshot(vendor_id);
CREATE INDEX idx_device_snapshot_hostname ON device_snapshot(hostname);
CREATE INDEX idx_device_snapshot_organization ON device_snapshot(organization_name);
CREATE INDEX idx_device_snapshot_os_name ON device_snapshot(os_name);
CREATE INDEX idx_device_snapshot_device_type ON device_snapshot(device_type_id);

-- Hardware Information indexes
CREATE INDEX idx_device_snapshot_os_architecture ON device_snapshot(os_architecture);
CREATE INDEX idx_device_snapshot_cpu_model ON device_snapshot(cpu_model);
CREATE INDEX idx_device_snapshot_system_manufacturer ON device_snapshot(system_manufacturer);
CREATE INDEX idx_device_snapshot_system_model ON device_snapshot(system_model);
CREATE INDEX idx_device_snapshot_memory_gib ON device_snapshot(memory_gib);

-- Windows 11 24H2 Assessment indexes
CREATE INDEX idx_device_snapshot_windows_11_24h2_capable
ON device_snapshot(windows_11_24h2_capable)
WHERE windows_11_24h2_capable IS NOT NULL;

CREATE INDEX idx_device_snapshot_windows_11_24h2_deficiencies
ON device_snapshot USING GIN (windows_11_24h2_deficiencies);

-- Exceptions indexes
CREATE INDEX idx_exceptions_date_found ON exceptions(date_found);
CREATE INDEX idx_exceptions_type ON exceptions(type);
CREATE INDEX idx_exceptions_hostname ON exceptions(hostname);
CREATE INDEX idx_exceptions_resolved ON exceptions(resolved);
CREATE INDEX idx_exceptions_variance_status ON exceptions(variance_status);
```

### **Composite Indexes**
```sql
-- Device snapshot composite indexes
CREATE INDEX idx_device_snapshot_date_vendor ON device_snapshot(snapshot_date, vendor_id);
CREATE INDEX idx_device_snapshot_date_os ON device_snapshot(snapshot_date, os_name);
CREATE INDEX idx_device_snapshot_date_device_type ON device_snapshot(snapshot_date, device_type_id);

-- Exceptions composite indexes
CREATE INDEX idx_exceptions_date_type ON exceptions(date_found, type);
CREATE INDEX idx_exceptions_date_resolved ON exceptions(date_found, resolved);
CREATE INDEX idx_exceptions_type_resolved ON exceptions(type, resolved);
```

---

## 🔧 **SCHEMA MIGRATIONS**

### **Windows 11 24H2 Assessment Fields**
```sql
-- Add Windows 11 24H2 capability fields to device_snapshot table
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
```

### **Hardware Fields**
```sql
-- Add missing hardware fields to device_snapshot table
BEGIN;

ALTER TABLE device_snapshot ADD COLUMN os_architecture VARCHAR(100) DEFAULT NULL;
ALTER TABLE device_snapshot ADD COLUMN cpu_model VARCHAR(255) DEFAULT NULL;
ALTER TABLE device_snapshot ADD COLUMN system_manufacturer VARCHAR(255) DEFAULT NULL;
ALTER TABLE device_snapshot ADD COLUMN system_model VARCHAR(255) DEFAULT NULL;
ALTER TABLE device_snapshot ADD COLUMN memory_gib NUMERIC(10, 2) DEFAULT NULL;
ALTER TABLE device_snapshot ADD COLUMN volumes TEXT DEFAULT NULL;

-- Add indexes for performance
CREATE INDEX idx_device_snapshot_os_architecture ON device_snapshot(os_architecture);
CREATE INDEX idx_device_snapshot_cpu_model ON device_snapshot(cpu_model);
CREATE INDEX idx_device_snapshot_memory_gib ON device_snapshot(memory_gib);

COMMIT;
```

---

## 📊 **DATA ANALYSIS QUERIES**

### **Device Distribution by Vendor**
```sql
SELECT 
    v.name as vendor,
    COUNT(*) as total_devices,
    COUNT(CASE WHEN ds.is_online = true THEN 1 END) as online_devices,
    COUNT(CASE WHEN ds.is_server = true THEN 1 END) as servers
FROM device_snapshot ds
JOIN vendor v ON ds.vendor_id = v.id
WHERE ds.snapshot_date = CURRENT_DATE
GROUP BY v.name
ORDER BY total_devices DESC;
```

### **Operating System Distribution**
```sql
SELECT 
    ds.os_name,
    COUNT(*) as device_count,
    COUNT(CASE WHEN ds.is_online = true THEN 1 END) as online_count
FROM device_snapshot ds
WHERE ds.snapshot_date = CURRENT_DATE
GROUP BY ds.os_name
ORDER BY device_count DESC;
```

### **Organization Device Counts**
```sql
SELECT 
    ds.organization_name,
    COUNT(*) as total_devices,
    COUNT(CASE WHEN ds.is_online = true THEN 1 END) as online_devices,
    COUNT(CASE WHEN ds.is_server = true THEN 1 END) as servers
FROM device_snapshot ds
WHERE ds.snapshot_date = CURRENT_DATE
GROUP BY ds.organization_name
ORDER BY total_devices DESC
LIMIT 20;
```

### **Windows 11 24H2 Compatibility by Organization**
```sql
SELECT 
    ds.organization_name,
    COUNT(*) as total_windows_devices,
    COUNT(CASE WHEN ds.windows_11_24h2_capable = true THEN 1 END) as compatible_devices,
    COUNT(CASE WHEN ds.windows_11_24h2_capable = false THEN 1 END) as incompatible_devices,
    ROUND(
        COUNT(CASE WHEN ds.windows_11_24h2_capable = true THEN 1 END) * 100.0 / COUNT(*), 
        2
    ) as compatibility_rate
FROM device_snapshot ds
JOIN vendor v ON ds.vendor_id = v.id
WHERE v.name = 'Ninja'
AND ds.snapshot_date = CURRENT_DATE
AND ds.os_name ILIKE '%windows%'
AND (ds.device_type_id IN (SELECT id FROM device_type WHERE name IN ('Desktop', 'Laptop', 'workstation')))
GROUP BY ds.organization_name
HAVING COUNT(*) >= 5  -- Only organizations with 5+ devices
ORDER BY compatibility_rate DESC;
```

### **Exception Trends Over Time**
```sql
SELECT 
    date_found,
    type,
    COUNT(*) as exception_count,
    COUNT(CASE WHEN resolved = true THEN 1 END) as resolved_count
FROM exceptions
WHERE date_found >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY date_found, type
ORDER BY date_found DESC, type;
```

---

## 🔍 **DEBUGGING QUERIES**

### **Check Data Freshness**
```sql
SELECT 
    MAX(snapshot_date) as latest_snapshot,
    COUNT(*) as total_snapshots,
    COUNT(CASE WHEN snapshot_date = CURRENT_DATE THEN 1 END) as today_snapshots
FROM device_snapshot;
```

### **Check Windows 11 24H2 Assessment Status**
```sql
SELECT 
    COUNT(*) as total_windows_devices,
    COUNT(CASE WHEN windows_11_24h2_capable IS NOT NULL THEN 1 END) as assessed_devices,
    COUNT(CASE WHEN windows_11_24h2_capable = true THEN 1 END) as compatible_devices,
    COUNT(CASE WHEN windows_11_24h2_capable = false THEN 1 END) as incompatible_devices,
    COUNT(CASE WHEN windows_11_24h2_capable IS NULL THEN 1 END) as not_assessed_devices
FROM device_snapshot ds
JOIN vendor v ON ds.vendor_id = v.id
WHERE v.name = 'Ninja'
AND ds.snapshot_date = CURRENT_DATE
AND ds.os_name ILIKE '%windows%';
```

### **Check Hardware Data Availability**
```sql
SELECT 
    COUNT(*) as total_devices,
    COUNT(CASE WHEN cpu_model IS NOT NULL THEN 1 END) as devices_with_cpu,
    COUNT(CASE WHEN system_manufacturer IS NOT NULL THEN 1 END) as devices_with_manufacturer,
    COUNT(CASE WHEN system_model IS NOT NULL THEN 1 END) as devices_with_model,
    COUNT(CASE WHEN memory_gib IS NOT NULL THEN 1 END) as devices_with_memory,
    COUNT(CASE WHEN volumes IS NOT NULL THEN 1 END) as devices_with_volumes,
    COUNT(CASE WHEN os_architecture IS NOT NULL THEN 1 END) as devices_with_architecture
FROM device_snapshot ds
JOIN vendor v ON ds.vendor_id = v.id
WHERE v.name = 'Ninja'
AND ds.snapshot_date = CURRENT_DATE;
```

### **Check Exception Data Quality**
```sql
SELECT 
    type,
    COUNT(*) as total_exceptions,
    COUNT(CASE WHEN details::text != '{}' THEN 1 END) as exceptions_with_details,
    COUNT(CASE WHEN organization_name IS NOT NULL THEN 1 END) as exceptions_with_organization
FROM exceptions
WHERE date_found = CURRENT_DATE
GROUP BY type
ORDER BY total_exceptions DESC;
```

---

## 📚 **RELATED DOCUMENTATION**

- [API Integration Guide](./API_INTEGRATION_GUIDE.md) - Core API endpoints and usage
- [Variances Dashboard Guide](./VARIANCES_DASHBOARD_GUIDE.md) - Dashboard functionality
- [Windows 11 24H2 Guide](./WINDOWS_11_24H2_GUIDE.md) - Windows 11 compatibility assessment
- [Setup and Troubleshooting Guide](./SETUP_AND_TROUBLESHOOTING_GUIDE.md) - Operational guide

---

**🎉 The ES Inventory Hub database schema is fully operational and ready for Dashboard AI integration!**

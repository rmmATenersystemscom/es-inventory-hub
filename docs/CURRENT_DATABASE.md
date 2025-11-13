# Current Database Structure - ES Inventory Hub

**Last Updated**: January 2025  
**Database System**: PostgreSQL  
**ORM Framework**: SQLAlchemy  
**Migration Tool**: Alembic  
**Status**: ✅ **OPERATIONAL**

---

## 📋 **Overview**

The ES Inventory Hub database stores device inventory data collected from multiple vendors (NinjaRMM, ThreatLocker) on a daily snapshot basis. The database is designed to track device state over time, support cross-vendor consistency checks, and enable variance reporting.

### **Key Design Principles**
- **Daily Snapshots**: Each device has one snapshot per day per vendor
- **Vendor-Agnostic Identity**: Devices are tracked via `device_identity` table using vendor-specific keys
- **Historical Preservation**: Data is preserved for 65 days, with monthly rollups for older history
- **Cross-Vendor Matching**: Sophisticated algorithms match devices across vendors by hostname

---

## 🗄️ **Database Tables**

### **Core Reference Tables**

#### **`vendor`**
Represents different vendors/suppliers that provide device data.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Unique vendor identifier |
| `name` | VARCHAR(255) | Vendor name (unique) |

**Current Values:**
- `id=3`: Ninja (NinjaRMM)
- `id=4`: ThreatLocker

**Relationships:**
- One-to-many with `site`
- One-to-many with `device_identity`
- One-to-many with `device_snapshot`
- One-to-many with `daily_counts`
- One-to-many with `month_end_counts`
- One-to-many with `change_log`

---

#### **`device_type`**
Represents different types of devices.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Unique device type identifier |
| `code` | VARCHAR(100) | Device type code (unique) |

**Common Values:**
- `server`: Server computers
- `workstation`: Workstation computers
- `Desktop`: Desktop computers
- `Laptop`: Laptop computers

**Relationships:**
- One-to-many with `device_snapshot`
- One-to-many with `daily_counts`
- One-to-many with `month_end_counts`

---

#### **`billing_status`**
Represents billing status classifications for devices.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Unique billing status identifier |
| `code` | VARCHAR(100) | Billing status code (unique) |

**Common Values:**
- `billable`: Device is billable
- `spare`: Device is a spare (not billable)
- `unknown`: Billing status unknown

**Relationships:**
- One-to-many with `device_snapshot`
- One-to-many with `daily_counts`
- One-to-many with `month_end_counts`

---

### **Site and Organization Tables**

#### **`site`**
Represents sites/locations within vendor systems.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Unique site identifier |
| `vendor_id` | INTEGER FK | Reference to `vendor.id` |
| `vendor_site_key` | VARCHAR(255) | Vendor-specific site identifier |
| `name` | VARCHAR(255) | Site name |

**Unique Constraint:** `(vendor_id, vendor_site_key)`

**Indexes:**
- `idx_site_vendor_id`
- `idx_site_vendor_site_key`

**Relationships:**
- Many-to-one with `vendor`
- One-to-many with `device_snapshot`
- One-to-many with `daily_counts`
- One-to-many with `month_end_counts`

**Note:** Sites are vendor-specific. The same physical location may have different site records for different vendors.

---

#### **`site_alias`**
Represents alternative names for sites (for matching purposes).

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Unique alias identifier |
| `canonical_name` | VARCHAR(255) | Canonical site name |
| `vendor_id` | INTEGER FK | Reference to `vendor.id` |
| `vendor_site_key` | VARCHAR(255) | Vendor-specific site identifier |

**Unique Constraint:** `(vendor_id, vendor_site_key)`

**Relationships:**
- Many-to-one with `vendor`

---

### **Device Identity and Tracking**

#### **`device_identity`**
Central table representing unique device identifiers across vendors. This is the foundation for cross-vendor device matching.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Unique device identity identifier |
| `vendor_id` | INTEGER FK | Reference to `vendor.id` |
| `vendor_device_key` | VARCHAR(255) | Vendor-specific unique device identifier |
| `first_seen_date` | DATE | Date device was first discovered |
| `last_seen_date` | DATE | Date device was last seen |

**Unique Constraint:** `(vendor_id, vendor_device_key)`

**Indexes:**
- `idx_device_identity_vendor_id`
- `idx_device_identity_vendor_device_key`
- `idx_device_identity_first_seen`
- `idx_device_identity_last_seen`

**Vendor-Specific Keys:**
- **ThreatLocker**: Uses `computerId` (UUID) as `vendor_device_key`
- **NinjaRMM**: Uses `systemName` as `vendor_device_key`

**Relationships:**
- Many-to-one with `vendor`
- One-to-many with `device_snapshot`

**Purpose:** Prevents duplicate device entries and enables tracking device lifecycle across vendors.

---

#### **`device_snapshot`**
Main table storing device state at a point in time. Contains daily snapshots of all devices from all vendors.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Unique snapshot identifier |
| `snapshot_date` | DATE | Date of the snapshot |
| `vendor_id` | INTEGER FK | Reference to `vendor.id` |
| `device_identity_id` | INTEGER FK | Reference to `device_identity.id` |
| `site_id` | INTEGER FK | Reference to `site.id` (nullable) |
| `device_type_id` | INTEGER FK | Reference to `device_type.id` (nullable) |
| `billing_status_id` | INTEGER FK | Reference to `billing_status.id` (nullable) |
| `hostname` | VARCHAR(255) | Device hostname |
| `os_name` | VARCHAR(255) | Operating system name |
| `created_at` | TIMESTAMPTZ | Record creation timestamp |

**Core Device Information:**
- `organization_name` | VARCHAR(255) | Organization name from vendor
- `display_name` | VARCHAR(255) | Display name
- `device_status` | VARCHAR(100) | Device status

**NinjaRMM-Specific Fields:**
- `location_name` | VARCHAR(255) | Location name
- `device_type_name` | VARCHAR(100) | Device type name
- `billable_status_name` | VARCHAR(100) | Billable status name
- `last_online` | TIMESTAMPTZ | Last online timestamp
- `agent_install_timestamp` | TIMESTAMPTZ | Agent installation timestamp

**ThreatLocker-Specific Fields:**
- `organization_id` | VARCHAR(255) | ThreatLocker organization ID
- `computer_group` | VARCHAR(255) | Computer group
- `security_mode` | VARCHAR(100) | Security mode
- `deny_count_1d` | INTEGER | Deny count (1 day)
- `deny_count_3d` | INTEGER | Deny count (3 days)
- `deny_count_7d` | INTEGER | Deny count (7 days)
- `install_date` | TIMESTAMPTZ | ThreatLocker install date
- `is_locked_out` | BOOLEAN | Locked out status
- `is_isolated` | BOOLEAN | Isolated status
- `agent_version` | VARCHAR(100) | Agent version
- `has_checked_in` | BOOLEAN | Check-in status

**Hardware Information (Ninja-specific):**
- `has_tpm` | BOOLEAN | TPM available
- `tpm_enabled` | BOOLEAN | TPM enabled
- `tpm_version` | VARCHAR(100) | TPM version
- `secure_boot_available` | BOOLEAN | Secure Boot available
- `secure_boot_enabled` | BOOLEAN | Secure Boot enabled
- `os_architecture` | VARCHAR(100) | OS architecture
- `cpu_model` | VARCHAR(255) | CPU model
- `system_manufacturer` | VARCHAR(255) | System manufacturer
- `system_model` | VARCHAR(255) | System model
- `memory_gib` | NUMERIC(10,2) | Memory in GiB
- `volumes` | TEXT | Volume information

**Windows 11 24H2 Assessment:**
- `windows_11_24h2_capable` | BOOLEAN | Windows 11 24H2 capable
- `windows_11_24h2_deficiencies` | TEXT | Deficiency details (JSON)
- `os_build` | VARCHAR(100) | OS build number
- `os_release_id` | VARCHAR(100) | OS release ID

**Unique Constraint:** `(snapshot_date, vendor_id, device_identity_id)`

**Key Indexes:**
- `idx_device_snapshot_date` - For date-based queries
- `idx_device_snapshot_vendor_id` - For vendor filtering
- `idx_device_snapshot_device_identity_id` - For device lookup
- `idx_device_snapshot_hostname` - For hostname matching
- `idx_device_snapshot_organization_name` - For organization queries
- Plus many vendor-specific indexes

**Relationships:**
- Many-to-one with `vendor`
- Many-to-one with `device_identity`
- Many-to-one with `site`
- Many-to-one with `device_type`
- Many-to-one with `billing_status`

**Data Collection Behavior:**
- **Daily Snapshots**: One snapshot per device per day per vendor
- **Multiple Runs**: If collector runs multiple times per day, existing snapshots for that day are deleted and replaced
- **Historical Preservation**: Previous days' data is never modified

---

### **Aggregation Tables**

#### **`daily_counts`**
Pre-aggregated daily device counts by various dimensions for performance.

| Column | Type | Description |
|--------|------|-------------|
| `snapshot_date` | DATE PK | Date of the count |
| `vendor_id` | INTEGER PK, FK | Reference to `vendor.id` |
| `site_id` | INTEGER PK, FK | Reference to `site.id` (nullable) |
| `device_type_id` | INTEGER PK, FK | Reference to `device_type.id` (nullable) |
| `billing_status_id` | INTEGER PK, FK | Reference to `billing_status.id` (nullable) |
| `cnt` | INTEGER | Count of devices |

**Composite Primary Key:** `(snapshot_date, vendor_id, site_id, device_type_id, billing_status_id)`

**Indexes:**
- `idx_daily_counts_date`
- `idx_daily_counts_vendor_id`
- `idx_daily_counts_site_id`
- `idx_daily_counts_device_type_id`
- `idx_daily_counts_billing_status_id`

**Purpose:** Optimizes queries that need aggregated counts without scanning all device snapshots.

---

#### **`month_end_counts`**
Pre-aggregated month-end device counts for historical reporting.

| Column | Type | Description |
|--------|------|-------------|
| `month_end_date` | DATE PK | Month-end date |
| `vendor_id` | INTEGER PK, FK | Reference to `vendor.id` |
| `site_id` | INTEGER PK, FK | Reference to `site.id` (nullable) |
| `device_type_id` | INTEGER PK, FK | Reference to `device_type.id` (nullable) |
| `billing_status_id` | INTEGER PK, FK | Reference to `billing_status.id` (nullable) |
| `cnt` | INTEGER | Count of devices |

**Composite Primary Key:** `(month_end_date, vendor_id, site_id, device_type_id, billing_status_id)`

**Indexes:**
- `idx_month_end_counts_date`
- `idx_month_end_counts_vendor_id`
- `idx_month_end_counts_site_id`
- `idx_month_end_counts_device_type_id`
- `idx_month_end_counts_billing_status_id`

**Purpose:** Stores monthly rollups for data older than 65 days.

---

### **Exception and Variance Tracking**

#### **`exceptions`**
Stores persistent exceptions and variances detected by cross-vendor consistency checks.

| Column | Type | Description |
|--------|------|-------------|
| `id` | BIGINT PK | Unique exception identifier |
| `date_found` | DATE | Date exception was found |
| `type` | VARCHAR(64) | Exception type |
| `hostname` | VARCHAR(255) | Device hostname |
| `details` | JSONB | Exception details (JSON) |
| `resolved` | BOOLEAN | Resolution status |

**Exception Types:**
- `MISSING_NINJA`: Device in ThreatLocker but not in Ninja
- `DUPLICATE_TL`: Duplicate hostnames in ThreatLocker
- `SITE_MISMATCH`: Same device assigned to different sites
- `SPARE_MISMATCH`: ThreatLocker installed on spare devices

**Indexes:**
- `ix_exceptions_type_date` - Composite index on (type, date_found)
- `ix_exceptions_hostname` - For hostname lookups
- `ix_exceptions_resolved` - For filtering unresolved exceptions

**Purpose:** Tracks cross-vendor discrepancies that require technician attention.

---

### **Job Tracking Tables**

#### **`job_batches`**
Tracks batch execution of collector jobs.

| Column | Type | Description |
|--------|------|-------------|
| `batch_id` | VARCHAR(50) PK | Unique batch identifier |
| `created_at` | TIMESTAMPTZ | Batch creation timestamp |
| `status` | VARCHAR(20) | Batch status (queued, running, completed, failed) |
| `priority` | VARCHAR(20) | Batch priority (normal, high, low) |
| `started_at` | TIMESTAMPTZ | Batch start timestamp |
| `ended_at` | TIMESTAMPTZ | Batch end timestamp |
| `progress_percent` | INTEGER | Progress percentage (0-100) |
| `estimated_completion` | TIMESTAMPTZ | Estimated completion time |
| `message` | TEXT | Status message |
| `error` | TEXT | Error message (if failed) |
| `duration_seconds` | INTEGER | Execution duration |

**Indexes:**
- `idx_job_batches_status`
- `idx_job_batches_created_at`

**Relationships:**
- One-to-many with `job_runs`

---

#### **`job_runs`**
Tracks individual job execution history within batches.

| Column | Type | Description |
|--------|------|-------------|
| `job_id` | VARCHAR(50) PK | Unique job identifier |
| `batch_id` | VARCHAR(50) FK | Reference to `job_batches.batch_id` |
| `job_name` | VARCHAR(50) | Job name (e.g., 'ninja', 'threatlocker') |
| `status` | VARCHAR(20) | Job status |
| `started_at` | TIMESTAMPTZ | Job start timestamp |
| `updated_at` | TIMESTAMPTZ | Last update timestamp |
| `ended_at` | TIMESTAMPTZ | Job end timestamp |
| `progress_percent` | INTEGER | Progress percentage |
| `message` | TEXT | Status message |
| `error` | TEXT | Error message |
| `duration_seconds` | INTEGER | Execution duration |

**Indexes:**
- `idx_job_runs_batch_id`
- `idx_job_runs_job_name`
- `idx_job_runs_started_at`
- `idx_job_runs_status`

**Relationships:**
- Many-to-one with `job_batches`

---

#### **`change_log`**
Tracks changes in metrics over time.

| Column | Type | Description |
|--------|------|-------------|
| `change_date` | DATE PK | Date of change |
| `vendor_id` | INTEGER PK, FK | Reference to `vendor.id` |
| `metric` | TEXT PK | Metric name |
| `prev_value` | INTEGER | Previous value |
| `new_value` | INTEGER | New value |
| `delta` | INTEGER | Change amount |
| `details` | JSONB | Additional details (JSON) |

**Composite Primary Key:** `(change_date, vendor_id, metric)`

**Indexes:**
- `idx_change_log_date`
- `idx_change_log_vendor_id`
- `idx_change_log_metric`

---

## 🔗 **Table Relationships**

### **Entity Relationship Diagram (Conceptual)**

```
vendor (1) ──< (many) site
vendor (1) ──< (many) device_identity
vendor (1) ──< (many) device_snapshot
vendor (1) ──< (many) daily_counts
vendor (1) ──< (many) month_end_counts
vendor (1) ──< (many) change_log

device_identity (1) ──< (many) device_snapshot

site (1) ──< (many) device_snapshot
site (1) ──< (many) daily_counts
site (1) ──< (many) month_end_counts

device_type (1) ──< (many) device_snapshot
device_type (1) ──< (many) daily_counts
device_type (1) ──< (many) month_end_counts

billing_status (1) ──< (many) device_snapshot
billing_status (1) ──< (many) daily_counts
billing_status (1) ──< (many) month_end_counts

job_batches (1) ──< (many) job_runs
```

---

## 📊 **Data Collection Pattern**

### **Daily Snapshot Model**

The database uses a **daily snapshot model** where:

1. **One Snapshot Per Day**: Each device has exactly one snapshot per day per vendor
2. **Daily Refresh**: Collectors run daily and replace that day's data
3. **Historical Preservation**: Previous days' data is never modified
4. **65-Day Retention**: Daily data is kept for 65 days
5. **Monthly Rollups**: Data older than 65 days is aggregated into `month_end_counts`

### **Collection Schedule**

- **Ninja Collector**: Daily at 02:10 AM Central Time
- **ThreatLocker Collector**: Daily at 02:31 AM Central Time
- **Cross-Vendor Checks**: Daily at 03:00 AM Central Time

### **Multiple Runs Per Day**

If a collector runs multiple times in the same day:
- Existing snapshots for that day are **deleted**
- New snapshots are **inserted**
- Result: Only the latest state is preserved for each day

---

## 🔍 **Device Matching Logic**

### **Cross-Vendor Device Matching**

Devices are matched between vendors using **canonical keys**:

**ThreatLocker Canonical Key:**
```sql
LOWER(LEFT(SPLIT_PART(hostname,'.',1),15))
```

**Ninja Canonical Keys** (matches if ANY are true):
1. `LOWER(LEFT(SPLIT_PART(ds.hostname,'.',1),15))`
2. `LOWER(LEFT(SPLIT_PART(COALESCE(ds.raw->>'system_name', ...),'.',1),15))`
3. `LOWER(LEFT(SPLIT_PART(SPLIT_PART(COALESCE(ds.raw->>'display_name', ...),'|',1),'.',1),15))`

**Matching Strategy:**
- Case-insensitive comparison
- Domain-stripped (removes `.domain.com`)
- 15-character limit for consistency
- Multiple fallback fields for Ninja

---

## 📈 **Common Queries**

### **Count Devices Per Vendor Per Day**
```sql
SELECT snapshot_date, vendor_id, COUNT(*)
FROM device_snapshot
GROUP BY snapshot_date, vendor_id
ORDER BY snapshot_date DESC, vendor_id;
```

### **Check for ThreatLocker Duplicates**
```sql
SELECT LOWER(SPLIT_PART(hostname, '.', 1)) AS host, COUNT(*)
FROM device_snapshot
WHERE snapshot_date = CURRENT_DATE AND vendor_id = 4
GROUP BY LOWER(SPLIT_PART(hostname, '.', 1))
HAVING COUNT(*) > 1
ORDER BY 2 DESC;
```

### **Get Unresolved Exceptions**
```sql
SELECT type, hostname, date_found, details
FROM exceptions
WHERE resolved = FALSE
ORDER BY date_found DESC, type;
```

### **Get Latest Device Counts**
```sql
SELECT 
    snapshot_date,
    vendor_id,
    COUNT(*) as device_count,
    COUNT(DISTINCT site_id) as site_count
FROM device_snapshot
WHERE snapshot_date = CURRENT_DATE
GROUP BY snapshot_date, vendor_id;
```

---

## 🔧 **Database Management**

### **Migration Management**
- **Tool**: Alembic
- **Location**: `/opt/es-inventory-hub/storage/alembic/`
- **Schema Definition**: `/opt/es-inventory-hub/storage/schema.py`

### **Connection**
- **ORM**: SQLAlchemy
- **Connection String**: Stored in environment variable `DB_DSN`
- **Format**: `postgresql://username:password@hostname:port/database_name`

### **Backup Strategy**
- Daily snapshots preserved for 65 days
- Monthly rollups for historical data
- Exceptions table persists until manually resolved

---

## 📝 **Notes**

### **Vendor IDs**
- **NinjaRMM**: `vendor_id = 3`
- **ThreatLocker**: `vendor_id = 4`

### **Data Volume**
- Current device count: ~762 devices (NinjaRMM)
- Daily snapshot volume: ~1,500+ records (multiple vendors)
- Historical data: 65 days of daily snapshots + monthly rollups

### **Performance Considerations**
- Extensive indexing on `device_snapshot` for fast queries
- Aggregation tables (`daily_counts`, `month_end_counts`) for summary queries
- JSONB fields for flexible vendor-specific data storage

---

**Document Version**: 1.0  
**Last Updated**: January 2025  
**Maintained By**: Database AI


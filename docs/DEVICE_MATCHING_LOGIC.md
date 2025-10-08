# Device Matching Logic for Cross-Vendor Consistency

**Purpose**: This document explains how devices are matched between Ninja and ThreatLocker vendors in the ES Inventory Hub database for variance reporting and cross-vendor consistency checks.

**Last Updated**: October 8, 2025  
**Related Files**: `/opt/es-inventory-hub/collectors/checks/cross_vendor.py`  
**Status**: ✅ **UPDATED** - ThreatLocker now uses computerId for unique device identification

---

## 🔗 Overview

The ES Inventory Hub uses sophisticated algorithms to match devices between different vendors (Ninja and ThreatLocker) to identify discrepancies, duplicates, and inconsistencies. This matching logic is essential for generating accurate variance reports.

---

## 🏗️ Database Schema for Device Matching

### **Core Tables**

#### **`device_identity` Table**
The central table that represents unique device identifiers across vendors:

```sql
CREATE TABLE device_identity (
    id BIGINT PRIMARY KEY,
    vendor_id INTEGER NOT NULL REFERENCES vendor(id),
    vendor_device_key VARCHAR(255) NOT NULL,
    first_seen_date DATE NOT NULL,
    last_seen_date DATE NOT NULL,
    UNIQUE(vendor_id, vendor_device_key)
);
```

#### **`device_snapshot` Table**
Contains the actual device data linked to device identities:

```sql
CREATE TABLE device_snapshot (
    id BIGINT PRIMARY KEY,
    snapshot_date DATE NOT NULL,
    vendor_id INTEGER NOT NULL REFERENCES vendor(id),
    device_identity_id BIGINT NOT NULL REFERENCES device_identity(id),
    hostname VARCHAR(255),
    display_name VARCHAR(255),
    organization_name VARCHAR(255),
    -- ... other fields
    UNIQUE(snapshot_date, vendor_id, device_identity_id)
);
```

#### **`vendor` Table**
Identifies the data source:

```sql
CREATE TABLE vendor (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE
);

-- Typical values:
-- id=3: Ninja
-- id=4: ThreatLocker
```

---

## 🔍 Device Matching Algorithms

### **1. Canonical Key Generation**

The system uses normalized "canonical keys" to match devices across vendors:

#### **ThreatLocker Canonical Key**
```sql
LOWER(LEFT(SPLIT_PART(SPLIT_PART(hostname,'|',1),'.',1),15))
```

**Important**: ThreatLocker has multiple fields with specific usage:
- **Required for unique device identification**: `computerId` field (UUID format, used as vendor_device_key)
- **Required for device matching**: `hostname` field (no fallbacks)
- **Used for display_name**: `computerName` field (contains user-friendly names like "CHI-4YHKJL3 | Keith Oneil")
- **Do NOT use**: `name` field (no fallbacks allowed)

**⚠️ Data Quality Handling**: The system uses different fields for different purposes:
1. **Unique Device Identification**: Uses `computerId` field (UUID) as vendor_device_key to prevent duplicate device entries
2. **Device Matching**: Uses `hostname` field (clean hostname without user info)
3. **Display Names**: Uses `computerName` field (contains user-friendly names with pipe symbols)
4. **Canonical Key Generation**: Extracts clean hostnames by taking the first part before the pipe symbol

The system **requires** both the `computerId` and `hostname` fields and will throw an exception if either is missing, as this indicates a critical data quality issue that prevents proper device identification and matching.

**Examples**: 
- `computerId: 7bfd601f-8863-49e2-b8a1-8d88edca0169` → Used as vendor_device_key
- `hostname: SERVER-01.domain.com` → `server-01` (for canonical key)
- `computerName: CHI-1P397H2 | SPARE - was Blake Thomas` → Used for display_name

#### **Ninja Canonical Key**
The system uses only the `systemName` field (analogous to ThreatLocker's `hostname`):

```sql
LOWER(LEFT(SPLIT_PART(hostname,'.',1),15))
```

**Important**: Ninja has multiple fields, but only the `systemName` field is used:
- **Required**: `systemName` field (no fallbacks)
- **Do NOT use**: `displayName` field (never used as anchor for device matching)
- **Do NOT use**: `hostname`, `deviceName`, `dnsName` fields (no fallbacks allowed)

The system **requires** the `systemName` field and will throw an exception if it's missing, as this indicates a critical data quality issue that prevents device matching.

**Example**: `SERVER-01.domain.com` → `server-01`

### **2. Cross-Vendor Matching Process**

#### **Step 1: Generate Canonical Keys**
```python
def to_base(hostname: str) -> str:
    """Convert hostname to base form (lowercase, first part before dot)."""
    if not hostname:
        return ''
    return hostname.lower().split('.')[0]
```

#### **Step 2: Find Matching Devices**
```sql
-- Find ThreatLocker devices with no matching Ninja device
-- Note: Both vendors require their primary hostname fields (no fallbacks)
-- ThreatLocker: hostname field (computerName contains pipe symbols)
-- Ninja: systemName field (displayName never used as anchor)
-- UPDATED: ThreatLocker canonical key now handles pipe symbols
WITH tl_canonical AS (
    SELECT 
        ds.id,
        ds.hostname,
        LOWER(LEFT(SPLIT_PART(SPLIT_PART(ds.hostname,'|',1),'.',1),15)) as canonical_key
    FROM device_snapshot ds
    WHERE ds.snapshot_date = :snapshot_date
      AND ds.vendor_id = :tl_vendor_id
      AND ds.hostname IS NOT NULL
),
ninja_canonical AS (
    SELECT DISTINCT
        LOWER(LEFT(SPLIT_PART(ds.hostname,'.',1),15)) as canonical_key
    FROM device_snapshot ds
    WHERE ds.snapshot_date = :snapshot_date
      AND ds.vendor_id = :ninja_vendor_id
      AND ds.hostname IS NOT NULL
)
SELECT 
    tl.id,
    tl.hostname,
    tl.canonical_key
FROM tl_canonical tl
LEFT JOIN ninja_canonical nc ON tl.canonical_key = nc.canonical_key
WHERE nc.canonical_key IS NULL
```

---

## 📊 Variance Check Types

### **1. MISSING_NINJA**
**Purpose**: Find ThreatLocker devices that have no matching Ninja device.

**Logic**: 
- Generate canonical keys for all ThreatLocker devices
- Generate canonical keys for all Ninja devices (hostname + display_name)
- Find ThreatLocker devices with no matching Ninja canonical key

**Example**:
- ThreatLocker: `SERVER-01.domain.com` → `server-01`
- Ninja: No device with canonical key `server-01`
- **Result**: MISSING_NINJA exception

### **2. DUPLICATE_TL**
**Purpose**: Find duplicate ThreatLocker entries (same hostname with different computerIds).

**Logic**:
```sql
SELECT 
    LOWER(LEFT(SPLIT_PART(hostname, '.', 1)), 15) as hostname_base,
    COUNT(*) as count
FROM device_snapshot 
WHERE snapshot_date = :date 
  AND vendor_id = :tl_vendor_id
  AND hostname IS NOT NULL
GROUP BY hostname_base
HAVING COUNT(*) > 1
```

**Example**:
- ThreatLocker Device 1: `computerId: abc-123`, `hostname: SERVER-01.domain.com` → `server-01`
- ThreatLocker Device 2: `computerId: def-456`, `hostname: SERVER-01.other.com` → `server-01`
- **Result**: DUPLICATE_TL exception (same hostname, different computerIds)

**Note**: This detects when the same physical device has been added multiple times to the ThreatLocker portal with the same hostname but different computerIds.

### **3. SITE_MISMATCH**
**Purpose**: Find devices that exist in both vendors but have different site assignments.

**Logic**:
1. Find devices that match between vendors (same canonical key)
2. Compare their site assignments
3. Flag mismatches

**Example**:
- ThreatLocker: `SERVER-01` in site "Office A"
- Ninja: `SERVER-01` in site "Office B"
- **Result**: SITE_MISMATCH exception

### **4. SPARE_MISMATCH (DevicesThatShouldNotHaveThreatlocker)**
**Purpose**: Find devices marked as "spare" in Ninja but still present in ThreatLocker.

**Logic**:
1. Find devices that match between vendors
2. Check if Ninja marks the device as "spare" (billing_status = 'spare')
3. Flag for potential cleanup

**Example**:
- ThreatLocker: `OLD-SERVER` still present
- Ninja: `OLD-SERVER` marked as spare
- **Result**: SPARE_MISMATCH exception (DevicesThatShouldNotHaveThreatlocker - cleanup opportunity)

---

## 💻 Implementation Details

### **Key Functions in `cross_vendor.py`**

#### **`check_missing_ninja()`**
```python
def check_missing_ninja(session: Session, vendor_ids: Dict[str, int], snapshot_date: date) -> int:
    """
    Check for ThreatLocker hosts that have no matching Ninja host using robust anchors.
    
    Uses canonical TL key: LOWER(LEFT(SPLIT_PART(hostname,'.',1),15))
    Uses canonical Ninja keys (ANY match true):
    1) LOWER(LEFT(SPLIT_PART(ds.hostname,'.',1),15))
    2) LOWER(LEFT(SPLIT_PART(COALESCE(ds.display_name,''),'.',1),15))
    """
```

#### **`check_duplicate_tl()`**
```python
def check_duplicate_tl(session: Session, vendor_ids: Dict[str, int], snapshot_date: date) -> int:
    """
    Check for duplicate ThreatLocker hosts (same hostname_base count > 1).
    """
```

#### **`check_site_mismatch()`**
```python
def check_site_mismatch(session: Session, vendor_ids: Dict[str, int], snapshot_date: date) -> int:
    """
    Check for site/org mismatch between matching Ninja and ThreatLocker hosts.
    """
```

#### **`check_spare_mismatch()`**
```python
def check_spare_mismatch(session: Session, vendor_ids: Dict[str, int], snapshot_date: date) -> int:
    """
    Check for spare mismatch: ThreatLocker present but Ninja marks as spare.
    (DevicesThatShouldNotHaveThreatlocker)
    """
```

### **Main Entry Point**
```python
def run_cross_vendor_checks(session: Session, snapshot_date: Optional[date] = None) -> Dict[str, int]:
    """
    Run all cross-vendor consistency checks between Ninja and ThreatLocker.
    
    Returns:
        dict: Count of exceptions inserted by type
    """
    results = {}
    results['MISSING_NINJA'] = check_missing_ninja(session, vendor_ids, snapshot_date)
    results['DUPLICATE_TL'] = check_duplicate_tl(session, vendor_ids, snapshot_date)
    results['SITE_MISMATCH'] = check_site_mismatch(session, vendor_ids, snapshot_date)
    results['SPARE_MISMATCH'] = check_spare_mismatch(session, vendor_ids, snapshot_date)
    return results
```

---

## 🔧 Usage for Dashboard Development

### **Essential Queries for Variance Dashboard**

#### **Get All Exceptions by Type**
```sql
SELECT 
    type,
    COUNT(*) as count,
    COUNT(CASE WHEN resolved = false THEN 1 END) as unresolved_count
FROM exceptions 
WHERE date_found = CURRENT_DATE 
GROUP BY type
ORDER BY count DESC;
```

#### **Get Detailed Exception Data**
```sql
SELECT 
    e.id,
    e.type,
    e.hostname,
    e.details,
    e.resolved,
    e.date_found
FROM exceptions e
WHERE e.date_found = CURRENT_DATE
ORDER BY e.type, e.hostname;
```

#### **Get Device Counts by Vendor**
```sql
SELECT 
    v.name as vendor_name,
    COUNT(ds.id) as device_count
FROM device_snapshot ds
JOIN vendor v ON ds.vendor_id = v.id
WHERE ds.snapshot_date = CURRENT_DATE
GROUP BY v.name
ORDER BY device_count DESC;
```

### **Python Integration Example**
```python
from sqlalchemy.orm import Session
from storage.schema import Exceptions, DeviceSnapshot, Vendor
from collectors.checks.cross_vendor import run_cross_vendor_checks

def get_variance_data(session: Session, snapshot_date: date):
    """Get complete variance data for dashboard."""
    
    # Run cross-vendor checks to ensure data is current
    check_results = run_cross_vendor_checks(session, snapshot_date)
    
    # Get exception summary
    exceptions = session.query(Exceptions).filter(
        Exceptions.date_found == snapshot_date
    ).all()
    
    # Get device counts
    device_counts = session.query(
        Vendor.name,
        func.count(DeviceSnapshot.id).label('count')
    ).join(DeviceSnapshot).filter(
        DeviceSnapshot.snapshot_date == snapshot_date
    ).group_by(Vendor.name).all()
    
    return {
        'exceptions': exceptions,
        'device_counts': device_counts,
        'check_results': check_results
    }
```

---

## 🚨 Important Considerations

### **Critical Hostname Truncation Issue**
**⚠️ MAJOR LIMITATION**: Ninja truncates hostnames to 15 characters, while ThreatLocker stores full hostnames (up to 20 characters). This creates several problems:

1. **Search/Lookup Issues**: Users searching with Ninja hostnames won't find corresponding ThreatLocker devices
   - Example: Search for `AEC-02739619435` (Ninja) won't find `AEC-027396194353` (ThreatLocker)
2. **Data Loss**: Information beyond 15 characters is permanently lost in Ninja data
3. **False Matches**: Devices that differ only in characters 16+ will incorrectly match

**Impact on User Experience**:
- Dashboard searches may fail to find devices
- Manual lookups between vendors will be problematic
- Users need to know the full hostname to search ThreatLocker data

### **Solutions for Hostname Truncation Issues**

#### **1. Enhanced Search Functionality**
Implement fuzzy search that handles truncated hostnames:

```sql
-- Search for devices with partial hostname matching
SELECT 
    v.name as vendor,
    ds.hostname,
    ds.display_name,
    ds.organization_name
FROM device_snapshot ds
JOIN vendor v ON ds.vendor_id = v.id
WHERE ds.snapshot_date = CURRENT_DATE
  AND (
    ds.hostname ILIKE :search_term || '%'  -- Exact prefix match
    OR ds.hostname ILIKE '%' || :search_term || '%'  -- Contains match
    OR LEFT(ds.hostname, 15) = LEFT(:search_term, 15)  -- Truncated match
  )
ORDER BY v.name, ds.hostname;
```

#### **2. Cross-Vendor Device Lookup**
Create a function to find matching devices across vendors:

```sql
-- Find all vendors for a given canonical hostname
CREATE OR REPLACE FUNCTION find_device_across_vendors(search_hostname TEXT)
RETURNS TABLE (
    vendor_name TEXT,
    full_hostname TEXT,
    canonical_key TEXT,
    display_name TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        v.name as vendor_name,
        ds.hostname as full_hostname,
        LOWER(LEFT(SPLIT_PART(SPLIT_PART(ds.hostname,'|',1),'.',1),15)) as canonical_key,
        ds.display_name
    FROM device_snapshot ds
    JOIN vendor v ON ds.vendor_id = v.id
    WHERE ds.snapshot_date = CURRENT_DATE
      AND ds.hostname IS NOT NULL
      AND (
        -- Exact match
        ds.hostname ILIKE search_hostname || '%'
        -- Or canonical key match (handles truncation)
        OR LOWER(LEFT(SPLIT_PART(SPLIT_PART(ds.hostname,'|',1),'.',1),15)) = 
           LOWER(LEFT(SPLIT_PART(search_hostname,'.',1),15))
      )
    ORDER BY v.name, ds.hostname;
END;
$$ LANGUAGE plpgsql;
```

#### **3. Dashboard Search Recommendations**
- **Primary Search**: Use canonical key matching (first 15 characters)
- **Secondary Search**: Show all devices with matching canonical keys
- **User Education**: Display warnings when hostnames are truncated
- **Suggestion System**: When searching with truncated hostname, suggest full hostnames from other vendors

#### **4. API Implementation**
The ES Inventory Hub now includes a dedicated search endpoint that handles hostname truncation:

```bash
GET /api/devices/search?q={hostname}&vendor={ninja|threatlocker}&limit={number}
```

**Features:**
- **Multi-strategy search**: Exact match, contains match, canonical key match, prefix match
- **Cross-vendor grouping**: Results grouped by canonical key to show related devices
- **Truncation detection**: Indicates when hostnames are truncated
- **Vendor filtering**: Optional vendor-specific searches
- **Performance optimized**: Capped at 200 results with efficient queries

**Example Usage:**
```bash
# Search for device using Ninja hostname (truncated)
curl "https://db-api.enersystems.com:5400/api/devices/search?q=AEC-02739619435"

# Search for device using ThreatLocker hostname (full)
curl "https://db-api.enersystems.com:5400/api/devices/search?q=AEC-027396194353"

# Search only in Ninja
curl "https://db-api.enersystems.com:5400/api/devices/search?q=AEC-02739619435&vendor=ninja"
```

**Response Format:**
```json
{
  "search_term": "AEC-02739619435",
  "total_results": 2,
  "vendors_found": ["Ninja", "ThreatLocker"],
  "truncated_hostnames": 1,
  "grouped_by_canonical_key": {
    "aec-02739619435": [
      {
        "vendor": "Ninja",
        "hostname": "AEC-02739619435",
        "is_truncated": true
      },
      {
        "vendor": "ThreatLocker", 
        "hostname": "AEC-027396194353",
        "is_truncated": false
      }
    ]
  },
  "warning": "Some hostnames may be truncated due to Ninja 15-character limit"
}
```

### **Data Quality Requirements**
1. **Hostnames must be present** - devices without hostnames cannot be matched
2. **Consistent naming** - devices should use consistent naming conventions
3. **Regular collection** - data must be collected daily for accurate matching
4. **Hostname truncation awareness** - Users must understand Ninja truncation limitations
5. **Field mapping requirements** - The system maps vendor fields as follows:
   
   **ThreatLocker**:
   - `hostname` → `hostname` (required field for device matching, no fallbacks)
   - `computerName` → `display_name` (contains user-friendly names like "CHI-4YHKJL3 | Keith Oneil")
   - `name` → **NOT USED** (no fallbacks allowed)
   
   **Ninja**:
   - `systemName` → `hostname` (required field, no fallbacks)
   - `displayName` → **NOT USED** (never used as anchor for device matching)
   - `hostname`, `deviceName`, `dnsName` → **NOT USED** (no fallbacks allowed)
   
   **Critical**: If either `hostname` (ThreatLocker) or `systemName` (Ninja) is missing, the system throws an exception and stops processing. The `computerName` field is used for display purposes but is not required for device matching.

### **Performance Optimization**
1. **Indexes are critical** - the system relies on database indexes for performance
2. **Batch processing** - checks are run in batches for efficiency
3. **Idempotent operations** - checks can be run multiple times safely

### **Edge Cases**
1. **Empty hostnames** - devices with null/empty hostnames are skipped
2. **Special characters** - canonical keys handle most special characters
3. **Case sensitivity** - all matching is case-insensitive
4. **Domain variations** - only the first part of hostname is used for matching

---

## 📞 Troubleshooting

### **Common Issues**
1. **No matches found** - check if hostnames are present and properly formatted
2. **Too many exceptions** - verify data collection is working correctly
3. **Performance issues** - ensure database indexes are present and up-to-date
4. **Missing hostname exceptions** - if devices are missing their required hostname fields (ThreatLocker: `hostname`, Ninja: `systemName`), this indicates a critical data quality issue that must be resolved. Note that `computerName` is used for display purposes but is not required for device matching.

### **Debug Queries**
```sql
-- Check for devices without hostnames
SELECT vendor_id, COUNT(*) 
FROM device_snapshot 
WHERE snapshot_date = CURRENT_DATE 
  AND hostname IS NULL 
GROUP BY vendor_id;

-- Check canonical key distribution (UPDATED for clean hostnames)
SELECT 
    LOWER(LEFT(SPLIT_PART(SPLIT_PART(hostname,'|',1),'.',1),15)) as canonical_key,
    COUNT(*) as count
FROM device_snapshot 
WHERE snapshot_date = CURRENT_DATE 
  AND hostname IS NOT NULL
  AND vendor_id = 4  -- ThreatLocker only
GROUP BY canonical_key
HAVING COUNT(*) > 1
ORDER BY count DESC;

-- Check for data quality issues (pipe symbols in hostnames)
SELECT 
    vendor_id,
    COUNT(*) as devices_with_pipe_symbols
FROM device_snapshot 
WHERE snapshot_date = CURRENT_DATE 
  AND hostname LIKE '%|%'
GROUP BY vendor_id;

-- Check clean hostname extraction results
SELECT 
    hostname as original_hostname,
    LOWER(LEFT(SPLIT_PART(SPLIT_PART(hostname,'|',1),'.',1),15)) as clean_canonical_key,
    CASE 
        WHEN hostname LIKE '%|%' THEN 'Has pipe symbols'
        ELSE 'Clean'
    END as data_quality_status
FROM device_snapshot 
WHERE snapshot_date = CURRENT_DATE 
  AND vendor_id = 4  -- ThreatLocker vendor ID
  AND hostname IS NOT NULL
LIMIT 10;
```

---

## 🔧 Current Status (September 20, 2025)

### **System Status**
- ✅ **Cross-Vendor Field Mapping**: Resolved - All hostnames display clean (no pipe symbols)
- ✅ **Display Name Matching**: Fixed - ThreatLocker now uses computerName field for display_name to match Ninja format
- ✅ **ThreatLocker API**: Configured for full dataset collection (~400+ devices, updated daily at 02:31 AM)
- ✅ **Data Quality Monitoring**: Active validation and reporting
- ✅ **Variance Dashboard**: Displays professional, clean hostnames

### **Key Features**
- **Clean Hostname Extraction**: Automatically handles pipe symbols in ThreatLocker data
- **Data Quality Validation**: Monitors and reports field mapping violations
- **Comprehensive Collection**: Full dataset from all child organizations
- **Robust Error Handling**: Enhanced logging and debugging capabilities

---

**Related Documentation**:
- [DATABASE_ACCESS_GUIDE.md](./DATABASE_ACCESS_GUIDE.md) - Database connection and setup
- [AI_PROMPT_FOR_DASHBOARD.md](./AI_PROMPT_FOR_DASHBOARD.md) - Dashboard development guide
- [README.md](../README.md) - Project overview and variance reporting guidelines

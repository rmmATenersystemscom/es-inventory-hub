# ES Inventory Hub - Dashboard Integration Guide

## **For the Dashboard AI**

This guide provides everything the dashboard AI needs to integrate with the ES Inventory Hub system.

---

## **🚀 Quick Start - Two Options**

### **Option 1: Use the New API Server (Recommended)**

The ES Inventory Hub now includes a REST API server that provides clean endpoints for accessing variance data and triggering collectors.

**Start the API Server:**
```bash
cd /opt/es-inventory-hub
pip install -r api/requirements-api.txt
python3 api/api_server.py
```

**API Base URL:** `http://localhost:5400`

### **Option 2: Direct Database Access**

Connect directly to the PostgreSQL database using the connection details below.

---

## **📊 API Endpoints Reference**

### **System Status**
```bash
GET /api/status
# Returns overall system status, device counts, exception counts
```

### **Variance Reports**
```bash
GET /api/variance-report/latest
# Returns the latest variance report with all exception data

GET /api/variance-report/2025-09-21
# Returns variance report for a specific date (YYYY-MM-DD format)

GET /api/variance-report/filtered
# Returns filtered variance report in dashboard format (unresolved exceptions only)
# This endpoint provides the same data format as the Variances dashboard
# but uses Database AI's authoritative filtered data
```

### **Collector Management**
```bash
POST /api/collectors/run
# Trigger collector runs
# Body: {"collector": "both|ninja|threatlocker", "run_cross_vendor": true}

GET /api/collectors/status
# Check status of collector services
```

### **Exception Management**
```bash
GET /api/exceptions?type=MISSING_NINJA&resolved=false&limit=50
# Get exceptions with filtering options

POST /api/exceptions/123/resolve
# Mark an exception as resolved
# Body: {"resolved_by": "username", "notes": "Fixed in Ninja"}

POST /api/exceptions/123/mark-manually-fixed
# Mark an exception as manually fixed (NEW - Critical for variance management)
# Body: {
#   "updated_by": "dashboard_user",
#   "update_type": "display_name",
#   "old_value": {"display_name": "OLD_NAME"},
#   "new_value": {"display_name": "NEW_NAME"},
#   "notes": "Fixed display name mismatch"
# }

POST /api/exceptions/bulk-update
# Bulk exception operations (NEW - Efficient for multiple exceptions)
# Body: {
#   "exception_ids": [123, 124, 125],
#   "action": "mark_manually_fixed",
#   "updated_by": "dashboard_user",
#   "notes": "Bulk fix for display names"
# }

GET /api/exceptions/status-summary
# Get exception status summary with variance tracking (NEW)
# Returns: status counts, recent manual updates, variance status breakdown
```

### **Device Search (NEW - Handles Hostname Truncation)**
```bash
GET /api/devices/search?q=AEC-02739619435
# Search for devices across vendors with hostname truncation handling
# Query parameters:
#   - q: Search term (required)
#   - vendor: Optional filter ('ninja' or 'threatlocker')
#   - limit: Maximum results (default 50, max 200)

GET /api/devices/search?q=AEC-027396194353&vendor=threatlocker
# Search only in ThreatLocker for full hostname
```

### **Variance Management System (NEW - Critical Feature)**
```bash
# Mark device as manually fixed (solves the critical gap where dashboard updates
# ThreatLocker but database doesn't know about manual fixes)
POST /api/exceptions/{id}/mark-manually-fixed
# Body: {
#   "updated_by": "dashboard_user",
#   "update_type": "display_name",
#   "old_value": {"display_name": "AEC-02739619435"},
#   "new_value": {"display_name": "AEC-02739619435 | Updated"},
#   "notes": "Fixed display name mismatch"
# }

# Bulk operations for efficiency
POST /api/exceptions/bulk-update
# Body: {
#   "exception_ids": [123, 124, 125],
#   "action": "mark_manually_fixed",  # or "resolve", "reset_status"
#   "updated_by": "dashboard_user"
# }

# Get real-time variance status summary
GET /api/exceptions/status-summary
# Returns: {
#   "status_summary": {
#     "active": {"DISPLAY_NAME_MISMATCH": {"total": 972, "unresolved": 972}},
#     "manually_fixed": {"DISPLAY_NAME_MISMATCH": {"total": 5, "resolved": 5}}
#   },
#   "recent_manual_updates": [...],
#   "generated_at": "2025-09-23T02:33:08.654872"
# }
```

---

## **🔗 Database Connection (Direct Access)**

If you prefer direct database access:

**Connection String:**
```
postgresql://postgres:Xat162gT2Qsg4WDlO5r@localhost:5432/es_inventory_hub
```

**Key Tables:**
- `exceptions` - Variance data and cross-vendor discrepancies (ENHANCED with variance tracking)
- `device_snapshot` - Device inventory from both vendors
- `vendor` - Vendor information (Ninja, ThreatLocker)

**Enhanced Exceptions Table (NEW):**
- `manually_updated_at` - Timestamp when manually fixed
- `manually_updated_by` - User who performed the fix
- `update_type` - Type of update (display_name, hostname, etc.)
- `old_value` - JSONB of old values before fix
- `new_value` - JSONB of new values after fix
- `variance_status` - Status: 'active', 'manually_fixed', 'collector_verified', 'stale'

**Essential Queries:**
```sql
-- Get latest variance report
SELECT * FROM exceptions 
WHERE date_found = (
    SELECT MAX(date_found) FROM exceptions
) 
ORDER BY type, hostname;

-- Get exception counts by type
SELECT type, COUNT(*) as count 
FROM exceptions 
WHERE resolved = FALSE 
GROUP BY type;

-- Get device counts by vendor
SELECT v.name as vendor, COUNT(*) as count
FROM device_snapshot ds
JOIN vendor v ON ds.vendor_id = v.id
WHERE ds.snapshot_date = CURRENT_DATE
GROUP BY v.name;

-- NEW: Get variance status summary
SELECT 
    COALESCE(variance_status, 'active') as status,
    type,
    COUNT(*) as count,
    COUNT(CASE WHEN resolved = true THEN 1 END) as resolved_count
FROM exceptions
WHERE date_found >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY variance_status, type
ORDER BY status, type;

-- NEW: Get recent manual updates
SELECT 
    hostname,
    type,
    manually_updated_by,
    manually_updated_at,
    update_type,
    old_value,
    new_value
FROM exceptions
WHERE manually_updated_at >= CURRENT_DATE - INTERVAL '24 hours'
ORDER BY manually_updated_at DESC;

-- NEW: Search devices with hostname truncation handling
SELECT 
    v.name as vendor,
    ds.hostname,
    ds.display_name,
    LOWER(LEFT(SPLIT_PART(SPLIT_PART(ds.hostname,'|',1),'.',1),15)) as canonical_key
FROM device_snapshot ds
JOIN vendor v ON ds.vendor_id = v.id
WHERE ds.snapshot_date = CURRENT_DATE
  AND ds.hostname ILIKE 'AEC-02739619435%'
ORDER BY v.name, ds.hostname;
```

---

## **📋 Variance Report Data Structure**

### **Exception Types:**
- `MISSING_NINJA` - Devices in ThreatLocker but not in Ninja
- `DUPLICATE_TL` - Duplicate hostnames in ThreatLocker
- `SITE_MISMATCH` - Same device assigned to different sites
- `SPARE_MISMATCH` - Devices marked as spare in Ninja but still in ThreatLocker
- `DISPLAY_NAME_MISMATCH` - Same hostname but different display names between vendors

### **Sample API Response:**
```json
{
  "report_date": "2025-09-21",
  "data_status": {
    "status": "current",
    "message": "Data is current",
    "latest_date": "2025-09-21"
  },
  "summary": {
    "total_exceptions": 100,
    "unresolved_count": 100,
    "resolved_count": 0
  },
  "exception_counts": {
    "SPARE_MISMATCH": 73,
    "MISSING_NINJA": 26,
    "DUPLICATE_TL": 1
  },
  "exceptions_by_type": {
    "MISSING_NINJA": [
      {
        "id": 123,
        "hostname": "CHI-1P397H2 | SPARE - was Blake Thomas",
        "details": {
          "tl_hostname": "CHI-1P397H2 | SPARE - was Blake Thomas",
          "tl_org_name": "ChillCo",
          "tl_site_name": null
        },
        "resolved": false
      }
    ]
  }
}
```

---

## **🔄 Triggering Collectors**

### **Via API:**
```bash
# Run both collectors and cross-vendor checks
curl -X POST http://localhost:5400/api/collectors/run \
  -H "Content-Type: application/json" \
  -d '{"collector": "both", "run_cross_vendor": true}'

# Run only Ninja collector
curl -X POST http://localhost:5400/api/collectors/run \
  -H "Content-Type: application/json" \
  -d '{"collector": "ninja", "run_cross_vendor": false}'
```

### **Via Systemd (Direct):**
```bash
# Run Ninja collector
sudo systemctl start ninja-collector.service

# Run ThreatLocker collector
sudo systemctl start threatlocker-collector@rene.service
```

---

## **📁 Key Files for Dashboard Development**

**Essential Documentation:**
- `/opt/es-inventory-hub/docs/DATABASE_ACCESS_GUIDE.md` - Complete database guide
- `/opt/es-inventory-hub/docs/DASHBOARD_INTEGRATION_GUIDE.md` - Dashboard requirements
- `/opt/es-inventory-hub/docs/DEVICE_MATCHING_LOGIC.md` - Device matching logic

**API Server:**
- `/opt/es-inventory-hub/api/api_server.py` - REST API server
- `/opt/es-inventory-hub/api/requirements-api.txt` - Python dependencies

**Database Schema:**
- `/opt/es-inventory-hub/storage/schema.py` - SQLAlchemy models

---

## **🎯 Dashboard Requirements Summary**

### **Core Features:**
1. **Variance Status Dashboard** - Show current exception counts and types
2. **Exception Management** - View, filter, and resolve exceptions
3. **Data Freshness** - Display data status (current/stale/out_of_sync)
4. **Collector Controls** - Trigger manual collection runs
5. **Historical Analysis** - View variance reports for specific dates
6. **NEW: Real-time Variance Management** - Mark exceptions as manually fixed
7. **NEW: Bulk Operations** - Handle multiple exceptions efficiently
8. **NEW: Variance Status Tracking** - Show fix status and audit trail
9. **NEW: Hostname Truncation Search** - Find devices across vendors despite truncation

### **Data Status Handling:**
- **Current** (`status: "current"`) - Data is ≤1 day old, show normal report
- **Stale Data** (`status: "stale_data"`) - Data is >1 day old, show warning
- **Out of Sync** (`status: "out_of_sync"`) - No matching data between vendors

### **User Actions:**
- Refresh variance data
- Trigger collector runs
- Resolve exceptions
- Export reports
- Historical date selection
- **NEW: Mark exceptions as manually fixed** (critical for real-time variance management)
- **NEW: Bulk mark multiple exceptions as fixed**
- **NEW: Search devices with hostname truncation handling**
- **NEW: View variance status and audit trail**
- **NEW: Monitor recent manual updates**

---

## **🚨 Critical Hostname Truncation Issue (RESOLVED)**

### **Problem:**
- **Ninja**: Truncates hostnames to 15 characters (e.g., `AEC-02739619435`)
- **ThreatLocker**: Stores full hostnames up to 20 characters (e.g., `AEC-027396194353`)
- **Impact**: Users searching with Ninja hostnames couldn't find corresponding ThreatLocker devices

### **Solution:**
The new `/api/devices/search` endpoint handles this automatically:
- **Multi-strategy search**: Exact match, contains match, canonical key match, prefix match
- **Cross-vendor grouping**: Results grouped by canonical key to show related devices
- **Truncation detection**: Indicates when hostnames are truncated
- **Vendor filtering**: Optional vendor-specific searches

### **Usage:**
```bash
# Both of these will find the same device in both vendors:
GET /api/devices/search?q=AEC-02739619435      # Ninja format (truncated)
GET /api/devices/search?q=AEC-027396194353     # ThreatLocker format (full)
```

---

## **🔧 Setup Instructions for Dashboard AI**

### **1. Install Dependencies:**
```bash
cd /opt/es-inventory-hub
pip install -r api/requirements-api.txt
```

### **2. Start API Server:**
```bash
python3 api/api_server.py
```

### **3. Test API:**
```bash
# Basic endpoints
curl http://localhost:5400/api/health
curl http://localhost:5400/api/status
curl http://localhost:5400/api/variance-report/latest

# NEW: Test variance management endpoints
curl http://localhost:5400/api/exceptions/status-summary
curl "http://localhost:5400/api/devices/search?q=AEC-02739619435"

# NEW: Test manual fix endpoint (replace 123 with actual exception ID)
curl -X POST http://localhost:5400/api/exceptions/123/mark-manually-fixed \
  -H "Content-Type: application/json" \
  -d '{"updated_by": "test_user", "update_type": "display_name"}'
```

### **4. Build Dashboard:**
- Use Flask or your preferred web framework
- Connect to `http://localhost:5400` for API endpoints
- Or connect directly to PostgreSQL database
- Follow the design guidelines in this integration guide

---

## **📞 Support**

If you need help with integration:
1. Check the comprehensive documentation in `/opt/es-inventory-hub/docs/`
2. Test API endpoints using the examples above
3. Review the existing variance data structure
4. Use the provided SQL queries for direct database access

**The system is fully operational and ready for dashboard integration!** 🎉

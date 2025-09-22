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

**API Base URL:** `http://localhost:5500`

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
```

---

## **🔗 Database Connection (Direct Access)**

If you prefer direct database access:

**Connection String:**
```
postgresql://postgres:Xat162gT2Qsg4WDlO5r@localhost:5432/es_inventory_hub
```

**Key Tables:**
- `exceptions` - Variance data and cross-vendor discrepancies
- `device_snapshot` - Device inventory from both vendors
- `vendor` - Vendor information (Ninja, ThreatLocker)

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
curl -X POST http://localhost:5500/api/collectors/run \
  -H "Content-Type: application/json" \
  -d '{"collector": "both", "run_cross_vendor": true}'

# Run only Ninja collector
curl -X POST http://localhost:5500/api/collectors/run \
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
curl http://localhost:5500/api/health
curl http://localhost:5500/api/status
curl http://localhost:5500/api/variance-report/latest
```

### **4. Build Dashboard:**
- Use Flask or your preferred web framework
- Connect to `http://localhost:5500` for API endpoints
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

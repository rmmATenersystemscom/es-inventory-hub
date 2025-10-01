# ES Inventory Hub - Dashboard Integration Guide

**Complete guide for integrating with the ES Inventory Hub system - API endpoints, database access, and Variances Dashboard functionality.**

**Last Updated**: January 15, 2025  
**ES Inventory Hub Version**: v1.12.0  
**Status**: ✅ **FULLY OPERATIONAL**

---

## 🚀 **Quick Start - Two Integration Options**

### **Option 1: REST API Server (Recommended)**

The ES Inventory Hub includes a comprehensive REST API server with all Variances Dashboard functionality.

**Start the API Server:**
```bash
cd /opt/es-inventory-hub
pip install -r api/requirements-api.txt
python3 api/api_server.py
```

**API Base URL:** 
- **Production HTTPS**: `https://db-api.enersystems.com:5400` (Let's Encrypt Certificate)
- **Local Access**: `https://localhost:5400` (HTTPS)
- **IP Access**: `https://192.168.99.246:5400` (HTTPS - Use `-k` flag for testing)
- **HTTP Fallback**: `http://192.168.99.246:5400` (HTTP - Not recommended for production)

### **Option 2: Direct Database Access (Database AI Only)**

**⚠️ DASHBOARD AI SHOULD NEVER USE THIS OPTION!**

This is for Database AI internal operations only. Dashboard AI must use the API server.

**Connection Details (Database AI Internal Only):**
```
Host: 192.168.99.246 (Database AI Server)
Port: 5432
Database: es_inventory_hub
Username: postgres
Password: Xat162gT2Qsg4WDlO5r
```

**🚨 CRITICAL FOR DASHBOARD AI:**
- **Dashboard AI Server**: 192.168.99.245
- **Database AI Server**: 192.168.99.246
- **Dashboard AI MUST use**: `https://db-api.enersystems.com:5400` (HTTPS API server)
- **Dashboard AI MUST NOT use**: Port 5432 (direct database access)
- **HTTPS Required**: Mixed content security requires HTTPS for dashboard integration
- **Certificate**: Valid Let's Encrypt certificate for db-api.enersystems.com

---

## 📊 **COMPLETE API ENDPOINTS REFERENCE**

### **System Status & Health**
```bash
GET /api/health                    # Health check
GET /api/status                    # Overall system status with device counts
GET /api/collectors/status         # Collector service status
GET /api/collectors/history        # Collection history (last 10 runs)
GET /api/collectors/progress       # Real-time collection progress
```

### **Variance Reports & Analysis**
```bash
GET /api/variance-report/latest    # Latest variance report
GET /api/variance-report/{date}    # Specific date variance report
GET /api/variance-report/filtered  # Filtered report for dashboard (unresolved only)

# NEW: Historical Analysis
GET /api/variances/available-dates # Get available analysis dates
GET /api/variances/historical/{date} # Historical variance data
GET /api/variances/trends          # Trend analysis over time
```

### **Export Functionality (NEW)**
```bash
GET /api/variances/export/csv      # Export variance data to CSV
GET /api/variances/export/pdf      # Export variance data to PDF
GET /api/variances/export/excel    # Export variance data to Excel
```

### **Collector Management**
```bash
POST /api/collectors/run           # Trigger collector runs
# Body: {"collector": "both|ninja|threatlocker", "run_cross_vendor": true}
```

### **Exception Management**
```bash
GET /api/exceptions                # Get exceptions with filtering
GET /api/exceptions/status-summary # Exception status summary
POST /api/exceptions/{id}/resolve  # Mark exception as resolved
POST /api/exceptions/{id}/mark-manually-fixed # Mark as manually fixed
POST /api/exceptions/bulk-update   # Bulk exception operations
```

### **Device Search (Handles Hostname Truncation)**
```bash
GET /api/devices/search?q={hostname} # Search devices across vendors
```

---

## 🎯 **VARIANCES DASHBOARD FUNCTIONALITY**

### **✅ 1. RUN COLLECTORS BUTTON (⚡ Run Collectors)**

**Status**: ✅ **FULLY IMPLEMENTED**

**API Endpoints:**
- `POST /api/collectors/run` - Trigger manual data collection
- `GET /api/collectors/status` - Get real-time collection status  
- `GET /api/collectors/history` - Get collection history (last 10 runs)
- `GET /api/collectors/progress` - Get real-time collection progress

**Features:**
- ✅ Triggers both NinjaRMM and ThreatLocker data collection
- ✅ Returns collection job ID and estimated completion time
- ✅ Handles collection conflicts (if already running)
- ✅ Real-time status updates and progress tracking
- ✅ Collection history with timestamps and duration
- ✅ Integration with existing systemd services

**Usage Example:**
```javascript
// Trigger collectors
async function runCollectors() {
    const response = await fetch('/api/collectors/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            collector: 'both',
            run_cross_vendor: true
        })
    });
    return await response.json();
}

// Check status
async function getCollectorStatus() {
    const response = await fetch('/api/collectors/status');
    return await response.json();
}
```

### **✅ 2. HISTORICAL VIEW BUTTON (📅 Historical View)**

**Status**: ✅ **FULLY IMPLEMENTED**

**API Endpoints:**
- `GET /api/variances/available-dates` - Get available analysis dates
- `GET /api/variances/historical/{date}` - Get variance data for specific date
- `GET /api/variances/trends` - Get trend analysis over time

**Features:**
- ✅ List of dates where both Ninja and ThreatLocker have data
- ✅ Date range (earliest to latest available)
- ✅ Data quality status for each date
- ✅ Same structure as latest report but for historical dates
- ✅ Enhanced trend analysis with custom date ranges
- ✅ Variance trends over time with type breakdowns

**Usage Example:**
```javascript
// Get available dates
async function getAvailableDates() {
    const response = await fetch('/api/variances/available-dates');
    return await response.json();
}

// Get historical data
async function getHistoricalData(date) {
    const response = await fetch(`/api/variances/historical/${date}`);
    return await response.json();
}

// Get trends
async function getTrends(startDate, endDate) {
    const response = await fetch(`/api/variances/trends?start_date=${startDate}&end_date=${endDate}`);
    return await response.json();
}
```

### **✅ 3. EXPORT REPORT BUTTON (📊 Export Report)**

**Status**: ✅ **FULLY IMPLEMENTED**

**API Endpoints:**
- `GET /api/variances/export/csv` - Enhanced CSV export
- `GET /api/variances/export/pdf` - PDF report generation
- `GET /api/variances/export/excel` - Excel export with multiple sheets

**Features:**
- ✅ **CSV Export**: All variance data with metadata and filtering
- ✅ **PDF Export**: Comprehensive reports with executive summary, charts, and professional formatting
- ✅ **Excel Export**: Multi-sheet workbooks with summary and detailed data
- ✅ Support for filtering by variance type and date ranges
- ✅ Include device details and organization info
- ✅ Export metadata and timestamps
- ✅ Professional formatting and styling

**Usage Example:**
```javascript
// Export to CSV
async function exportCSV(date = 'latest', includeResolved = false) {
    const params = new URLSearchParams({
        date: date,
        include_resolved: includeResolved
    });
    const response = await fetch(`/api/variances/export/csv?${params}`);
    return await response.blob();
}

// Export to PDF
async function exportPDF(date = 'latest') {
    const response = await fetch(`/api/variances/export/pdf?date=${date}`);
    return await response.blob();
}

// Export to Excel
async function exportExcel(date = 'latest') {
    const response = await fetch(`/api/variances/export/excel?date=${date}`);
    return await response.blob();
}
```

---

## 🔗 **DATABASE SCHEMA & DIRECT ACCESS**

### **Primary Tables for Dashboard**

#### **`exceptions` Table (Enhanced)**
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

#### **`device_snapshot` Table**
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
    -- ... additional fields
);
```

### **Essential Database Queries**

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

-- Get variance status summary (NEW)
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

---

## 📋 **RESPONSE EXAMPLES**

### **System Status Response**
```json
{
  "data_status": {
    "status": "current",
    "message": "Data is current",
    "latest_date": "2025-01-15"
  },
  "device_counts": {
    "Ninja": 750,
    "ThreatLocker": 400
  },
  "exception_counts": {
    "SPARE_MISMATCH": 73,
    "MISSING_NINJA": 26,
    "DUPLICATE_TL": 1
  },
  "total_exceptions": 100
}
```

### **Available Dates Response**
```json
{
  "available_dates": [
    {
      "date": "2025-01-15",
      "ninja_devices": 750,
      "threatlocker_devices": 400,
      "total_exceptions": 100,
      "unresolved_exceptions": 85,
      "data_quality": "current",
      "days_old": 0
    }
  ],
  "date_range": {
    "earliest": "2025-01-01",
    "latest": "2025-01-15"
  }
}
```

### **Collection Status Response**
```json
{
  "ninja": {
    "status": "active",
    "last_run": "2025-01-15T02:10:00Z"
  },
  "threatlocker": {
    "status": "active", 
    "last_run": "2025-01-15T02:31:00Z"
  }
}
```

---

## 🔧 **SETUP INSTRUCTIONS**

### **1. Install Dependencies**
```bash
cd /opt/es-inventory-hub
pip install -r api/requirements-api.txt
```

### **2. Start API Server**
```bash
python3 api/api_server.py
```

### **3. Test API**
```bash
# Basic endpoints (from Dashboard AI server 192.168.99.245)
curl https://db-api.enersystems.com:5400/api/health
curl https://db-api.enersystems.com:5400/api/status
curl https://db-api.enersystems.com:5400/api/variance-report/latest

# NEW: Test Variances Dashboard endpoints
curl https://db-api.enersystems.com:5400/api/variances/available-dates
curl https://db-api.enersystems.com:5400/api/collectors/history
curl "https://db-api.enersystems.com:5400/api/variances/export/csv"

# Alternative IP access (use -k flag for testing)
curl -k https://192.168.99.246:5400/api/health
```

---

## 🎯 **DASHBOARD REQUIREMENTS SUMMARY**

### **Core Features:**
1. **Variance Status Dashboard** - Show current exception counts and types
2. **Exception Management** - View, filter, and resolve exceptions
3. **Data Freshness** - Display data status (current/stale/out_of_sync)
4. **Collector Controls** - Trigger manual collection runs
5. **Historical Analysis** - View variance reports for specific dates
6. **Export Functionality** - CSV, PDF, and Excel export capabilities
7. **Real-time Updates** - Live collection progress and status updates

### **Data Status Handling:**
- **Current** (`status: "current"`) - Data is ≤1 day old, show normal report
- **Stale Data** (`status: "stale_data"`) - Data is >1 day old, show warning
- **Out of Sync** (`status: "out_of_sync"`) - No matching data between vendors

### **User Actions:**
- Refresh variance data
- Trigger collector runs
- Resolve exceptions
- Export reports (CSV, PDF, Excel)
- Historical date selection
- Real-time progress monitoring

---

## 🚨 **CRITICAL HOSTNAME TRUNCATION ISSUE (RESOLVED)**

### **Problem:**
- **Ninja**: Truncates hostnames to 15 characters (e.g., `AEC-02739619435`)
- **ThreatLocker**: Stores full hostnames up to 20 characters (e.g., `AEC-027396194353`)
- **Impact**: Users searching with Ninja hostnames couldn't find corresponding ThreatLocker devices

### **Solution:**
The `/api/devices/search` endpoint handles this automatically:
- **Multi-strategy search**: Exact match, contains match, canonical key match, prefix match
- **Cross-vendor grouping**: Results grouped by canonical key to show related devices
- **Truncation detection**: Indicates when hostnames are truncated
- **Vendor filtering**: Optional vendor-specific searches

---

## 📞 **SUPPORT & TROUBLESHOOTING**

### **Common Issues**
1. **API Server Not Running**: Check if `python3 api/api_server.py` is running
2. **Database Connection Failed**: Verify PostgreSQL is running and accessible
3. **Export Dependencies Missing**: Install `pip install reportlab openpyxl xlsxwriter`
4. **Permission Denied**: Check systemd service permissions for collectors

### **Debug Commands**
```bash
# Check API server status (from Dashboard AI server 192.168.99.245)
curl -k https://192.168.99.246:5400/api/health

# Check database connection (from Dashboard AI server 192.168.99.245)
psql postgresql://postgres:Xat162gT2Qsg4WDlO5r@192.168.99.246:5432/es_inventory_hub

# Test collectors (from Dashboard AI server 192.168.99.245)
curl -k -X POST https://192.168.99.246:5400/api/collectors/run \
  -H "Content-Type: application/json" \
  -d '{"collector": "both", "run_cross_vendor": true}'
```

---

## 🔐 **HTTPS CONFIGURATION**

The API server now supports HTTPS to resolve mixed content errors when accessed from HTTPS dashboards.

### **Current SSL Setup:**
- **Let's Encrypt certificate**: Production-ready certificate for `db-api.enersystems.com`
- **HTTPS URL**: `https://db-api.enersystems.com:5400`
- **Certificate location**: `/opt/es-inventory-hub/ssl/api.crt`
- **Private key location**: `/opt/es-inventory-hub/ssl/api.key`
- **Certificate expires**: December 29, 2025 (auto-renewal configured)

### **Production SSL Setup (Let's Encrypt):**
```bash
# 1. Configure GoDaddy API credentials
nano /opt/es-inventory-hub/ssl/godaddy.ini

# 2. Run SSL setup script
cd /opt/es-inventory-hub/ssl
./setup_ssl.sh

# 3. Restart API server
sudo systemctl restart es-inventory-api.service
```

### **Testing HTTPS:**
```bash
# Test with Let's Encrypt certificate (production)
curl https://db-api.enersystems.com:5400/api/health

# Test main endpoint
curl https://db-api.enersystems.com:5400/api/variance-report/latest

# Test with IP address (use -k flag for testing)
curl -k https://192.168.99.246:5400/api/health
```

### **Firewall Configuration:**
- **Port 5400**: Allowed for HTTPS API access
- **Port 443**: Allowed for HTTPS traffic
- **Port 5432**: Blocked for Dashboard AI (database access)

---

## 📚 **ADDITIONAL RESOURCES**

### **Key Files**
- **API Server**: `/opt/es-inventory-hub/api/api_server.py`
- **Database Models**: `/opt/es-inventory-hub/storage/schema.py`
- **Configuration**: `/opt/es-inventory-hub/common/config.py`

### **Documentation**
- **Main README**: `/opt/es-inventory-hub/README.md`
- **Device Matching Logic**: `/opt/es-inventory-hub/docs/DEVICE_MATCHING_LOGIC.md`
- **API Quick Reference**: `/opt/es-inventory-hub/docs/API_QUICK_REFERENCE.md`

---

**🎉 The ES Inventory Hub system is fully operational and ready for dashboard integration with complete Variances Dashboard functionality!**
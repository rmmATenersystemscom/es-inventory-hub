# API Integration Guide for Dashboard AI

**Complete API reference for Dashboard AI to integrate with the Database AI's ES Inventory Hub system.**

**Last Updated**: October 2, 2025  
**ES Inventory Hub Version**: v1.15.0  
**Status**: ✅ **FULLY OPERATIONAL**

---

## 🚀 **Quick Start**

### **Connection Information**
- **Your Server**: 192.168.99.245 (Dashboard AI)
- **Database AI Server**: 192.168.99.246 (API Server)
- **NEVER use localhost** - Dashboard AI has no local API server
- **ALWAYS use external URLs** to connect to Database AI's API server

### **API Base URLs**
- **Production HTTPS**: `https://db-api.enersystems.com:5400` (Let's Encrypt Certificate) ✅ **RECOMMENDED**
- **IP Access**: `https://192.168.99.246:5400` (HTTPS - Use `-k` flag for testing) ✅ **ALTERNATIVE**

### **Authentication**
- **No authentication required** for current endpoints
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
GET /api/variance-report/latest    # Latest variance report (ENHANCED with by_organization data)
GET /api/variance-report/{date}    # Specific date variance report
GET /api/variance-report/filtered  # Filtered report for dashboard (unresolved only)

# Historical Analysis
GET /api/variances/available-dates # Get available analysis dates
GET /api/variances/historical/{date} # Historical variance data (ENHANCED with by_organization data)
GET /api/variances/trends          # Trend analysis over time
```

### **Export Functionality**
```bash
GET /api/variances/export/csv      # Export variance data to CSV (ENHANCED with variance_type parameter)
GET /api/variances/export/pdf      # Export variance data to PDF (ENHANCED with variance_type parameter)
GET /api/variances/export/excel    # Export variance data to Excel (ENHANCED with variance_type parameter)
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

### **Device Search**
```bash
GET /api/devices/search?q={hostname} # Search devices across vendors
```

### **Windows 11 24H2 Assessment**
```bash
GET /api/windows-11-24h2/status        # Windows 11 24H2 compatibility status summary
GET /api/windows-11-24h2/incompatible  # List of incompatible devices with deficiencies
GET /api/windows-11-24h2/compatible    # List of compatible devices with passed requirements
POST /api/windows-11-24h2/run          # Manually trigger Windows 11 24H2 assessment
```

---

## 🎯 **DASHBOARD FUNCTIONALITY**

### **✅ 1. RUN COLLECTORS BUTTON (⚡ Run Collectors)**

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

**Usage Example:**
```javascript
// Trigger collectors
async function runCollectors() {
    const response = await fetch('https://db-api.enersystems.com:5400/api/collectors/run', {
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
    const response = await fetch('https://db-api.enersystems.com:5400/api/collectors/status');
    return await response.json();
}
```

### **✅ 2. HISTORICAL VIEW BUTTON (📅 Historical View)**

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

**Usage Example:**
```javascript
// Get available dates
async function getAvailableDates() {
    const response = await fetch('https://db-api.enersystems.com:5400/api/variances/available-dates');
    return await response.json();
}

// Get historical data
async function getHistoricalData(date) {
    const response = await fetch(`https://db-api.enersystems.com:5400/api/variances/historical/${date}`);
    return await response.json();
}
```

### **✅ 3. EXPORT REPORT BUTTON (📊 Export Report)**

**API Endpoints:**
- `GET /api/variances/export/csv` - Enhanced CSV export with variance_type filtering
- `GET /api/variances/export/pdf` - PDF report generation with variance_type filtering
- `GET /api/variances/export/excel` - Excel export with multiple sheets and variance_type filtering

**Enhanced Features:**
- ✅ **CSV Export**: All variance data with metadata and filtering by variance type
- ✅ **PDF Export**: Comprehensive reports with executive summary, charts, and professional formatting
- ✅ **Excel Export**: Multi-sheet workbooks with summary and detailed data
- ✅ **NEW**: Support for filtering by specific variance types (`variance_type` parameter)
- ✅ Include device details and organization info
- ✅ Export metadata and timestamps
- ✅ Professional formatting and styling

**Usage Example:**
```javascript
// Export specific variance type to CSV
async function exportCSVByType(varianceType = 'all', date = 'latest', includeResolved = false) {
    const params = new URLSearchParams({
        date: date,
        include_resolved: includeResolved,
        variance_type: varianceType
    });
    const response = await fetch(`https://db-api.enersystems.com:5400/api/variances/export/csv?${params}`);
    return await response.blob();
}

// Supported variance types
const VARIANCE_TYPES = {
    ALL: 'all',
    MISSING_IN_NINJA: 'missing_in_ninja',
    THREATLOCKER_DUPLICATES: 'threatlocker_duplicates',
    NINJA_DUPLICATES: 'ninja_duplicates',
    DISPLAY_NAME_MISMATCHES: 'display_name_mismatches'
};
```

### **✅ 4. WINDOWS 11 24H2 ASSESSMENT (🪟 Compatibility Analysis)**

**API Endpoints:**
- `GET /api/windows-11-24h2/status` - Compatibility status summary with counts and rates
- `GET /api/windows-11-24h2/incompatible` - List of incompatible devices with detailed deficiencies
- `GET /api/windows-11-24h2/compatible` - List of compatible devices with passed requirements
- `POST /api/windows-11-24h2/run` - Manually trigger Windows 11 24H2 assessment

**Features:**
- ✅ **Automatic Assessment**: Runs 45 minutes after Ninja collector completion
- ✅ **Comprehensive Requirements**: CPU (Intel 8th gen+, AMD Zen 2+), TPM 2.0, Secure Boot, Memory (≥4GB), Storage (≥64GB), 64-bit OS
- ✅ **Detailed Deficiency Reporting**: Specific reasons why devices fail requirements with remediation suggestions
- ✅ **Organization Breakdown**: Incompatible devices grouped by organization
- ✅ **Real-time Status**: Current compatibility rates and assessment status
- ✅ **Hardware Information**: Includes `cpu_model` and `last_contact` fields for detailed device information

### **Date Field Distinctions:**
- **`last_contact`**: When the device was last online/active (from Ninja RMM)
- **`last_update`**: When we last updated this device record in our database  
- **`assessment_date`**: When the Windows 11 24H2 compatibility assessment was performed

**Usage Example:**
```javascript
// Get Windows 11 24H2 compatibility status
async function getWindows11Status() {
    const response = await fetch('https://db-api.enersystems.com:5400/api/windows-11-24h2/status');
    return await response.json();
}

// Get incompatible devices with deficiencies
async function getIncompatibleDevices() {
    const response = await fetch('https://db-api.enersystems.com:5400/api/windows-11-24h2/incompatible');
    return await response.json();
}

// Manually trigger Windows 11 24H2 assessment
async function runWindows11Assessment() {
    const response = await fetch('https://db-api.enersystems.com:5400/api/windows-11-24h2/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    });
    return await response.json();
}
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

### **Variance Report Response**
```json
{
  "report_date": "2025-10-02",
  "data_status": {
    "status": "current",
    "message": "Data is current",
    "latest_date": "2025-10-02"
  },
  "summary": {
    "total_exceptions": 100,
    "unresolved_count": 85,
    "resolved_count": 15
  },
  "missing_in_ninja": {
    "total_count": 2,
    "by_organization": {
      "Organization A": [
        {
          "hostname": "device1",
          "vendor": "ThreatLocker",
          "display_name": "Device 1",
          "organization": "Organization A",
          "billing_status": "active",
          "action": "Investigate"
        }
      ]
    }
  }
}
```

### **Windows 11 24H2 Status Response**
```json
{
  "total_windows_devices": 1232,
  "compatible_devices": 856,
  "incompatible_devices": 376,
  "not_assessed_devices": 0,
  "compatibility_rate": 69.5,
  "last_assessment": "2025-10-02T23:45:00Z"
}
```

### **Manual Trigger Response**
```json
{
  "status": "success",
  "message": "Windows 11 24H2 assessment completed successfully",
  "output": "2025-10-02 19:52:31,441 - INFO - Assessment complete:\n  - Total devices assessed: 634\n  - Compatible devices: 296\n  - Incompatible devices: 338\n  - Compatibility rate: 46.7%",
  "timestamp": "2025-10-03T00:52:31Z"
}
```

---

## 🔧 **TESTING COMMANDS**

### **Basic Endpoints**
```bash
# Health check
curl https://db-api.enersystems.com:5400/api/health

# System status
curl https://db-api.enersystems.com:5400/api/status

# Latest variance report
curl https://db-api.enersystems.com:5400/api/variance-report/latest
```

### **Enhanced Endpoints**
```bash
# Available dates
curl https://db-api.enersystems.com:5400/api/variances/available-dates

# Historical data
curl https://db-api.enersystems.com:5400/api/variances/historical/2025-10-01

# Export with filtering
curl "https://db-api.enersystems.com:5400/api/variances/export/csv?variance_type=missing_in_ninja&date=latest&include_resolved=false"
```

### **Windows 11 24H2 Endpoints**
```bash
# Status
curl https://db-api.enersystems.com:5400/api/windows-11-24h2/status

# Incompatible devices
curl https://db-api.enersystems.com:5400/api/windows-11-24h2/incompatible

# Manual trigger
curl -X POST https://db-api.enersystems.com:5400/api/windows-11-24h2/run
```

### **Collector Management**
```bash
# Trigger collectors
curl -X POST https://db-api.enersystems.com:5400/api/collectors/run \
  -H "Content-Type: application/json" \
  -d '{"collector": "both", "run_cross_vendor": true}'

# Check status
curl https://db-api.enersystems.com:5400/api/collectors/status
```

---

## 🚨 **CRITICAL NOTES FOR DASHBOARD AI**

### **Connection Requirements**
- **ALWAYS use HTTPS URLs** - Never use HTTP
- **Use production URL**: `https://db-api.enersystems.com:5400` (recommended)
- **Certificate**: Valid Let's Encrypt certificate (no `-k` flag needed for production)
- **IP Access**: Use `-k` flag only for testing with IP addresses

### **Data Status Handling**
- **Current** (`status: "current"`) - Data is ≤1 day old, show normal report
- **Stale Data** (`status: "stale_data"`) - Data is >1 day old, show warning
- **Out of Sync** (`status: "out_of_sync"`) - No matching data between vendors

### **Error Handling**
- All endpoints return JSON responses
- Check HTTP status codes (200 = success, 4xx = client error, 5xx = server error)
- Error responses include `error` field with details

---

## 📚 **RELATED DOCUMENTATION**

- [Variances Dashboard Guide](./VARIANCES_DASHBOARD_GUIDE.md) - Detailed dashboard functionality
- [Windows 11 24H2 Guide](./WINDOWS_11_24H2_GUIDE.md) - Windows 11 compatibility assessment
- [Setup and Troubleshooting Guide](./SETUP_AND_TROUBLESHOOTING.md) - Operational guide
- [Database Schema Guide](./DATABASE_SCHEMA_GUIDE.md) - Database reference

---

**🎉 The ES Inventory Hub API is fully operational and ready for Dashboard AI integration!**

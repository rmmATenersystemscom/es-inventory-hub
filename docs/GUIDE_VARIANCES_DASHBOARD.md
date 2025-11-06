# Variances Dashboard Guide

**Complete guide for Variances Dashboard functionality, enhanced API capabilities, and modal functionality.**

**Last Updated**: November 5, 2025  
**ES Inventory Hub Version**: v1.19.10  
**Status**: ✅ **FULLY OPERATIONAL**

---

## 🔧 **Hostname Usage Guidelines**

### **Critical: Use Correct Hostname for Vendor API Calls**

When updating device information, **each vendor system requires its own hostname format**.

**✅ CORRECT Usage:**
- **ThreatLocker Portal API**: Use `threatlocker_hostname` field
- **NinjaRMM API**: Use `ninja_hostname` field
- **Device Updates**: Use the appropriate vendor hostname for each system

**❌ INCORRECT Usage:**
- **Never use** `ninja_hostname` for ThreatLocker Portal API calls
- **Never use** `threatlocker_hostname` for NinjaRMM API calls
- **Never assume** hostnames are interchangeable between systems

**Example from Display Name Mismatches:**
```json
{
  "hostname": "nochi-002062482",                    // Base identifier
  "ninja_hostname": "NOCHI-002062482",             // Use for NinjaRMM API
  "threatlocker_hostname": "NOCHI-002062482753",   // Use for ThreatLocker Portal API (automatically cleaned, ready for API calls)
  "ninja_display_name": "NOCHI-002062482753 | SPARE - was Maintenance (at ES)",
  "threatlocker_display_name": "NOCHI-002062482753 | Maintenance"
}
```

**⚠️ Common Issue**: Dashboard must use `threatlocker_hostname` when calling ThreatLocker Portal API for device updates.

**📋 Hostname Format Guarantee (v1.19.9+):**
- The `threatlocker_hostname` field is **automatically cleaned** before being returned in API responses
- Clean hostnames are guaranteed to work with ThreatLocker API's `find_computer_by_hostname()` function
- Cleaning removes pipe symbols (`|`) and domain suffixes (`.local`, `.domain`, etc.) that may be present in stored data
- Original case is preserved (ThreatLocker API does case-insensitive search)
- **No manual cleaning required** - use the hostname directly from the API response

---

## 🚀 **ENHANCED API CAPABILITIES (OCTOBER 2025)**

### **Enhanced Variance Report Structure**
The main variance report endpoints now include detailed `by_organization` data structure:

**Enhanced Response Format:**
```json
{
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
  },
  "threatlocker_duplicates": {
    "total_count": 4,
    "by_organization": { ... }
  },
  "ninja_duplicates": {
    "total_count": 45,
    "by_organization": { ... }
  },
  "display_name_mismatches": {
    "total_count": 87,
    "by_organization": { ... }
  }
}
```

### **Enhanced Export Parameters**
Export endpoints now support the `variance_type` parameter for filtering:

**Supported Parameters:**
- `date`: `latest`, `today`, `yesterday`, or specific date (YYYY-MM-DD)
- `include_resolved`: `true`/`false` - whether to include resolved exceptions
- `variance_type`: `all`, `missing_in_ninja`, `threatlocker_duplicates`, `ninja_duplicates`, `display_name_mismatches`

**Example Usage:**
```bash
# Export only missing in Ninja variances
GET /api/variances/export/csv?variance_type=missing_in_ninja&date=latest&include_resolved=false

# Export all variance types for specific date
GET /api/variances/export/pdf?date=2025-10-01&include_resolved=true

# Export Excel with all data
GET /api/variances/export/excel?variance_type=all&date=latest
```

### **Enhanced Historical Data**
Historical endpoints now provide the same detailed organization breakdown:

```bash
# Get historical data with organization breakdown
GET /api/variances/historical/2025-10-01

# Get trends with enhanced filtering
GET /api/variances/trends?start_date=2025-09-01&end_date=2025-10-02&type=missing_in_ninja
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
    const response = await fetch('https://db-api.enersystems.com:5400/api/variances/available-dates');
    return await response.json();
}

// Get historical data
async function getHistoricalData(date) {
    const response = await fetch(`https://db-api.enersystems.com:5400/api/variances/historical/${date}`);
    return await response.json();
}

// Get trends
async function getTrends(startDate, endDate) {
    const response = await fetch(`https://db-api.enersystems.com:5400/api/variances/trends?start_date=${startDate}&end_date=${endDate}`);
    return await response.json();
}
```

### **✅ 3. EXPORT REPORT BUTTON (📊 Export Report)**

**Status**: ✅ **FULLY IMPLEMENTED & ENHANCED**

**API Endpoints:**
- `GET /api/variances/export/csv` - Enhanced CSV export with variance_type filtering
- `GET /api/variances/export/pdf` - PDF report generation with variance_type filtering
- `GET /api/variances/export/excel` - Excel export with multiple sheets and variance_type filtering

**Enhanced Features:**
- ✅ **CSV Export**: All variance data with metadata and filtering by variance type
- ✅ **PDF Export**: Comprehensive reports with executive summary, charts, and professional formatting
- ✅ **Excel Export**: Multi-sheet workbooks with summary and detailed data
- ✅ **NEW**: Support for filtering by specific variance types (`variance_type` parameter)
- ✅ **NEW**: Enhanced parameter support (`variance_type` instead of `type`)
- ✅ Include device details and organization info
- ✅ Export metadata and timestamps
- ✅ Professional formatting and styling
- ✅ **NEW**: Backward compatibility with existing `type` parameter

**Enhanced Usage Examples:**
```javascript
// Export specific variance type to CSV
async function exportCSVByType(varianceType = 'all', date = 'latest', includeResolved = false) {
    const params = new URLSearchParams({
        date: date,
        include_resolved: includeResolved,
        variance_type: varianceType  // NEW: Enhanced parameter
    });
    const response = await fetch(`https://db-api.enersystems.com:5400/api/variances/export/csv?${params}`);
    return await response.blob();
}

// Export to PDF with variance type filtering
async function exportPDFByType(varianceType = 'all', date = 'latest') {
    const params = new URLSearchParams({
        date: date,
        variance_type: varianceType  // NEW: Enhanced parameter
    });
    const response = await fetch(`https://db-api.enersystems.com:5400/api/variances/export/pdf?${params}`);
    return await response.blob();
}

// Export to Excel with enhanced filtering
async function exportExcelByType(varianceType = 'all', date = 'latest', includeResolved = false) {
    const params = new URLSearchParams({
        date: date,
        include_resolved: includeResolved,
        variance_type: varianceType  // NEW: Enhanced parameter
    });
    const response = await fetch(`https://db-api.enersystems.com:5400/api/variances/export/excel?${params}`);
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

### **✅ 4. ENHANCED MODAL FUNCTIONALITY (📋 Detailed Views)**

**Status**: ✅ **FULLY IMPLEMENTED & ENHANCED**

**New Capability**: Complete modal functionality with detailed device breakdowns by organization.

**Enhanced API Response Structure:**
```json
{
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
      ],
      "Organization B": [
        {
          "hostname": "device2",
          "vendor": "ThreatLocker", 
          "display_name": "Device 2",
          "organization": "Organization B",
          "billing_status": "active",
          "action": "Investigate"
        }
      ]
    }
  }
}
```

**Enhanced Features:**
- ✅ **Complete Modal Data**: Detailed device breakdowns by organization
- ✅ **Device Information**: Hostname, vendor, display name, organization, billing status
- ✅ **Action Items**: Clear action recommendations for each device
- ✅ **Organization Grouping**: Devices grouped by organization for easy management
- ✅ **Historical Support**: Same detailed structure for historical data
- ✅ **Export Integration**: Modal data included in all export formats

**Usage Example:**
```javascript
// Get enhanced variance report with organization breakdown
async function getEnhancedVarianceReport() {
    const response = await fetch('https://db-api.enersystems.com:5400/api/variance-report/latest');
    const data = await response.json();
    
    // Access detailed organization data
    const missingInNinja = data.missing_in_ninja;
    console.log(`Total missing in Ninja: ${missingInNinja.total_count}`);
    
    // Iterate through organizations
    Object.entries(missingInNinja.by_organization).forEach(([orgName, devices]) => {
        console.log(`Organization: ${orgName} has ${devices.length} devices`);
        devices.forEach(device => {
            console.log(`- ${device.hostname} (${device.vendor}) - ${device.action}`);
        });
    });
    
    return data;
}

// Get historical data with same structure
async function getHistoricalVarianceReport(date) {
    const response = await fetch(`https://db-api.enersystems.com:5400/api/variances/historical/${date}`);
    return await response.json();
}
```

---

## 🔧 **DATA QUALITY FIXES IMPLEMENTED**

### **Missing in Ninja Organization Fix**
- **Issue**: Organization field showing "Unknown" instead of actual ThreatLocker organization names
- **Solution**: Enhanced `get_organization_breakdown` function to extract organization data from `details` JSONB field
- **Result**: ✅ **FIXED** - Now shows correct organization names like "Doctors' Exchange, Inc." and "Insurance Shield"

### **ThreatLocker Duplicates Organization Fix**
- **Issue**: Organization field showing "Unknown" instead of actual ThreatLocker organization names
- **Solution**: 
  - Enhanced `check_duplicate_tl` function to collect and store organization data in `details` JSONB field
  - Updated `get_organization_breakdown` function to extract organization data for ThreatLocker Duplicates
- **Result**: ✅ **FIXED** - Now shows correct organization names like "BFM Corp LLC", "Ener Systems", and "Gulf South Engineering and Testing Inc."

### **DevicesThatShouldNotHaveThreatlocker Organization Fix**
- **Issue**: Organization field showing "Unknown" for 44 out of 45 devices instead of actual organization names
- **Solution**: 
  - Enhanced `check_spare_mismatch` function to collect and store organization data from both Ninja and ThreatLocker in `details` JSONB field
  - Updated `get_organization_breakdown` function to extract organization data for DevicesThatShouldNotHaveThreatlocker with preference for Ninja organization data
- **Result**: ✅ **FIXED** - Now shows correct organization names like "ChillCo", "Ener Systems", "BFM Corp LLC", "Quality Plumbing", and many more

---

## 📋 **RESPONSE EXAMPLES**

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

### **Enhanced Export Response**
```json
{
  "export_type": "csv",
  "variance_type": "missing_in_ninja",
  "date": "latest",
  "include_resolved": false,
  "total_records": 2,
  "file_size": "1.2KB",
  "download_url": "/api/variances/export/csv?variance_type=missing_in_ninja&date=latest&include_resolved=false"
}
```

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

## 📚 **RELATED DOCUMENTATION**

- [API Integration Guide](./API_INTEGRATION.md) - Core API endpoints and usage
- [Windows 11 24H2 Guide](./GUIDE_WINDOWS_11_24H2.md) - Windows 11 compatibility assessment
- [Setup and Troubleshooting Guide](./TROUBLESHOOT_SETUP.md) - Operational guide
- [Database Schema Guide](./GUIDE_DATABASE_SCHEMA.md) - Database reference

---

**🎉 The Variances Dashboard functionality is fully operational and ready for Dashboard AI integration!**

---

**Version**: v1.19.10  
**Last Updated**: November 5, 2025 02:00 UTC  
**Maintainer**: ES Inventory Hub Team

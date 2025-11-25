# API Integration Guide for Dashboard AI

**Complete API reference for Dashboard AI to integrate with the Database AI's ES Inventory Hub system.**

**Last Updated**: November 25, 2025
**ES Inventory Hub Version**: v1.24.0
**Status**: ✅ **FULLY OPERATIONAL**

> **📅 API Behavior Update (October 9, 2025)**: All status and exception endpoints now return **latest data only** (current date) instead of historical ranges. This ensures consistent reporting and prevents data accumulation issues.

---

## 🔧 **Hostname Usage Guidelines**

### **Critical: Use Correct Hostname for Each Vendor System**

When working with device data, **each vendor system requires its own hostname format**. The API provides the correct hostname for each system.

**✅ CORRECT Usage:**
- **For ThreatLocker Portal API calls**: Use `threatlocker_hostname` field
- **For NinjaRMM API calls**: Use `ninja_hostname` field
- **For device identification**: Use the appropriate vendor hostname

**❌ INCORRECT Usage:**
- **Never use** `ninja_hostname` for ThreatLocker Portal API calls
- **Never use** `threatlocker_hostname` for NinjaRMM API calls
- **Never assume** hostnames are interchangeable between systems

**Example from Variance Report:**
```json
{
  "hostname": "nochi-002062482",                    // Base identifier
  "ninja_hostname": "NOCHI-002062482",             // Use for NinjaRMM API
  "threatlocker_hostname": "NOCHI-002062482753",   // Use for ThreatLocker Portal API (cleaned, ready for API calls)
  "ninja_display_name": "NOCHI-002062482753 | SPARE - was Maintenance (at ES)",
  "threatlocker_display_name": "NOCHI-002062482753 | Maintenance"
}
```

**⚠️ Common Issue**: Dashboard AI must use `threatlocker_hostname` when calling ThreatLocker Portal API, not `ninja_hostname`.

**📋 Hostname Format Guarantee:**
- The `threatlocker_hostname` field is **automatically cleaned** before being returned in API responses
- Clean hostnames are guaranteed to work with ThreatLocker API's `find_computer_by_hostname()` function
- Cleaning removes pipe symbols (`|`) and domain suffixes (`.local`, `.domain`, etc.) that may be present in stored data
- Original case is preserved (ThreatLocker API does case-insensitive search, but case is maintained for consistency)
- **No manual cleaning required** - the API returns hostnames in the exact format ThreatLocker API expects

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
- **Variance/Status Endpoints**: No authentication required
- **QBR Endpoints**: Microsoft 365 OAuth required (see QBR section below)
- **HTTPS Required**: Mixed content security requires HTTPS for dashboard integration
- **Certificate**: Valid Let's Encrypt certificate for db-api.enersystems.com

---

## 📊 **COMPLETE API ENDPOINTS REFERENCE**

### **System Status & Health**
```bash
GET /api/health                    # Health check
GET /api/status                    # Overall system status with device counts, vendor freshness, and collector health (ENHANCED - auto-cleans stale jobs)
GET /api/collectors/status         # Collector service status
GET /api/collectors/history        # Collection history (last 10 runs)
GET /api/collectors/progress       # Real-time collection progress (ENHANCED - auto-cleans stale jobs, includes process_running status)
POST /api/collectors/cleanup-stale # Manually trigger cleanup of stale running jobs
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

### **Collector Management (ENHANCED)**
```bash
POST /api/collectors/run           # Trigger collector runs (ENHANCED: Runs collectors independently, continues even if one fails)
# Body: {"collectors": ["ninja", "threatlocker"], "run_cross_vendor": true}
# Note: Collectors now run independently - if one fails, others continue
# Response includes detailed status for each collector
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

### **QBR (Quarterly Business Review) Metrics** 🔐
**⚠️ Authentication Required**: All QBR endpoints require Microsoft 365 OAuth authentication.

```bash
# Authentication
GET /api/auth/microsoft/login          # Initiate OAuth login (redirects to Microsoft)
GET /api/auth/microsoft/callback       # OAuth callback (internal use)
GET /api/auth/status                   # Check if user is authenticated
POST /api/auth/logout                  # Logout and clear session

# Monthly Metrics
GET /api/qbr/metrics/monthly           # Raw monthly metrics
    ?period=YYYY-MM                    # Optional: specific month (default: latest)
    &organization_id=1                 # Optional: organization filter (default: 1)
    &vendor_id=1                       # Optional: vendor filter
    &metric_name=seats_managed         # Optional: specific metric

# Quarterly Metrics (Aggregated)
GET /api/qbr/metrics/quarterly         # Aggregated quarterly metrics
    ?period=YYYY-Q1                    # Optional: specific quarter (default: latest)
    &organization_id=1                 # Optional: organization filter

# Device Counts by Client (NEW)
GET /api/qbr/metrics/devices-by-client # Seats and endpoints per client
    ?period=YYYY-MM                    # Required: month to query
    &organization_id=1                 # Optional: organization filter

# SmartNumbers (KPIs)
GET /api/qbr/smartnumbers              # Calculated KPIs for quarterly review
    ?period=YYYY-Q1                    # Required: quarter
    &organization_id=1                 # Optional: organization filter

# Performance Thresholds
GET /api/qbr/thresholds                # Get threshold definitions (green/yellow/red zones)
    ?organization_id=1                 # Optional: organization filter
POST /api/qbr/thresholds               # Update threshold definitions

# Manual Data Entry
POST /api/qbr/metrics/manual           # Manually enter or update metrics
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
// 1. Trigger collectors
const response = await fetch('https://db-api.enersystems.com:5400/api/collectors/run', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ 
    collectors: ['ninja', 'threatlocker'],
    run_cross_vendor: true 
  })
});
const { batch_id } = await response.json();

// 2. Poll for progress
const pollStatus = async (batchId) => {
  const response = await fetch(`https://db-api.enersystems.com:5400/api/collectors/runs/batch/${batchId}`);
  const data = await response.json();
  
  // Update UI with real-time progress
  updateProgressUI(data);
  
  // Stop polling when complete
  if (['completed', 'failed', 'cancelled'].includes(data.status)) {
    return;
  }
  
  // Continue polling every 5-10 seconds
  setTimeout(() => pollStatus(batchId), 5000);
};

// 3. Update UI with progress
function updateProgressUI(data) {
  // Update batch status
  document.getElementById('batch-status').textContent = 
    `${data.status} (${data.progress_percent}%)`;
  
  // Update individual jobs
  data.collectors.forEach(job => {
    const jobElement = document.getElementById(`job-${job.job_id}`);
    if (jobElement) {
      jobElement.querySelector('.progress').style.width = `${job.progress_percent}%`;
      jobElement.querySelector('.message').textContent = job.message;
    }
  });
}

// Implementation Tips:
// - Poll every 5-10 seconds (not more frequent)
// - Stop polling when status is 'completed', 'failed', or 'cancelled'
// - Show progress bars using progress_percent field
// - Display messages using message field for user feedback
// - Handle errors gracefully - check for error field
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
- ✅ **Hardware Information**: Includes `cpu_model`, `last_contact`, `system_manufacturer`, and `system_model` fields for detailed device information

**⚠️ CRITICAL: Manual Trigger Behavior**
- The `POST /api/windows-11-24h2/run` endpoint runs **SYNCHRONOUSLY** and blocks until completion
- Assessment typically takes **2-5 minutes** to process all Windows devices (600+ devices)
- **You MUST set a long timeout** (minimum 300 seconds / 5 minutes) when calling this endpoint
- The endpoint will return a JSON response with `status`, `message`, `output`, and `timestamp` fields
- If the request times out, the assessment may still be running on the server - check status endpoint to verify

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
// ⚠️ IMPORTANT: This endpoint runs SYNCHRONOUSLY and can take 2-5 minutes to complete
// The assessment processes all Windows devices (typically 600+ devices)
// You MUST set a long timeout (at least 300 seconds / 5 minutes)
async function runWindows11Assessment() {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 300000); // 5 minute timeout
    
    try {
        const response = await fetch('https://db-api.enersystems.com:5400/api/windows-11-24h2/run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            signal: controller.signal
        });
        clearTimeout(timeoutId);
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `Assessment failed: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        clearTimeout(timeoutId);
        if (error.name === 'AbortError') {
            throw new Error('Assessment request timed out after 5 minutes. The assessment may still be running on the server.');
        }
        throw error;
    }
}
```

### **✅ 5. QBR DASHBOARD (📊 Quarterly Business Review)**

**API Endpoints:**
- `GET /api/auth/status` - Check authentication status
- `GET /api/auth/microsoft/login` - Initiate Microsoft OAuth login
- `GET /api/qbr/metrics/monthly` - Get monthly metrics
- `GET /api/qbr/metrics/quarterly` - Get quarterly aggregated metrics
- `GET /api/qbr/metrics/devices-by-client` - Get per-client seat and endpoint counts
- `GET /api/qbr/smartnumbers` - Get calculated KPIs

**Features:**
- ✅ Microsoft 365 OAuth authentication
- ✅ Monthly and quarterly metric tracking
- ✅ Per-client seat and endpoint counts
- ✅ SmartNumbers/KPI calculations
- ✅ Configurable performance thresholds

**⚠️ CRITICAL: Authentication Required**
All QBR endpoints require authentication. You must:
1. Check auth status first
2. Redirect to login if not authenticated
3. Include credentials in all fetch requests

**Usage Example:**
```javascript
// 1. Check if user is authenticated
async function checkAuth() {
    const response = await fetch('https://db-api.enersystems.com:5400/api/auth/status', {
        credentials: 'include'  // REQUIRED: Include session cookies
    });
    const data = await response.json();
    return data.authenticated;
}

// 2. Redirect to login if not authenticated
function redirectToLogin() {
    window.location.href = 'https://db-api.enersystems.com:5400/api/auth/microsoft/login';
}

// 3. Fetch QBR data (after authentication)
async function getDevicesByClient(period) {
    const response = await fetch(
        `https://db-api.enersystems.com:5400/api/qbr/metrics/devices-by-client?period=${period}`,
        { credentials: 'include' }  // REQUIRED: Include session cookies
    );

    if (response.status === 401) {
        // Session expired - redirect to login
        redirectToLogin();
        return null;
    }

    return await response.json();
}

// 4. Get monthly metrics
async function getMonthlyMetrics(period, organizationId = 1) {
    const params = new URLSearchParams({
        period: period,
        organization_id: organizationId
    });

    const response = await fetch(
        `https://db-api.enersystems.com:5400/api/qbr/metrics/monthly?${params}`,
        { credentials: 'include' }
    );

    return await response.json();
}

// 5. Get quarterly SmartNumbers
async function getSmartNumbers(quarter, organizationId = 1) {
    const params = new URLSearchParams({
        period: quarter,  // Format: YYYY-Q1, YYYY-Q2, YYYY-Q3, YYYY-Q4
        organization_id: organizationId
    });

    const response = await fetch(
        `https://db-api.enersystems.com:5400/api/qbr/smartnumbers?${params}`,
        { credentials: 'include' }
    );

    return await response.json();
}

// Example: Full authentication flow
async function initQBRDashboard() {
    const isAuthenticated = await checkAuth();

    if (!isAuthenticated) {
        // Show login button or auto-redirect
        document.getElementById('login-btn').style.display = 'block';
        document.getElementById('qbr-content').style.display = 'none';
        return;
    }

    // User is authenticated - load data
    const devicesData = await getDevicesByClient('2025-11');

    if (devicesData && devicesData.success) {
        // Render client table
        devicesData.data.clients.forEach(client => {
            console.log(`${client.client_name}: ${client.seats} seats, ${client.endpoints} endpoints`);
        });

        // Show totals
        console.log(`Total: ${devicesData.data.total_seats} seats, ${devicesData.data.total_endpoints} endpoints`);
    }
}
```

**Data Availability:**
- Device snapshot data available from **October 8, 2025** onwards
- Use last day of month for historical queries (e.g., period=2025-10 uses Oct 31 data)

---

## 📋 **RESPONSE EXAMPLES**

### **System Status Response (ENHANCED)**
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
  "vendor_status": {
    "Ninja": {
      "latest_date": "2025-11-04",
      "freshness_status": "current",
      "freshness_message": "Data is current",
      "days_old": 0
    },
    "ThreatLocker": {
      "latest_date": "2025-11-04",
      "freshness_status": "current",
      "freshness_message": "Data is current",
      "days_old": 0
    }
  },
  "collector_health": {
    "has_recent_failures": true,
    "recent_failures": [
      {
        "collector": "Ninja",
        "job_name": "ninja-collector",
        "status": "failed",
        "message": "400 Client Error: Bad Request for url: https://app.ninjarmm.com/oauth/token",
        "error": null,
        "started_at": "2025-11-05T02:09:03.781381+00:00Z",
        "ended_at": "2025-11-05T02:09:04.681104+00:00Z"
      }
    ],
    "total_failures_last_24h": 4
  },
  "warnings": [
    "Recent collector failures: Ninja"
  ],
  "has_warnings": true,
  "exception_counts": {
    "SPARE_MISMATCH": 73,
    "MISSING_NINJA": 26,
    "DUPLICATE_TL": 1
  },
  "total_exceptions": 100
}
```

**New Fields in `/api/status` Response:**
- **`vendor_status`**: Per-vendor data freshness information
  - `latest_date`: Most recent snapshot date for this vendor
  - `freshness_status`: `current`, `yesterday`, `stale`, `very_stale`, or `no_data`
  - `freshness_message`: Human-readable status message
  - `days_old`: Number of days since last collection
- **`collector_health`**: Collector failure tracking
  - `has_recent_failures`: Boolean flag for easy checking
  - `recent_failures`: Array of failed collector runs in last 24 hours
  - `total_failures_last_24h`: Count of failures
- **`warnings`**: Array of warning messages when data is stale or collectors failed
- **`has_warnings`**: Boolean flag indicating if any warnings exist

**Use Cases:**
- Display warning badges when `has_warnings: true`
- Show per-vendor freshness indicators using `vendor_status`
- Alert users when collectors have failed using `collector_health.has_recent_failures`
- Display specific error messages from `collector_health.recent_failures`

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

### **QBR Authentication Status Response**
```json
{
  "authenticated": true,
  "user": {
    "email": "user@enersystems.com",
    "name": "User Name"
  }
}
```

### **QBR Devices by Client Response**
```json
{
  "success": true,
  "data": {
    "period": "2025-11",
    "organization_id": 1,
    "snapshot_date": "2025-11-30",
    "clients": [
      {"client_name": "ChillCo Inc.", "seats": 104, "endpoints": 111},
      {"client_name": "New Orleans Culinary & Hospitality Instit", "seats": 51, "endpoints": 51},
      {"client_name": "NNW Oil", "seats": 44, "endpoints": 44},
      {"client_name": "Southern Retinal Institute, LLC", "seats": 28, "endpoints": 30}
    ],
    "total_seats": 530,
    "total_endpoints": 579
  }
}
```

**Field Definitions:**
- **`seats`**: Billable workstations only (excludes servers, VMware hosts, spares, internal orgs)
- **`endpoints`**: All billable devices including servers (excludes spares, internal orgs)
- **`snapshot_date`**: The actual date of the device snapshot used (last day of requested month)

### **QBR Monthly Metrics Response**
```json
{
  "success": true,
  "data": {
    "period": "2025-11",
    "organization_id": 1,
    "metrics": [
      {
        "metric_name": "seats_managed",
        "metric_value": 530,
        "vendor_id": 1,
        "data_source": "collected",
        "notes": null,
        "updated_at": "2025-11-25T12:00:00Z"
      },
      {
        "metric_name": "endpoints_managed",
        "metric_value": 579,
        "vendor_id": 1,
        "data_source": "collected",
        "notes": null,
        "updated_at": "2025-11-25T12:00:00Z"
      },
      {
        "metric_name": "reactive_tickets_created",
        "metric_value": 125,
        "vendor_id": 2,
        "data_source": "collected",
        "notes": null,
        "updated_at": "2025-11-25T12:00:00Z"
      }
    ]
  }
}
```

### **QBR SmartNumbers Response**
```json
{
  "success": true,
  "data": {
    "period": "2025-Q4",
    "organization_id": 1,
    "smart_numbers": {
      "tickets_per_endpoint": 0.85,
      "revenue_per_endpoint": 125.50,
      "csat_score": 4.2,
      "first_call_resolution": 78.5
    },
    "thresholds": {
      "tickets_per_endpoint": {"green_max": 1.0, "yellow_max": 1.5, "status": "green"},
      "revenue_per_endpoint": {"green_min": 100, "yellow_min": 80, "status": "green"}
    }
  }
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

# Manual trigger (⚠️ WARNING: This can take 2-5 minutes - use --max-time flag)
curl --max-time 300 -X POST https://db-api.enersystems.com:5400/api/windows-11-24h2/run
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

### **QBR Endpoints (Requires Authentication)**
```bash
# Check authentication status (no auth required)
curl https://db-api.enersystems.com:5400/api/auth/status

# Get devices by client for November 2025
# Note: Requires valid session cookie from browser authentication
curl --cookie "session=YOUR_SESSION_COOKIE" \
  "https://db-api.enersystems.com:5400/api/qbr/metrics/devices-by-client?period=2025-11"

# Get monthly metrics
curl --cookie "session=YOUR_SESSION_COOKIE" \
  "https://db-api.enersystems.com:5400/api/qbr/metrics/monthly?period=2025-11&organization_id=1"

# Get quarterly metrics
curl --cookie "session=YOUR_SESSION_COOKIE" \
  "https://db-api.enersystems.com:5400/api/qbr/metrics/quarterly?period=2025-Q4&organization_id=1"

# Get SmartNumbers/KPIs
curl --cookie "session=YOUR_SESSION_COOKIE" \
  "https://db-api.enersystems.com:5400/api/qbr/smartnumbers?period=2025-Q4&organization_id=1"
```

**Note**: QBR endpoints require Microsoft 365 OAuth authentication. To test:
1. Open browser to `https://db-api.enersystems.com:5400/api/auth/microsoft/login`
2. Complete Microsoft login
3. Extract session cookie from browser dev tools
4. Use cookie in curl commands above

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

### **Enhanced Status Endpoint Features (v1.19.8)**
The `/api/status` endpoint now provides comprehensive collector health and data freshness information:
- **Per-vendor freshness tracking**: Know exactly which vendor's data is stale
- **Collector failure notification**: Automatic alerts when collectors fail in last 24 hours
- **Warning system**: Consolidated warnings array for easy UI integration
- **Proactive sync status**: Dashboard can check `has_warnings` to display alerts without polling multiple endpoints
- **Automatic stale job cleanup**: Automatically detects and cleans up jobs that appear "running" but have no active process

### **Stale Job Detection and Cleanup (v1.19.8)**
The API now automatically detects and cleans up stale running jobs:
- **Automatic cleanup**: `/api/status` and `/api/collectors/progress` automatically clean stale jobs
- **Manual cleanup**: `POST /api/collectors/cleanup-stale` endpoint for on-demand cleanup
- **Detection logic**: Jobs marked "running" for >10 minutes with no active process are marked as "failed"
- **Process verification**: Uses `pgrep` to verify Python collector processes are actually running
- **No action required**: Dashboard continues using existing endpoints - cleanup happens automatically

### **Error Handling**
- All endpoints return JSON responses
- Check HTTP status codes (200 = success, 4xx = client error, 5xx = server error)
- Error responses include `error` field with details

---

## 📚 **RELATED DOCUMENTATION**

- [Variances Dashboard Guide](./GUIDE_VARIANCES_DASHBOARD.md) - Detailed dashboard functionality
- [Windows 11 24H2 Guide](./GUIDE_WINDOWS_11_24H2.md) - Windows 11 compatibility assessment
- [Setup and Troubleshooting Guide](./TROUBLESHOOT_SETUP.md) - Operational guide
- [Database Schema Guide](./GUIDE_DATABASE_SCHEMA.md) - Database reference

---

**🎉 The ES Inventory Hub API is fully operational and ready for Dashboard AI integration!**

---

**Version**: v1.24.0
**Last Updated**: November 25, 2025 22:30 UTC
**Maintainer**: ES Inventory Hub Team

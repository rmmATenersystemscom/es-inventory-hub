# API Integration Guide for Dashboard AI

**Complete API reference for Dashboard AI to integrate with the Database AI's ES Inventory Hub system.**

**Last Updated**: December 18, 2025
**ES Inventory Hub Version**: v1.32.0
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

### **Ninja Usage Changes**
**Public Endpoints**: No authentication required.

```bash
GET /api/ninja/usage-changes           # Compare device inventory between two dates
    ?start_date=YYYY-MM-DD             # Required: Baseline date
    &end_date=YYYY-MM-DD               # Required: Comparison date
    &detail_level=summary              # Optional: "summary" (default) or "full"
    &organization_name=Acme            # Optional: Filter by organization

GET /api/ninja/available-dates         # Get dates with Ninja snapshot data available
    ?days=65                           # Optional: Days to look back (default: 65)
```

### **QBR (Quarterly Business Review) Metrics** 🔐
**⚠️ Authentication Required**: Most QBR endpoints require Microsoft 365 OAuth authentication.
**Exception**: `/api/qbr/metrics/devices-by-client` is **public** (no auth required) - seat/endpoint data is not sensitive.

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

# Device Counts by Client (PUBLIC - no auth required)
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

### **TenantSweep (M365 Security Audits)** 🔐
**⚠️ Authentication Required**: All TenantSweep endpoints require Microsoft 365 OAuth authentication.

```bash
# Create Audit Run
POST /api/tenantsweep/audits           # Create new audit run
    # Body: {"tenant_name": "ACME", "tenant_id": "abc-123", "initiated_by": "user@company.com"}

# Update Audit Run
PATCH /api/tenantsweep/audits/<id>     # Update audit (complete/fail)
    # Body: {"status": "completed", "summary": {"Critical": 1, "High": 2}}

# Add Findings
POST /api/tenantsweep/audits/<id>/findings      # Add single finding
POST /api/tenantsweep/audits/<id>/findings/bulk # Bulk add findings
    # Body: {"findings": [{...}, {...}]}

# Retrieve Audits
GET /api/tenantsweep/audits/<id>       # Get audit with findings
    ?include_findings=true             # Optional: include findings (default: true)
    &severity=Critical                 # Optional: filter by severity

GET /api/tenantsweep/audits            # List audits with filtering
    ?tenant_name=ACME                  # Optional: filter by tenant name (partial match)
    &status=completed                  # Optional: filter by status
    &limit=50                          # Optional: max results (default: 50, max: 200)
    &offset=0                          # Optional: pagination offset

# Get Latest Audit for Tenant
GET /api/tenantsweep/tenants/<tenant_name>/latest-audit

# Export to CSV
GET /api/tenantsweep/audits/<id>/export/csv
    ?severity=High                     # Optional: filter by severity
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

### **✅ 6. TENANTSWEEP DASHBOARD (🔒 M365 Security Audits)**

**API Endpoints:**
- `POST /api/tenantsweep/audits` - Create new audit run
- `PATCH /api/tenantsweep/audits/<id>` - Update audit (complete/fail)
- `POST /api/tenantsweep/audits/<id>/findings` - Add single finding
- `POST /api/tenantsweep/audits/<id>/findings/bulk` - Bulk add findings
- `GET /api/tenantsweep/audits/<id>` - Get audit with findings
- `GET /api/tenantsweep/audits` - List audits
- `GET /api/tenantsweep/tenants/<tenant_name>/latest-audit` - Get latest audit for tenant
- `GET /api/tenantsweep/audits/<id>/export/csv` - Export findings to CSV

**Features:**
- ✅ Create and track M365 tenant security audit runs
- ✅ Record individual security check findings with severity levels
- ✅ Bulk import findings from security scans
- ✅ Filter audits by tenant, status, and severity
- ✅ Export findings to CSV for reporting

**⚠️ CRITICAL: Authentication Required**
All TenantSweep endpoints require Microsoft 365 OAuth authentication (same as QBR).

**Usage Example:**
```javascript
// 1. Create a new audit run
async function createAudit(tenantName, tenantId, initiatedBy) {
    const response = await fetch('https://db-api.enersystems.com:5400/api/tenantsweep/audits', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
            tenant_name: tenantName,
            tenant_id: tenantId,
            initiated_by: initiatedBy
        })
    });
    return await response.json();
}

// 2. Bulk add findings
async function bulkAddFindings(auditId, findings) {
    const response = await fetch(
        `https://db-api.enersystems.com:5400/api/tenantsweep/audits/${auditId}/findings/bulk`,
        {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ findings })
        }
    );
    return await response.json();
}

// 3. Complete the audit with summary
async function completeAudit(auditId, summary) {
    const response = await fetch(
        `https://db-api.enersystems.com:5400/api/tenantsweep/audits/${auditId}`,
        {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({
                status: 'completed',
                summary: summary  // {"Critical": 1, "High": 2, "Medium": 3}
            })
        }
    );
    return await response.json();
}

// 4. Get latest audit for a tenant
async function getLatestAudit(tenantName) {
    const encodedName = encodeURIComponent(tenantName);
    const response = await fetch(
        `https://db-api.enersystems.com:5400/api/tenantsweep/tenants/${encodedName}/latest-audit`,
        { credentials: 'include' }
    );
    return await response.json();
}

// Example: Full audit workflow
async function runTenantAudit(tenantName, tenantId, findings) {
    // Create audit
    const auditResult = await createAudit(tenantName, tenantId, 'user@enersystems.com');
    if (!auditResult.success) throw new Error(auditResult.error.message);

    const auditId = auditResult.data.id;

    // Add findings
    await bulkAddFindings(auditId, findings);

    // Calculate summary
    const summary = findings.reduce((acc, f) => {
        acc[f.severity] = (acc[f.severity] || 0) + 1;
        return acc;
    }, {});

    // Complete audit
    await completeAudit(auditId, summary);

    console.log(`Audit ${auditId} completed for ${tenantName}`);
}
```

**Severity Levels:**
- `Critical` - Immediate action required
- `High` - Should be addressed soon
- `Medium` - Plan to address
- `Low` - Minor concern
- `Info` - Informational only

**Finding Statuses:**
- `pass` - Check passed
- `fail` - Check failed
- `warning` - Potential issue
- `error` - Check could not complete

### **✅ 7. NINJA USAGE CHANGES DASHBOARD (📊 Device Billing Changes)**

**API Endpoints:**
- `GET /api/ninja/usage-changes` - Compare device inventory between two dates
- `GET /api/ninja/available-dates` - Get dates with Ninja snapshot data available

**Features:**
- ✅ Compare device counts between any two dates
- ✅ Identify newly added devices
- ✅ Identify removed devices
- ✅ Track organization reassignments
- ✅ Monitor billing status changes (billable ↔ spare)
- ✅ Per-organization breakdown
- ✅ Summary counts and device-level details

**Public Endpoints**: No authentication required.

**Usage Example:**
```javascript
// 1. Get available dates for date picker
async function getAvailableDates(days = 65) {
    const response = await fetch(
        `https://db-api.enersystems.com:5400/api/ninja/available-dates?days=${days}`
    );
    return await response.json();
}

// 2. Get usage changes between two dates (summary)
async function getUsageChangesSummary(startDate, endDate) {
    const params = new URLSearchParams({
        start_date: startDate,
        end_date: endDate,
        detail_level: 'summary'
    });

    const response = await fetch(
        `https://db-api.enersystems.com:5400/api/ninja/usage-changes?${params}`
    );

    return await response.json();
}

// 3. Get detailed device-level changes
async function getUsageChangesDetail(startDate, endDate, organizationName = null) {
    const params = new URLSearchParams({
        start_date: startDate,
        end_date: endDate,
        detail_level: 'full'
    });

    if (organizationName) {
        params.append('organization_name', organizationName);
    }

    const response = await fetch(
        `https://db-api.enersystems.com:5400/api/ninja/usage-changes?${params}`
    );

    return await response.json();
}

// Example: Monthly comparison dashboard
async function loadMonthlyComparison() {
    // Get available dates first
    const datesData = await getAvailableDates();
    if (!datesData.success) return;

    // Use first and last dates for comparison
    const dates = datesData.data.dates;
    const startDate = dates[0];  // Oldest
    const endDate = dates[dates.length - 1];  // Most recent

    // Get summary
    const summary = await getUsageChangesSummary(startDate, endDate);
    if (summary && summary.success) {
        console.log(`Net change: ${summary.data.summary.net_change} devices`);
        console.log(`Added: ${summary.data.summary.changes.added}`);
        console.log(`Removed: ${summary.data.summary.changes.removed}`);
        console.log(`Org changes: ${summary.data.summary.changes.org_changed}`);
        console.log(`Billing changes: ${summary.data.summary.changes.billing_changed}`);
    }
}
```

**Change Types:**
- `added` - Device exists on end_date but not start_date
- `removed` - Device exists on start_date but not end_date
- `org_changed` - Device moved between organizations
- `billing_changed` - Device changed from billable to spare (or vice versa)

**Data Availability:**
- Device snapshots retained for **65 days**
- Use `/api/ninja/available-dates` to verify data availability before querying

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

**Data Sources:**
- **Oct 2025 onwards**: Live data from `device_snapshot` (Ninja collector)
- **Before Oct 2025**: Historical data from `qbr_client_metrics` (imported from EnerCare)

**Live Data Response (2025-10 onwards):**
```json
{
  "success": true,
  "data": {
    "period": "2025-11",
    "organization_id": 1,
    "data_source": "live",
    "snapshot_date": "2025-11-30",
    "clients": [
      {"client_name": "ChillCo Inc.", "seats": 104, "endpoints": 111},
      {"client_name": "New Orleans Culinary & Hospitality Instit", "seats": 51, "endpoints": 51},
      {"client_name": "NNW Oil", "seats": 44, "endpoints": 44}
    ],
    "total_seats": 530,
    "total_endpoints": 579
  }
}
```

**Historical Data Response (before 2025-10):**
```json
{
  "success": true,
  "data": {
    "period": "2024-10",
    "organization_id": 1,
    "data_source": "historical",
    "clients": [
      {"client_name": "ChillCo Inc.", "seats": 92, "endpoints": 101},
      {"client_name": "New Orleans Culinary & Hospitality Instit", "seats": 54, "endpoints": 54},
      {"client_name": "NNW Oil", "seats": 45, "endpoints": 45}
    ],
    "total_seats": 479,
    "total_endpoints": 521
  }
}
```

**Field Definitions:**
- **`data_source`**: `"live"` (from Ninja collector) or `"historical"` (imported from EnerCare Excel)
- **`seats`**: Billable workstations only (excludes servers, VMware hosts, spares, internal orgs)
- **`endpoints`**: All billable devices including servers (excludes spares, internal orgs)
- **`snapshot_date`**: Only present for live data - the actual date of the device snapshot used

**Data Availability:**
- Historical: Oct 2024 - Sep 2025 (42 clients, imported from EnerCare_Export.xlsx)
- Live: Oct 2025 onwards (from daily Ninja collector snapshots)

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

### **TenantSweep Create Audit Response**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "tenant_name": "ACME Corp",
    "tenant_id": "abc-123-def-456",
    "status": "running",
    "started_at": "2025-12-15T10:00:00Z",
    "completed_at": null,
    "summary": null,
    "error_message": null,
    "initiated_by": "user@enersystems.com",
    "created_at": "2025-12-15T10:00:00Z"
  }
}
```

### **TenantSweep Get Audit with Findings Response**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "tenant_name": "ACME Corp",
    "tenant_id": "abc-123-def-456",
    "status": "completed",
    "started_at": "2025-12-15T10:00:00Z",
    "completed_at": "2025-12-15T10:02:30Z",
    "summary": {"Critical": 1, "High": 2, "Medium": 5},
    "error_message": null,
    "initiated_by": "user@enersystems.com",
    "created_at": "2025-12-15T10:00:00Z",
    "findings": [
      {
        "id": 1,
        "audit_id": 1,
        "check_id": "MFA_ENFORCEMENT",
        "check_name": "MFA Enforcement",
        "severity": "Critical",
        "status": "fail",
        "current_value": "MFA not enforced for 45 users",
        "expected_value": "MFA required for all users",
        "details": {"users_without_mfa": 45, "total_users": 100},
        "recommendation": "Enable MFA via Conditional Access policy",
        "created_at": "2025-12-15T10:01:00Z"
      }
    ],
    "findings_count": 8,
    "severity_summary": {"Critical": 1, "High": 2, "Medium": 5}
  }
}
```

### **TenantSweep List Audits Response**
```json
{
  "success": true,
  "data": {
    "audits": [
      {
        "id": 1,
        "tenant_name": "ACME Corp",
        "tenant_id": "abc-123-def-456",
        "status": "completed",
        "started_at": "2025-12-15T10:00:00Z",
        "completed_at": "2025-12-15T10:02:30Z",
        "summary": {"Critical": 1, "High": 2},
        "error_message": null,
        "initiated_by": "user@enersystems.com",
        "created_at": "2025-12-15T10:00:00Z"
      }
    ],
    "total_count": 1,
    "limit": 50,
    "offset": 0
  }
}
```

### **Ninja Usage Changes Response (Summary)**
```json
{
  "success": true,
  "data": {
    "start_date": "2025-12-01",
    "end_date": "2025-12-18",
    "summary": {
      "start_total_devices": 1250,
      "end_total_devices": 1275,
      "net_change": 25,
      "changes": {
        "added": 35,
        "removed": 10,
        "org_changed": 5,
        "billing_changed": 8
      }
    },
    "by_organization": {
      "Acme Corp": {
        "start_count": 45,
        "end_count": 48,
        "added": 5,
        "removed": 2,
        "org_in": 1,
        "org_out": 0,
        "billing_changed": 1
      },
      "Widget Inc": {
        "start_count": 32,
        "end_count": 35,
        "added": 4,
        "removed": 1,
        "org_in": 2,
        "org_out": 0,
        "billing_changed": 0
      }
    },
    "metadata": {
      "vendor_id": 3,
      "vendor_name": "Ninja",
      "query_time_ms": 245,
      "detail_level": "summary",
      "data_retention_note": "Device-level data available for last 65 days"
    }
  }
}
```

### **Ninja Usage Changes Response (Full)**
```json
{
  "success": true,
  "data": {
    "start_date": "2025-12-01",
    "end_date": "2025-12-18",
    "summary": { ... },
    "by_organization": { ... },
    "changes": {
      "added": [
        {
          "device_identity_id": 12345,
          "hostname": "ACME-WKS-042",
          "display_name": "John Smith Workstation",
          "organization_name": "Acme Corp",
          "device_type": "workstation",
          "billing_status": "billable",
          "location_name": "Main Office"
        }
      ],
      "removed": [
        {
          "device_identity_id": 11234,
          "hostname": "WIDGET-OLD-PC",
          "display_name": "Old Workstation",
          "organization_name": "Widget Inc",
          "device_type": "workstation",
          "billing_status": "billable",
          "last_seen_date": "2025-12-01"
        }
      ],
      "org_changed": [
        {
          "device_identity_id": 10987,
          "hostname": "LAPTOP-TRANSFER",
          "display_name": "Transferred Laptop",
          "from_organization": "Acme Corp",
          "to_organization": "Widget Inc",
          "device_type": "workstation",
          "billing_status": "billable"
        }
      ],
      "billing_changed": [
        {
          "device_identity_id": 10555,
          "hostname": "SERVER-SPARE",
          "display_name": "Server Now Spare",
          "organization_name": "Acme Corp",
          "device_type": "server",
          "from_billing_status": "billable",
          "to_billing_status": "spare"
        }
      ]
    },
    "metadata": { ... }
  }
}
```

### **Ninja Available Dates Response**
```json
{
  "success": true,
  "data": {
    "dates": ["2025-10-14", "2025-10-15", "2025-10-16", "..."],
    "count": 65,
    "range": {
      "start": "2025-10-14",
      "end": "2025-12-18"
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

### **TenantSweep Endpoints (Requires Authentication)**
```bash
# Create an audit
curl --cookie "session=YOUR_SESSION_COOKIE" \
  -X POST https://db-api.enersystems.com:5400/api/tenantsweep/audits \
  -H "Content-Type: application/json" \
  -d '{"tenant_name": "ACME Corp", "tenant_id": "abc-123-def", "initiated_by": "user@enersystems.com"}'

# Add a finding to audit ID 1
curl --cookie "session=YOUR_SESSION_COOKIE" \
  -X POST https://db-api.enersystems.com:5400/api/tenantsweep/audits/1/findings \
  -H "Content-Type: application/json" \
  -d '{"check_id": "MFA_ENFORCEMENT", "check_name": "MFA Enforcement", "severity": "Critical", "status": "fail", "current_value": "MFA not enforced", "expected_value": "MFA required for all users"}'

# Complete an audit
curl --cookie "session=YOUR_SESSION_COOKIE" \
  -X PATCH https://db-api.enersystems.com:5400/api/tenantsweep/audits/1 \
  -H "Content-Type: application/json" \
  -d '{"status": "completed", "summary": {"Critical": 1, "High": 2}}'

# Get audit with findings
curl --cookie "session=YOUR_SESSION_COOKIE" \
  "https://db-api.enersystems.com:5400/api/tenantsweep/audits/1"

# List all audits
curl --cookie "session=YOUR_SESSION_COOKIE" \
  "https://db-api.enersystems.com:5400/api/tenantsweep/audits?limit=10"

# Get latest audit for tenant
curl --cookie "session=YOUR_SESSION_COOKIE" \
  "https://db-api.enersystems.com:5400/api/tenantsweep/tenants/ACME%20Corp/latest-audit"

# Export findings to CSV
curl --cookie "session=YOUR_SESSION_COOKIE" \
  "https://db-api.enersystems.com:5400/api/tenantsweep/audits/1/export/csv" \
  -o audit_findings.csv
```

**Note**: TenantSweep endpoints use the same Microsoft 365 OAuth authentication as QBR endpoints.

### **Ninja Usage Changes Endpoints (Public)**
```bash
# Get available dates for date picker
curl "https://db-api.enersystems.com:5400/api/ninja/available-dates?days=65"

# Get usage changes summary (month-over-month)
curl "https://db-api.enersystems.com:5400/api/ninja/usage-changes?start_date=2025-12-01&end_date=2025-12-18&detail_level=summary"

# Get usage changes with device details
curl "https://db-api.enersystems.com:5400/api/ninja/usage-changes?start_date=2025-12-01&end_date=2025-12-18&detail_level=full"

# Get usage changes for specific organization
curl "https://db-api.enersystems.com:5400/api/ninja/usage-changes?start_date=2025-12-01&end_date=2025-12-18&organization_name=ChillCo%20Inc."
```

**Note**: Ninja API endpoints are public and do not require authentication.

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

**Version**: v1.32.0
**Last Updated**: December 18, 2025 22:10 UTC
**Maintainer**: ES Inventory Hub Team

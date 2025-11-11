# QBR Web Dashboard Backend Readiness Assessment

**Date**: January 2025  
**Backend System**: ES Inventory Hub (Database AI)  
**Purpose**: Comprehensive assessment of current backend capabilities and readiness to support QBR Web Dashboard system

---

## 1️⃣ Role and Responsibilities

### Current Services Running

**Primary Services:**
1. **Flask REST API Server** (`api/api_server.py`)
   - **Port**: 5400 (HTTPS: `https://db-api.enersystems.com:5400`)
   - **Status**: ✅ Active and operational
   - **Purpose**: REST API for variance data, collector management, and system status
   - **Auto-start**: Enabled via systemd service (`es-inventory-api.service`)

2. **PostgreSQL Database**
   - **Status**: ✅ Installed and operational
   - **Location**: Local PostgreSQL instance
   - **Schema Management**: Alembic migrations
   - **Connection**: Via SQLAlchemy with connection pooling

3. **Background ETL Tasks** (Systemd Timers)
   - **Ninja Collector**: Daily at 02:10 AM Central Time
   - **ThreatLocker Collector**: Daily at 02:31 AM Central Time
   - **Cross-Vendor Checks**: Daily at 03:00 AM Central Time
   - **Windows 11 24H2 Assessment**: Runs after collectors complete

### Server Architecture Confirmation

✅ **CONFIRMED**: This server both:
- **Hosts PostgreSQL** database locally
- **Exposes REST API layer** to dashboards on port 5400

### Current API Operations Supported

**System Status & Health:**
- `GET /api/health` - Health check endpoint
- `GET /api/status` - Overall system status with device counts, vendor freshness, collector health
- `GET /api/collectors/status` - Collector service status
- `GET /api/collectors/history` - Collection history (last 10 runs)
- `GET /api/collectors/progress` - Real-time collection progress

**Variance Reports & Analysis:**
- `GET /api/variance-report/latest` - Latest variance report
- `GET /api/variance-report/{date}` - Variance report for specific date
- `GET /api/variance-report/filtered` - Filtered variance report for dashboard
- `GET /api/variances/available-dates` - Get available analysis dates
- `GET /api/variances/historical/{date}` - Historical variance data
- `GET /api/variances/trends` - Trend analysis over time

**Exception Management:**
- `GET /api/exceptions` - Get exceptions with filtering
- `POST /api/exceptions/{id}/resolve` - Resolve an exception
- `POST /api/exceptions/{id}/mark-manually-fixed` - Mark as manually fixed
- `POST /api/exceptions/mark-fixed-by-hostname` - Mark exceptions fixed by hostname
- `POST /api/exceptions/bulk-update` - Bulk exception operations
- `GET /api/exceptions/status-summary` - Exception status summary

**Collector Control (ETL Triggers):**
- `POST /api/collectors/run` - Trigger collector runs (supports async job tracking)
- `POST /api/collectors/threatlocker/run` - Run ThreatLocker collector
- `POST /api/collectors/cross-vendor/run` - Run cross-vendor checks
- `POST /api/collectors/sequence/run` - Run complete collector sequence

**Export Functionality:**
- `GET /api/variances/export/csv` - Export variance data to CSV
- `GET /api/variances/export/pdf` - Export variance data to PDF
- `GET /api/variances/export/excel` - Export variance data to Excel

**Device Management:**
- `GET /api/devices/search?q={hostname}` - Search devices (handles hostname truncation)
- `POST /api/threatlocker/update-name` - Update ThreatLocker computer name
- `POST /api/threatlocker/sync-device` - Sync ThreatLocker device to database

**Windows 11 24H2 Assessment:**
- `GET /api/windows-11-24h2/status` - Compatibility status summary
- `GET /api/windows-11-24h2/incompatible` - List of incompatible devices
- `GET /api/windows-11-24h2/compatible` - List of compatible devices
- `POST /api/windows-11-24h2/run` - Manually trigger assessment

---

## 2️⃣ ETL and Data Flow

### Current ETL Integrations

**✅ Implemented:**
1. **NinjaOne (NinjaRMM) API Integration**
   - **Location**: `collectors/ninja/`
   - **API Client**: `collectors/ninja/api.py` (OAuth2 refresh token flow)
   - **Main Collector**: `collectors/ninja/main.py`
   - **Data Collected**: Device inventory, organization data, device status, hardware info
   - **Storage**: `device_snapshot` table with `vendor_id = 3` (Ninja)
   - **Scheduling**: Daily at 02:10 AM Central via systemd timer

2. **ThreatLocker API Integration**
   - **Location**: `collectors/threatlocker/`
   - **API Client**: `collectors/threatlocker/api.py`
   - **Main Collector**: `collectors/threatlocker/main.py`
   - **Data Collected**: Device inventory, organization data, security status
   - **Storage**: `device_snapshot` table with `vendor_id = 4` (ThreatLocker)
   - **Scheduling**: Daily at 02:31 AM Central via systemd timer

**❌ NOT Implemented:**
1. **ConnectWise API Integration**
   - **Status**: Environment variables configured but no collector implemented
   - **Environment Variables Available**:
     - `CONNECTWISE_SERVER`
     - `CONNECTWISE_COMPANY_ID`
     - `CONNECTWISE_CLIENT_ID`
     - `CONNECTWISE_PUBLIC_KEY`
     - `CONNECTWISE_PRIVATE_KEY`
   - **Location**: `/opt/es-inventory-hub/.env`
   - **Action Required**: Build ConnectWise collector following existing collector patterns

2. **QuickBooks API Integration**
   - **Status**: Not implemented
   - **Action Required**: Build QuickBooks collector from scratch

### ETL Task Hosting and Scheduling

**✅ CONFIRMED**: This backend can host and schedule ETL tasks locally using:

1. **Systemd Timers** (Primary Method - Recommended)
   - **Location**: `/opt/es-inventory-hub/ops/systemd/`
   - **Pattern**: Service file + Timer file
   - **Example**: `ninja-collector.service` + `ninja-collector.timer`
   - **Benefits**: System-level scheduling, automatic restarts, logging via journald

2. **Cron Jobs** (Fallback Method)
   - **Location**: User crontab
   - **Documentation**: `docs/CRON.md`
   - **Status**: Available but systemd preferred

3. **Celery** (Not Currently Used)
   - **Status**: Not implemented
   - **Can Be Added**: Yes, if needed for more complex task orchestration

**ETL Execution Pattern:**
- Collectors run as Python subprocesses via systemd services
- Environment variables loaded from `/opt/dashboard-project/es-dashboards/.env` (symlink to `/opt/shared-secrets/api-secrets.env`)
- Logs stored in `/var/log/es-inventory-hub/`
- Job tracking via `job_runs` and `job_batches` tables

---

## 3️⃣ Data Refresh and Triggers

### Manual Refresh Implementation

**✅ ALREADY IMPLEMENTED**: Manual refresh functionality exists via:

**Endpoint**: `POST /api/collectors/run`

**Current Implementation:**
- **Type**: **Asynchronous** (returns immediately with job tracking)
- **Response Format**: Returns `batch_id` and job status immediately
- **Job Tracking**: Uses `job_batches` and `job_runs` tables
- **Progress Monitoring**: Available via `GET /api/collectors/progress`

**Request Format:**
```json
{
  "collectors": ["ninja", "threatlocker"],
  "priority": "normal",
  "run_cross_vendor": true
}
```

**Response Format:**
```json
{
  "batch_id": "bc_abc12345",
  "status": "queued",
  "message": "Starting collectors: ninja, threatlocker",
  "failed_jobs": [],
  "collectors": [
    {
      "job_name": "ninja-collector",
      "job_id": "ni_xyz67890",
      "status": "queued",
      "started_at": "2025-01-15T10:30:00Z"
    }
  ]
}
```

**Progress Tracking:**
- `GET /api/collectors/progress` - Real-time progress with `progress_percent` and `status`
- Jobs tracked in `job_runs` table with status: `queued`, `running`, `completed`, `failed`, `cancelled`

### Recommendation for QBR Dashboard

**Current Implementation is Suitable:**
- ✅ Asynchronous pattern prevents dashboard timeouts
- ✅ Job tracking allows progress monitoring
- ✅ Batch system supports multiple collectors
- ✅ Error handling and status reporting built-in

**Potential Enhancements:**
1. **WebSocket Support**: For real-time progress updates (currently requires polling)
2. **Webhook Notifications**: Callback URLs when jobs complete
3. **Synchronous Option**: Add `?wait=true` parameter for blocking requests (with timeout)

---

## 4️⃣ API Format and Standards

### Current API Format

**✅ REST API with JSON**

**Framework**: Flask with Flask-CORS
**Content-Type**: `application/json`
**Response Format**: JSON objects with consistent structure

### Example Endpoint Formats

**Example 1: System Status**
```bash
GET /api/status
```

**Response Schema:**
```json
{
  "data_status": {
    "status": "current",
    "message": "Data is current",
    "latest_date": "2025-01-15"
  },
  "device_counts": {
    "Ninja": 762,
    "ThreatLocker": 450
  },
  "vendor_status": {
    "Ninja": {
      "latest_date": "2025-01-15",
      "freshness_status": "current",
      "freshness_message": "Data is current",
      "days_old": 0
    },
    "ThreatLocker": {
      "latest_date": "2025-01-15",
      "freshness_status": "current",
      "freshness_message": "Data is current",
      "days_old": 0
    }
  },
  "collector_health": {
    "recent_failures": [],
    "has_recent_failures": false,
    "total_failures_last_24h": 0
  },
  "warnings": [],
  "has_warnings": false,
  "exception_counts": {
    "MISSING_NINJA": 5,
    "DUPLICATE_TL": 2
  },
  "total_exceptions": 7
}
```

**Example 2: Variance Report**
```bash
GET /api/variance-report/latest?include_resolved=false
```

**Response Schema:**
```json
{
  "report_date": "2025-01-15",
  "total_exceptions": 7,
  "unresolved_count": 7,
  "by_type": {
    "MISSING_NINJA": [
      {
        "id": 123,
        "hostname": "workstation-01",
        "details": {
          "tl_org_name": "Acme Corp",
          "tl_site_name": "Main Office"
        },
        "resolved": false
      }
    ]
  },
  "by_organization": {
    "missing_in_ninja": {
      "total_count": 5,
      "by_organization": {
        "Acme Corp": [
          {
            "hostname": "workstation-01",
            "vendor": "ThreatLocker",
            "display_name": "workstation-01 (Main Office)",
            "organization": "Acme Corp",
            "billing_status": "Unknown",
            "action": "Investigate"
          }
        ]
      }
    }
  }
}
```

**Example 3: Trigger Manual Refresh**
```bash
POST /api/collectors/run
Content-Type: application/json

{
  "collectors": ["ninja", "threatlocker"],
  "run_cross_vendor": true
}
```

**Response Schema:**
```json
{
  "batch_id": "bc_abc12345",
  "status": "queued",
  "message": "Starting collectors: ninja, threatlocker",
  "failed_jobs": [],
  "collectors": [
    {
      "job_name": "ninja-collector",
      "job_id": "ni_xyz67890",
      "status": "queued",
      "started_at": "2025-01-15T10:30:00Z"
    },
    {
      "job_name": "threatlocker-collector",
      "job_id": "tl_def45678",
      "status": "queued",
      "started_at": "2025-01-15T10:30:00Z"
    }
  ]
}
```

### API Standards

**Base URL**: `https://db-api.enersystems.com:5400`  
**API Prefix**: `/api/`  
**HTTP Methods**: GET, POST (PUT, DELETE available but not heavily used)  
**Error Responses**: JSON with `error` field and HTTP status codes  
**CORS**: Enabled for `https://dashboards.enersystems.com` and localhost (dev)

---

## 5️⃣ Security Model

### Current Authentication

**❌ NO AUTHENTICATION IMPLEMENTED**

**Current State:**
- API endpoints are publicly accessible (no authentication required)
- CORS configured for specific origins
- HTTPS available (SSL certificates in `/opt/es-inventory-hub/ssl/`)
- Documented as **HIGH PRIORITY SECURITY FINDING** in security audit

**Security Audit Finding (H-1):**
- **Severity**: HIGH
- **Status**: ⬜ Not Started
- **Location**: `docs/AUDIT_SECURITY_CHECKLIST.md`

### Current CORS Configuration

```python
CORS(app, 
     origins=['https://dashboards.enersystems.com', 'http://localhost:3000', 'http://localhost:8080'],
     methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
     allow_headers=['Content-Type', 'Authorization', 'X-Requested-With', 'X-API-Key', 'Cache-Control', 'Pragma'],
     supports_credentials=True,
     max_age=86400)
```

**Note**: Headers include `Authorization` and `X-API-Key` but no validation implemented.

### Token-Based Authentication Support

**✅ CAN EASILY SUPPORT**: The infrastructure is ready:

1. **Headers Already Configured**: `Authorization` and `X-API-Key` headers are allowed in CORS
2. **Flask Framework**: Easy to add authentication middleware/decorators
3. **Environment Variables**: Secure credential storage pattern already established

**Recommended Implementation Options:**

**Option 1: API Key Authentication (Simplest)**
```python
# Simple API key validation
API_KEY = os.getenv('API_KEY')
@app.before_request
def require_api_key():
    if request.headers.get('X-API-Key') != API_KEY:
        return jsonify({'error': 'Unauthorized'}), 401
```

**Option 2: JWT Authentication (More Secure)**
- Use `flask-jwt-extended` or `PyJWT`
- Token validation middleware
- Refresh token support
- User/role-based access control

**Option 3: Signed API Keys**
- HMAC-signed API keys
- Key rotation support
- Per-client key management

**Implementation Effort**: 2-3 days (per security audit estimate)

---

## 6️⃣ Schema and Expansion

### Current PostgreSQL Schema

**Core Tables (Inventory Management):**
- ✅ `vendor` - Vendor definitions (Ninja, ThreatLocker)
- ✅ `device_identity` - Unique device identifiers per vendor
- ✅ `device_snapshot` - Daily device snapshots with full device data
- ✅ `site` - Site/location definitions
- ✅ `site_alias` - Site name aliases
- ✅ `device_type` - Device type definitions
- ✅ `billing_status` - Billing status definitions
- ✅ `exceptions` - Variance and exception tracking
- ✅ `daily_counts` - Daily aggregated counts
- ✅ `month_end_counts` - Month-end aggregated counts
- ✅ `change_log` - Change tracking over time
- ✅ `job_runs` - ETL job execution tracking
- ✅ `job_batches` - Batch job tracking

### QBR Dashboard Schema Requirements

**❌ NOT PRESENT - NEEDS TO BE ADDED:**

1. **`metrics_monthly`** - Monthly metrics storage
   - **Required Fields**: Period (YYYY-MM), metric_name, metric_value, organization_id, etc.
   - **Action**: Create new table via Alembic migration

2. **`metrics_quarterly`** - Quarterly metrics storage
   - **Required Fields**: Period (YYYY-Q), metric_name, metric_value, organization_id, etc.
   - **Action**: Create new table via Alembic migration

3. **`smartnumbers`** - Key performance indicators
   - **Required Fields**: KPI name, value, period, organization_id, calculation_method, etc.
   - **Action**: Create new table via Alembic migration

4. **`thresholds`** - Threshold definitions for metrics
   - **Required Fields**: metric_name, threshold_type (warning/critical), threshold_value, organization_id, etc.
   - **Action**: Create new table via Alembic migration

5. **`periods`** - Period definitions and metadata
   - **Required Fields**: period_type (monthly/quarterly), period_value, start_date, end_date, is_active, etc.
   - **Action**: Create new table via Alembic migration

### Schema Constraints and Limitations

**Naming Conventions:**
- ✅ Consistent: snake_case for table and column names
- ✅ Primary keys: `id` (Integer or BigInteger)
- ✅ Foreign keys: `{table}_id` pattern
- ✅ Timestamps: `created_at`, `updated_at` (TIMESTAMP WITH TIME ZONE)
- ✅ Dates: `{name}_date` (DATE type)

**Legacy Tables:**
- No legacy tables identified that would conflict
- All tables use modern SQLAlchemy ORM patterns
- Alembic migrations for all schema changes

**Schema Expansion Process:**
1. Create SQLAlchemy model in `storage/schema.py`
2. Create Alembic migration: `alembic revision --autogenerate -m "add qbr tables"`
3. Review and test migration
4. Apply migration: `alembic upgrade head`

**No Limitations Identified:**
- PostgreSQL supports all required data types
- JSONB available for flexible data storage
- Indexing strategy well-established
- Foreign key relationships supported

---

## Summary and Recommendations

### ✅ Ready for QBR Dashboard Support

**Strengths:**
1. ✅ **REST API Infrastructure**: Fully operational Flask API server
2. ✅ **ETL Framework**: Proven collector pattern for external APIs
3. ✅ **Job Tracking**: Asynchronous job system with progress monitoring
4. ✅ **Database**: PostgreSQL with Alembic migrations
5. ✅ **Scheduling**: Systemd timers for automated ETL
6. ✅ **Manual Refresh**: Already implemented and working

**Gaps to Address:**
1. ⚠️ **ConnectWise Integration**: Environment variables ready, collector needs to be built
2. ⚠️ **QuickBooks Integration**: No collector exists, needs to be built from scratch
3. ⚠️ **QBR Schema Tables**: Need to create `metrics_monthly`, `metrics_quarterly`, `smartnumbers`, `thresholds`, `periods`
4. ⚠️ **API Authentication**: High priority security improvement needed

### Recommended Implementation Plan

**Phase 1: Schema Expansion (Week 1)**
- Create QBR-specific tables via Alembic migrations
- Add indexes and foreign key relationships
- Seed initial threshold and period data

**Phase 2: ETL Integration (Week 2-3)**
- Build ConnectWise collector (follow Ninja/ThreatLocker pattern)
- Build QuickBooks collector
- Create ETL jobs for metrics calculation
- Schedule automated monthly/quarterly ETL runs

**Phase 3: API Expansion (Week 3-4)**
- Add QBR-specific endpoints:
  - `GET /api/qbr/metrics/monthly`
  - `GET /api/qbr/metrics/quarterly`
  - `GET /api/qbr/smartnumbers`
  - `GET /api/qbr/thresholds`
  - `POST /api/qbr/thresholds` (update)
  - `GET /api/qbr/periods`
- Enhance manual refresh to include QBR ETL jobs

**Phase 4: Security Hardening (Week 4)**
- Implement API key or JWT authentication
- Add rate limiting
- Restrict CORS to production domains only
- Update documentation

### Estimated Timeline

**Total Implementation**: 4-5 weeks  
**Critical Path**: Schema → ConnectWise/QuickBooks Collectors → API Endpoints → Security

---

## Questions for Clarification

1. **QBR Data Sources**: What specific ConnectWise and QuickBooks endpoints/data are needed for QBR metrics?
2. **Metrics Calculation**: Are metrics calculated from raw data, or do APIs provide pre-calculated metrics?
3. **Refresh Frequency**: How often should QBR data be refreshed? (Daily, weekly, monthly?)
4. **Authentication Preference**: API keys, JWT, or signed keys?
5. **Dashboard Integration**: What specific API endpoints does the QBR dashboard need initially?

---

**Document Status**: ✅ Complete  
**Next Steps**: Review with QBR Dashboard team and begin Phase 1 implementation

---

**Version**: v1.20.1  
**Last Updated**: November 11, 2025 00:33 UTC  
**Maintainer**: ES Inventory Hub Team

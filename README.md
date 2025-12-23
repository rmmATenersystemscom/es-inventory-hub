# ES Inventory Hub

**Current Version**: v1.35.1 (stable)

A centralized inventory management system for collecting and storing data from various sources including Ninja and ThreatLocker.

## Overview

The **ES Inventory Hub** centralizes device inventory data from **NinjaRMM** and **ThreatLocker** into a PostgreSQL database running on Ubuntu. This repository contains the core infrastructure for the ES Inventory Hub, providing data collection, storage, and management capabilities for enterprise security inventory tracking.

## 🚧 **AI Assistant Boundaries**

**IMPORTANT**: This project has clear boundaries to prevent AI assistants from overstepping their responsibilities:

### **ES Inventory Hub AI (Database AI) Scope:**
- ✅ **Data Collection**: NinjaRMM and ThreatLocker collectors
- ✅ **Database Management**: PostgreSQL schema, migrations, queries
- ✅ **API Server**: REST API for variance data (see [Port Configuration](docs/PORT_CONFIGURATION.md))
- ✅ **Systemd Services**: Automated collection scheduling
- ✅ **Cross-Vendor Checks**: Variance detection and exception handling
- ✅ **Documentation**: Project-specific documentation in `/docs/`

### **Dashboard Project AI Scope:**
- ✅ **Web Dashboards**: All dashboard containers (see [Port Configuration](docs/PORT_CONFIGURATION.md))
- ✅ **Nginx Configuration**: Reverse proxy and SSL termination
- ✅ **Dashboard UI**: Frontend interfaces and user experience
- ✅ **Dashboard Integration**: Connecting dashboards to ES Inventory Hub API

### **Boundary Rules:**
1. **ES Inventory Hub AI** should NOT modify dashboard project files
2. **Dashboard AI** should NOT modify ES Inventory Hub database or collectors
3. **Cross-Project Requests**: Use text box requests for inter-project coordination
4. **Stay in Your Lane**: Focus on your project's core responsibilities

### **When to Request Dashboard AI Help:**
```
If ES Inventory Hub needs dashboard-related changes, put your request in a text box:
"Dashboard AI: Please update the nginx configuration to add new API endpoint routing for /api/variance-report/latest"
```

**Goals:**
- Collect daily device snapshots from NinjaRMM and ThreatLocker.
- Maintain 65 days of daily data, with monthly rollups for older history.
- Provide dashboards for analysis (seat counts, spares, billing vs non-billing, etc.).
- Highlight mismatches and exceptions (e.g., ThreatLocker device missing in Ninja).

## Current Version (v1.34.0)

ThreatLocker Usage Changes API release. Added new API endpoints for ThreatLocker device usage tracking:
- `GET /api/threatlocker/available-dates` - Returns dates with available ThreatLocker data
- `GET /api/threatlocker/usage-changes` - Returns device adds/removes by organization

These endpoints mirror the existing Ninja usage changes API pattern, enabling Dashboard AI to track ThreatLocker license changes across all managed organizations.

## Current State

- PostgreSQL database is installed and operational.
- Alembic migrations created the base schema with core tables:  
  `vendor`, `device_identity`, `device_snapshot`, `site`, `billing_status`, etc.
- Seed data loaded:  
  - Vendors: Ninja (id=3), ThreatLocker (id=4)  
  - Device types: server, workstation  
  - Billing status: billable, spare, unknown
- **Ninja collector implemented and tested:**
  - Successfully inserted **762 devices** into `device_snapshot`.
  - Verified with SQL queries (row counts and distinct checks).
- **ThreatLocker collector implemented and operational:**
  - API client, data mapping, and daily automation complete.
  - Runs daily at 02:31 AM Central Time via systemd timer.
  - Known differences: TL reports **hostnames** but not serial numbers.
- **Automated scheduling:**
  - Ninja collector: Daily at 02:10 AM Central Time via systemd timer
  - ThreatLocker collector: Daily at 02:31 AM Central Time via systemd timer
  - 21-minute stagger prevents conflicts and allows database locks to clear

## Environment Configuration

### **Environment Variable Sources**

The ES Inventory Hub system uses environment variables from multiple sources:

#### **Primary Source: Dashboard Project**
- **Location**: `/opt/dashboard-project/es-dashboards/.env` (symlink to `/opt/shared-secrets/api-secrets.env`)
- **Used By**: Systemd services, daily collection scripts
- **Contains**: NinjaRMM and ThreatLocker API credentials

#### **Local Source: ES Inventory Hub**
- **Location**: `/opt/es-inventory-hub/.env`
- **Contains**: Local configuration and ConnectWise credentials
- **Note**: Some API credentials may be duplicated here

### **Required Environment Variables**

#### **For Ninja Collector:**
```bash
NINJA_CLIENT_ID=your_ninja_client_id_here
NINJA_CLIENT_SECRET=your_ninja_client_secret_here
NINJA_REFRESH_TOKEN=your_ninja_refresh_token_here
```

#### **For Database Connection:**
```bash
DB_DSN=postgresql://username:password@hostname:port/database_name
```

### **Manual Testing Commands**

When testing collectors manually, use the dashboard project's environment file:

```bash
# Source environment variables from dashboard project
source /opt/dashboard-project/es-dashboards/.env

# Run collectors with proper environment
python3 -m collectors.ninja.main --limit 5
python3 -m collectors.threatlocker.main --limit 5
```

## 🔌 **Port Configuration**

### **Port Range Allocation**
- **Dashboard Project**: Ports 5000-5499 (reserved)
- **ES Inventory Hub**: Ports 5400-5499 (available for use)
- **Current API Server**: Port 5400

### **Port Usage**
- **API Server**: Port 5400 (REST API for variance data and collector management)
- **Future Services**: Ports 5401-5499 available for additional services
- **Conflict Prevention**: Clear separation from dashboard project port range

## Project Structure

- `api/` - REST API server and testing utilities
- `collectors/` - Data collection modules for various sources
- `storage/` - Database models and migration scripts
- `dashboard_diffs/` - Dashboard comparison and diff utilities
- `common/` - Shared utilities and common functionality
- `docker/` - Docker configuration files
- `tests/` - Test suite
- `scripts/` - Utility scripts and automation tools
- `ops/` - Operations and deployment scripts
- `system-backups/` - Backup copies of system configuration files (see [docs/SYSTEM_BACKUPS.md](docs/SYSTEM_BACKUPS.md))

## 📚 **Shared Documentation (Symbolic Links)**

**Important**: Some documentation files in the `docs/` directory are **symbolic links** to shared documentation across multiple projects. These files serve as a **single source of truth** and should **never be copied** into this project.

### **Shared Documentation Files:**
- **`docs/CHECK_IN_PROCESS.md`** → `/opt/dashboard-project/docs/CHECK_IN_PROCESS.md`
- **`docs/NINJA_API_DOCUMENTATION.md`** → `/opt/dashboard-project/docs/NINJA_API_DOCUMENTATION.md`
- **`docs/THREATLOCKER_API_GUIDE.md`** → `/opt/dashboard-project/docs/THREATLOCKER_API_GUIDE.md`

### **Why Symbolic Links?**
- **Single Source of Truth**: Changes to these documents are automatically reflected across all projects
- **Consistency**: Ensures all projects use the same version of shared documentation
- **Maintenance**: Updates only need to be made in one location
- **Cross-Project Integration**: Facilitates shared knowledge between ES Inventory Hub and Dashboard projects

### **⚠️ Important Notes:**
- **DO NOT COPY** these files - they are shared across multiple projects
- **DO NOT EDIT** these files directly - edit the source files in `/opt/dashboard-project/docs/`
- **DO NOT DELETE** these symbolic links - they are essential for project integration
- If you need to modify shared documentation, edit the source files in the dashboard project

## Exception Handling Rules

1. **Every Ninja device should be present in the database.**
2. **ThreatLocker devices must also exist in Ninja.**  
   If a TL device is missing from Ninja → flag as *exception*.
3. **Duplicates in TL**:  
   - Duplicates are determined by hostname.  
   - Keep the most recent (based on install/created date).  
   - Flag all others for technician review.
4. **Org/Site Name Mismatches**:  
   - Ninja and TL org/site names should match.  
   - If mismatch → flag for technician correction.
5. **Spares**:  
   - Spare determination is based on Ninja rules:  
     - Display name or Location contains "spare", or `deviceType = 'vmguest'`.  
   - If a TL device corresponds to a Ninja spare → flag as invalid (TL should not be installed on spares).
6. **Exceptions must persist until resolved.**  
   Once resolved, remove the exception from tracking.

## Device Classification

### Billable vs Spare Logic

**Source of Truth**: Only NinjaRMM determines billing status for devices.

**Spare Device Rules** (subtract from billable):
1. **Virtual Machine Guests**: `deviceType == 'vmguest'` (classified as 'virtualization', not billable)
2. **Spare in Name/Location**: Any device with "spare" in display name or location (case-insensitive)

**Note**: VM Hosts (`VMWARE_VM_HOST`, `HYPERV_VMM_GUEST`) remain **billable** as they are physical infrastructure requiring licensing.

**Default**: All other devices are classified as `billable`.

## Variance Reports

### Cross-Vendor Consistency Checks

The system automatically detects discrepancies between Ninja and ThreatLocker device inventories through daily variance reports.

**Automated Detection:**
- Runs after ThreatLocker collection (2:30 AM daily)
- Results stored in `exceptions` table
- Manual recalculation available via `scripts/recompute_tl_variance.sh`

**Variance Types:**
- **MISSING_NINJA**: Devices in ThreatLocker but not in Ninja
- **DUPLICATE_TL**: Duplicate hostnames in ThreatLocker
- **SITE_MISMATCH**: Same device assigned to different sites
- **SPARE_MISMATCH**: DevicesThatShouldNotHaveThreatlocker - spare devices still present in ThreatLocker

**Hostname Matching:**
- Uses robust canonical keys with 15-character hostname normalization
- Ninja matching includes fallback fields: `hostname`, `system_name`, `display_name`
- Case-insensitive, domain-stripped comparison

## Data Collection

### Scheduling

**Automated Daily Collection:**
- **Ninja Collector**: 02:10 AM Central Time daily
- **ThreatLocker Collector**: 02:31 AM Central Time daily
- **Cross-Vendor Checks**: 03:00 AM Central Time daily (NEW)
- **21-minute stagger**: Prevents conflicts and allows database locks to clear

**Collection Process:**
1. **Ninja Collection** (02:10 AM Central): Fetches and normalizes all devices
2. **ThreatLocker Collection** (02:31 AM Central): Fetches devices and stores in database
3. **Cross-Vendor Checks** (03:00 AM Central): Analyzes data and generates variance reports
4. **Variance Detection**: Automatically identifies discrepancies between vendors

**Scheduling Methods:**
- **Primary**: Systemd timers (recommended)
- **Fallback**: Cron jobs for Ninja collector

**Manual Execution:**
```bash
# Run collectors on-demand
systemctl start ninja-collector@${USER}.service
systemctl start threatlocker-collector@${USER}.service

# Run cross-vendor checks on-demand
systemctl start es-cross-vendor-checks.service
```

### Device Mapping

**Hostname-Based Matching:**
- **ThreatLocker Canonical Key**: `LOWER(LEFT(SPLIT_PART(hostname,'.',1),15))`
- **Ninja Canonical Keys** (ANY match true):
  1. `LOWER(LEFT(SPLIT_PART(ds.hostname,'.',1),15))`
  2. `LOWER(LEFT(SPLIT_PART(COALESCE(ds.raw->>'system_name', ds.raw->>'SystemName', ds.raw->>'systemName',''),'.',1),15))`
  3. `LOWER(LEFT(SPLIT_PART(SPLIT_PART(COALESCE(ds.raw->>'display_name', ds.raw->>'DisplayName', ds.raw->>'displayName',''),'|',1),'.',1),15))`

**Matching Strategy:**
- **Robustness**: Handles different hostname formats and case variations
- **Fallback Fields**: Uses multiple Ninja fields for comprehensive matching
- **Domain Stripping**: Removes domain suffixes for consistent comparison
- **15-Character Limit**: Prevents issues with very long hostnames

## Testing Queries

### Count devices per vendor per day
```sql
SELECT snapshot_date, vendor_id, COUNT(*)
FROM device_snapshot
GROUP BY snapshot_date, vendor_id
ORDER BY snapshot_date DESC, vendor_id;
```

### Check for ThreatLocker duplicates
```sql
SELECT LOWER(SPLIT_PART(hostname, '.', 1)) AS host, COUNT(*)
FROM device_snapshot
WHERE snapshot_date = CURRENT_DATE AND vendor_id = 4
GROUP BY LOWER(SPLIT_PART(hostname, '.', 1))
HAVING COUNT(*) > 1
ORDER BY 2 DESC;
```

### Check for TL devices installed on Ninja spares
```sql
SELECT tl.hostname, tl.snapshot_date
FROM device_snapshot tl
JOIN device_snapshot nj
  ON LOWER(SPLIT_PART(tl.hostname, '.', 1)) = LOWER(SPLIT_PART(nj.hostname, '.', 1))
WHERE tl.snapshot_date = CURRENT_DATE
  AND nj.snapshot_date = CURRENT_DATE
  AND tl.vendor_id = 4
  AND nj.vendor_id = 3
  AND nj.billing_status_id = 2; -- 2 = spare
```

## Next Steps

1. **ThreatLocker Collector** ✅ **COMPLETED**
   - ✅ API client implemented and tested.
   - ✅ Device data insertion into `device_snapshot` with `vendor_id = 4`.
   - ✅ Systemd timer automation running daily at 02:31 AM Central Time.

2. **Exception Dashboard**
   - Build queries into Flask dashboard:
     - TL device not in Ninja.
     - TL duplicates by hostname.
     - TL device marked spare in Ninja.
     - Org/site name mismatches.
   - Write results to a new `exceptions` table for persistence.

3. **Verification Scripts**
   - Automate daily checks: confirm today's Ninja and TL snapshots inserted successfully.  
   - Alert if missing or incomplete.

## Key Decisions

- Use **PostgreSQL** for structured data and relationships.
- Use **Alembic** for migrations.
- Use **systemd timers** for scheduling collectors (primary method).  
- Use **cron jobs** as fallback for Ninja collector.
- Store logs under `/var/log/es-inventory-hub/` for reliability.  
- Defer dashboard development until data collection and rules are finalized.

## Pending Questions

- Should TL collector use the same `.env` file keys as the dashboard?  
- Should exception handling be done **inline** (during collection) or **post-process** (separate job)?
- Preferred alerting mechanism: dashboard-only, or email/Slack notifications?

## 🔄 CHECK-IN Process

**For complete CHECK-IN process documentation, see:** **[docs/CHECK_IN_PROCESS.md](docs/CHECK_IN_PROCESS.md)**

The CHECK-IN process is a complete Git commit and tag workflow that preserves all changes with comprehensive version control. To trigger the process, use the command `CHECK-IN!` when working with an AI assistant, or run the automated script.

---

## 📚 Documentation

**Complete documentation is available in the `docs/` directory:**

- **[docs/README.md](docs/README.md)** - **Complete documentation index and quick start guide**
- **[docs/DASHBOARD_INTEGRATION_GUIDE.md](docs/DASHBOARD_INTEGRATION_GUIDE.md)** - **Dashboard integration guide with API endpoints**
- **[docs/DATABASE_ACCESS_GUIDE.md](docs/DATABASE_ACCESS_GUIDE.md)** - Database connection and schema information
- **[docs/DEVICE_MATCHING_LOGIC.md](docs/DEVICE_MATCHING_LOGIC.md)** - Device matching algorithms and variance detection
- **[docs/SYSTEMD.md](docs/SYSTEMD.md)** - Systemd service configuration
- **[docs/CRON.md](docs/CRON.md)** - Cron job setup (alternative to systemd)

**🚀 For Dashboard Developers:** Start with `docs/DASHBOARD_INTEGRATION_GUIDE.md`
**🔧 For API Integration:** See `docs/API_QUICK_REFERENCE.md` and `api/api_server.py`

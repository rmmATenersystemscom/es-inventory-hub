# ES Inventory Hub

**Current Version**: v1.4.0 (stable)

A centralized inventory management system for collecting and storing data from various sources including Ninja and ThreatLocker.

## Overview

The **ES Inventory Hub** centralizes device inventory data from **NinjaRMM** and **ThreatLocker** into a PostgreSQL database running on Ubuntu. This repository contains the core infrastructure for the ES Inventory Hub, providing data collection, storage, and management capabilities for enterprise security inventory tracking.

**Goals:**
- Collect daily device snapshots from NinjaRMM and ThreatLocker.
- Maintain 65 days of daily data, with monthly rollups for older history.
- Provide dashboards for analysis (seat counts, spares, billing vs non-billing, etc.).
- Highlight mismatches and exceptions (e.g., ThreatLocker device missing in Ninja).

## Current Version (v1.4.0)

This release includes the complete implementation of both Ninja and ThreatLocker collectors with PostgreSQL UPSERT functionality, automated daily collection scripts, variance detection, and comprehensive documentation.

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

**Note:** The `.env` file is symlinked and not managed in this repository. Please ensure your environment variables are properly configured in the linked location.

## Project Structure

- `collectors/` - Data collection modules for various sources
- `storage/` - Database models and migration scripts
- `dashboard_diffs/` - Dashboard comparison and diff utilities
- `common/` - Shared utilities and common functionality
- `docker/` - Docker configuration files
- `tests/` - Test suite
- `scripts/` - Utility scripts and automation tools
- `ops/` - Operations and deployment scripts

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
- **SPARE_MISMATCH**: Spare devices still present in ThreatLocker

**Hostname Matching:**
- Uses robust canonical keys with 15-character hostname normalization
- Ninja matching includes fallback fields: `hostname`, `system_name`, `display_name`
- Case-insensitive, domain-stripped comparison

## Data Collection

### Scheduling

**Automated Daily Collection:**
- **Ninja Collector**: 02:10 AM Central Time daily
- **ThreatLocker Collector**: 02:31 AM Central Time daily
- **21-minute stagger**: Prevents conflicts and allows database locks to clear

**Collection Process:**
1. **Ninja Collection** (02:10 AM Central): Fetches and normalizes all devices
2. **ThreatLocker Collection** (02:31 AM Central): Fetches devices and runs cross-vendor checks
3. **Variance Detection**: Automatically identifies discrepancies between vendors

**Scheduling Methods:**
- **Primary**: Systemd timers (recommended)
- **Fallback**: Cron jobs for Ninja collector

**Manual Execution:**
```bash
# Run collectors on-demand
systemctl start ninja-collector@${USER}.service
systemctl start threatlocker-collector@${USER}.service
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

### **Purpose**
The CHECK-IN process is a complete Git commit and tag workflow that preserves all changes made to the ES Inventory Hub project with comprehensive version control and documentation.

### **When to Use CHECK-IN**
- When you want to save all current changes to the project
- After completing a set of related modifications
- Before making major changes that might need to be reverted
- When you want to create a versioned snapshot of the current state

### **Usage**
To trigger the CHECK-IN process, simply run:
```bash
/opt/es-inventory-hub/scripts/checkin.sh
```

Or when working with an AI assistant, use the command:
```
CHECK-IN!
```

### **What Happens During CHECK-IN**

#### **1. Git Add**
- All changes are automatically staged for commit
- No manual `git add` commands needed

#### **2. Git Commit**
- Changes are committed with a detailed, descriptive message
- The commit message describes all modifications made

#### **3. Git Tag**
- A version tag is created with a comprehensive descriptive message
- Tag format: `vX.Y.Z` (e.g., v1.0.0, v1.1.0, v2.0.0)
- Tag message contains detailed notes about all changes

#### **4. Version Number Update**
- Updates the version number in main README.md to match the new tag
- Updates line: `**Current Version**: vX.Y.Z (stable)`
- Updates line: `## Current Version (vX.Y.Z)`

#### **5. Git Push**
- Both commit and tag are pushed to the remote repository
- Ensures all changes are backed up and available to other team members

### **Version Strategy**
- **Patch Updates**: `vX.Y.Z+1` (e.g., v1.0.0 → v1.0.1) for bug fixes and minor changes
- **Minor Features**: `vX.Y+1.0` (e.g., v1.0.1 → v1.1.0) for new features
- **Major Changes**: `vX+1.0.0` (e.g., v1.5.2 → v2.0.0) for significant architectural changes

### **Example CHECK-IN Output**
```
CHECK-IN COMPLETE! ✅

Tag Used: v1.1.0

Changes Committed:
Changes detected:
  + New file: scripts/run_ninja_daily.sh
  + New file: ops/CRON.md
  ~ Modified: README.md

Files Modified:
- scripts/run_ninja_daily.sh
- ops/CRON.md  
- README.md

The changes have been successfully committed and pushed to the remote repository
All detailed revision notes are preserved in Git tag messages and commit history
```

### **Key Benefits**
- **Complete Traceability**: Every change is documented and versioned
- **Rollback Capability**: Can revert to any previous version if needed
- **Team Collaboration**: All changes are available to other team members
- **Production Safety**: Versioned releases ensure stable deployments
- **Change Documentation**: Comprehensive notes about what was modified and why

### **Manual Commands**
If you prefer manual control, you can also use these commands:
```bash
# Check current status
git status

# View existing tags
git tag --sort=-version:refname

# Run CHECK-IN process
./scripts/checkin.sh

# View latest tag details
git show $(git tag --sort=-version:refname | head -1)
```

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
**🔧 For API Integration:** See `docs/API_QUICK_REFERENCE.md` and `docs/api_server.py`

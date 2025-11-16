# NinjaRMM Metrics Definition for QBR

**Purpose**: Official reference for NinjaRMM metric definitions used in QBR calculations

**Date**: January 2025

**Status**: ✅ **APPROVED**

---

## Overview

The QBR system collects two distinct metrics from NinjaRMM:
1. **# of Endpoints Managed** (Billable count)
2. **# of Seats Managed** (BHAG calculation)

**Critical Note**: These are **NOT the same metric**. They have different exclusion rules and serve different business purposes.

---

## Metric 1: # of Endpoints Managed

### Definition

**# of Endpoints Managed = Count of all billable devices managed in NinjaRMM**

This represents the total number of physical devices that the company bills clients for managing.

### What Gets Counted

- **Physical workstations** (not spare, not from excluded orgs)
- **Physical servers** (Windows Server, Linux, etc.) (not spare, not from excluded orgs)
- **VM Hosts** (VMWARE_VM_HOST, HYPERV_VMM_GUEST) (not spare, not from excluded orgs)
- **Any other physical devices** (not spare, not from excluded orgs)

### What Gets Excluded

**Exclusion 1: Virtual Machine Guests**
- Devices where `deviceType == 'vmguest'`
- Devices where `nodeClass == 'vmware_vm_guest'`
- **Rationale**: VM guests are virtual machines, not physical infrastructure
- **Current Status**: These are already excluded during collection (not in `device_snapshot` table)

**Exclusion 2: Spare Devices (ALL device types)**
- Display name contains "spare" (case-insensitive), OR
- Location contains "spare" (case-insensitive)
- **Applies to ALL types**: workstations, servers, VM hosts, etc.
- **Examples**:
  - "SPARE-SERVER-01" → Excluded
  - Server in location "Storage - Spare Equipment" → Excluded
  - "SPARE-LAPTOP" → Excluded
- **Database Field**: `billing_status = 'spare'`

**Exclusion 3: Internal/Non-Billable Organizations**
Exclude ALL devices from these organizations:
- **"Ener Systems"** - Internal organization
- **"Internal Infrastructure"** - Internal infrastructure devices
- **"z_Terese Ashley"** - Specific excluded organization

### SQL Query

```sql
SELECT COUNT(DISTINCT ds.device_identity_id) AS endpoints_managed
FROM device_snapshot ds
JOIN site s ON ds.site_id = s.id
WHERE ds.vendor_id = 2  -- NinjaRMM
  AND ds.snapshot_date = (
    SELECT MAX(snapshot_date)
    FROM device_snapshot
    WHERE vendor_id = 2
      AND snapshot_date >= :period_start
      AND snapshot_date <= :period_end
  )
  AND ds.billing_status = 'billable'  -- Excludes all spare devices
  AND s.organization_name NOT IN ('Ener Systems', 'Internal Infrastructure', 'z_Terese Ashley');
```

### Storage

- **Table**: `qbr_metrics_monthly`
- **Metric Name**: `endpoints_managed`
- **Vendor ID**: 2 (NinjaRMM)
- **Period Format**: `YYYY-MM` (e.g., "2025-01")

---

## Metric 2: # of Seats Managed (BHAG)

### Definition

**# of Seats Managed = Total NinjaRMM devices MINUS specific exclusions**

This represents a filtered count used for BHAG (Big Hairy Audacious Goal) calculations.

**Reference**: https://dashboards.enersystems.com/docs/API_NINJA_BHAG_CALCULATION.md

### What Gets Counted

All devices from NinjaRMM API that **do not** match any exclusion criteria.

### What Gets Excluded

**Exclusion 1: Node Class Exclusions**

Exclude devices where `nodeClass` equals:
- **VMWARE_VM_GUEST** - Virtual machine guest instances
- **WINDOWS_SERVER** - Windows Server operating systems
- **VMWARE_VM_HOST** - VMware host systems

**Exclusion 2: Spare Devices**

Exclude devices where:
- Display name contains "spare" (case-insensitive), OR
- Location name contains "spare" (case-insensitive)

**Examples**:
- Display name: "SPARE-LAPTOP-01" → Excluded
- Location: "Main Office - Spare Equipment" → Excluded

**Exclusion 3: Internal/Non-Billable Organizations**

Exclude ALL devices from these organizations:
- **"Ener Systems"** - Internal organization
- **"Internal Infrastructure"** - Internal infrastructure
- **"z_Terese Ashley"** - Specific excluded organization

### Important: OR Logic

A device is excluded if it matches **ANY ONE** of the above criteria (OR logic, not AND).

### Preventing Double-Counting

The calculation maintains a set of excluded device IDs to ensure each device is only excluded once, even if it matches multiple exclusion criteria.

### SQL Query

```sql
-- Step 1: Get all devices for the period
WITH all_devices AS (
  SELECT DISTINCT ds.device_identity_id, ds.raw, s.organization_name
  FROM device_snapshot ds
  JOIN site s ON ds.site_id = s.id
  WHERE ds.vendor_id = 2  -- NinjaRMM
    AND ds.snapshot_date = (
      SELECT MAX(snapshot_date)
      FROM device_snapshot
      WHERE vendor_id = 2
        AND snapshot_date >= :period_start
        AND snapshot_date <= :period_end
    )
),

-- Step 2: Identify excluded devices
excluded_devices AS (
  SELECT device_identity_id
  FROM all_devices
  WHERE
    -- Exclusion 1: Node Class
    (raw->>'nodeClass' IN ('VMWARE_VM_GUEST', 'WINDOWS_SERVER', 'VMWARE_VM_HOST'))
    OR
    -- Exclusion 2: Spare devices
    (LOWER(raw->>'displayName') LIKE '%spare%' OR LOWER(raw->>'location') LIKE '%spare%')
    OR
    -- Exclusion 3: Organizations
    (organization_name IN ('Ener Systems', 'Internal Infrastructure', 'z_Terese Ashley'))
)

-- Step 3: Count devices not in exclusion list
SELECT COUNT(DISTINCT ad.device_identity_id) AS seats_managed
FROM all_devices ad
WHERE ad.device_identity_id NOT IN (SELECT device_identity_id FROM excluded_devices);
```

### Storage

- **Table**: `qbr_metrics_monthly`
- **Metric Name**: `seats_managed`
- **Vendor ID**: 2 (NinjaRMM)
- **Period Format**: `YYYY-MM` (e.g., "2025-01")

---

## Comparison Table

| Aspect | # of Endpoints Managed | # of Seats Managed (BHAG) |
|--------|------------------------|---------------------------|
| **Purpose** | Billable device count | BHAG calculation metric |
| **VM Guests** | Excluded (not in DB) | Excluded (nodeClass filter) |
| **VM Hosts** | **INCLUDED** | **EXCLUDED** |
| **Windows Servers** | **INCLUDED** | **EXCLUDED** |
| **Workstations** | Included (if not spare/internal) | Included (if not spare/internal) |
| **Spare Devices** | Excluded | Excluded |
| **Internal Orgs** | Excluded | Excluded |
| **Database Field** | `billing_status = 'billable'` | Custom exclusion logic |

### Key Differences

1. **VM Hosts**: Counted in Endpoints, excluded from Seats
2. **Windows Servers**: Counted in Endpoints, excluded from Seats
3. **Implementation**: Endpoints uses `billing_status` field, Seats uses node class filtering

---

## Collection Strategy

### Current Database State

The existing NinjaRMM collector already:
- Collects devices daily at 02:10 AM Central Time
- Stores data in `device_snapshot` table with `vendor_id = 2`
- **Skips VM guests during collection** (they're not in the database)
- Marks spare devices with `billing_status = 'spare'`
- Stores organization/site information

### QBR Collection Approach

**For both metrics**, the QBR collector should:
1. **Query existing `device_snapshot` data** (don't call NinjaRMM API directly)
2. **Use the latest snapshot** within the period
3. **Apply appropriate filters** per metric definition
4. **Store results** in `qbr_metrics_monthly` table

**Note**: We leverage existing daily collection rather than duplicating API calls.

---

## Example Calculation

### Sample Data (January 2025)

Assume `device_snapshot` contains:
- 100 workstations (client organizations)
- 20 servers (Windows Server, client organizations)
- 5 VM hosts (ESXi hosts, client organizations)
- 10 spare workstations (marked with "spare" in name)
- 15 devices from "Ener Systems" organization

### Calculation

**# of Endpoints Managed:**
```
Total devices: 100 + 20 + 5 + 10 + 15 = 150
Exclude spares: 150 - 10 = 140
Exclude internal org: 140 - 15 = 125
Result: 125 endpoints managed
```

**# of Seats Managed (BHAG):**
```
Total devices: 100 + 20 + 5 + 10 + 15 = 150
Exclude servers (nodeClass): 150 - 20 = 130
Exclude VM hosts (nodeClass): 130 - 5 = 125
Exclude spares: 125 - 10 = 115
Exclude internal org: 115 - 15 = 100
Result: 100 seats managed
```

**Difference**: 125 endpoints vs 100 seats (25 device difference due to servers and VM hosts)

---

## Data Source Mapping

| Metric | Source Table | Vendor ID | Filter Field |
|--------|--------------|-----------|--------------|
| # of Endpoints Managed | `device_snapshot` | 2 (NinjaRMM) | `billing_status = 'billable'` + org filter |
| # of Seats Managed | `device_snapshot` | 2 (NinjaRMM) | Custom nodeClass exclusions + spare + org filter |

---

## Implementation Notes

### Database Schema References

**Tables Used:**
- `device_snapshot` - Daily snapshots of all devices
- `site` - Organization and location mapping
- `vendor` - Vendor definitions (id=2 for NinjaRMM)

**Fields Used:**
- `device_snapshot.vendor_id` - Filter to NinjaRMM (2)
- `device_snapshot.snapshot_date` - Period filtering
- `device_snapshot.billing_status` - Spare device identification
- `device_snapshot.raw` - JSON field with nodeClass, displayName, etc.
- `site.organization_name` - Organization filtering

### VM Guest Handling

**Current State**: VM guests are **not in the database** (skipped during collection)

**Impact on QBR**:
- **# of Endpoints Managed**: Already excluded (not in DB)
- **# of Seats Managed**: Already excluded (not in DB)
- **No additional filtering needed** for VM guests in QBR queries

### Future Considerations

If VM guests are ever included in `device_snapshot`:
- Update Endpoints Managed query to explicitly exclude `deviceType='vmguest'`
- Update Seats Managed query to ensure VM guests remain excluded

---

## Design Q&A - How We Arrived at These Definitions

This section documents the clarifying questions and answers that led to the final metric definitions. This provides context for future implementers to understand the design intent.

### Q1: VM Hosts vs VM Guests - Confirm Understanding

**Question:**
Just to confirm I understand the difference:
- **VM Host** = Physical server running virtualization (e.g., ESXi host, Hyper-V host) - **IS billable**
- **VM Guest** = Virtual machine running ON a VM host - **NOT billable**

Is this correct?

**Answer:** ✅ **Correct**

**Impact:** This established the fundamental distinction between physical infrastructure (billable) and virtual machines (not billable).

---

### Q2: Current Ninja Collector Skips VM Guests

**Question:**
The current Ninja collector at line 183 has this code:
```python
if device_type == 'vmguest' or node_class == 'vmware_vm_guest':
    logger.debug(f"Skipping VM guest: {device_name}")
    continue
```

This means VM Guests are **NOT in the `device_snapshot` table at all**. Correct?

**Answer:** Not explicitly answered, but confirmed through subsequent discussion.

**Resolution:** VM guests are already excluded from the database, so QBR queries don't need to filter them explicitly.

---

### Q3: Relationship Between Endpoints and Seats

**Question:**
I now understand these are THREE DIFFERENT concepts:
- **Billable** (for inventory/billing purposes)
- **Seats Managed (BHAG)** (specific calculation with its own exclusions)
- **Endpoints Managed** (for QBR - definition unknown)

Is this correct?

**Answer:** "seats and endpoints are NOT the same thing! VM Hosts and VM Guests are NOT the same thing. VM Hosts are billable, VM Guest are NOT. BHAG has NOTHING to do with billable."

**Key Clarification:** These are completely separate metrics with different exclusion rules.

---

### Q4: Definition of "Billable"

**Question:**
Q6: endpoints is the 'billable' number. Please explain your understanding of what is billable.

**Answer (User confirmed after iterative refinement):**

**Initial Understanding (Incomplete):**
```
Billable = All devices except:
1. VM Guests
2. Spare devices
```

**First Correction:**
"when you say 'All servers', you still need to exclude any server that has the name 'spare' in the name or is in a location whose name includes spare."

**Key Learning:** Spare exclusion applies to ALL device types (servers, workstations, VM hosts), not just workstations.

**Second Correction:**
"you still need to exclude the same organizations that 'seats' excluded."

**Key Learning:** Both Endpoints Managed and Seats Managed exclude the same internal organizations.

**Final Definition (Approved):**
```
Billable = All devices EXCEPT:
1. VM Guests (not in database)
2. ANY device with "spare" in display name or location (servers, workstations, VM hosts)
3. Devices from organizations: "Ener Systems", "Internal Infrastructure", "z_Terese Ashley"
```

**Impact:** This became the definition of "# of Endpoints Managed" for QBR.

---

### Q5: Seats Managed (BHAG) vs Endpoints Managed

**Question:**
Is "# of Endpoints Managed" the total count of all NinjaRMM devices (before exclusions), and "# of Seats Managed" is the BHAG filtered count (after exclusions)?

**Answer (Implied through discussion):**
No - both metrics have exclusions, but they are DIFFERENT exclusions.

**Key Differences Identified:**

| Aspect | Endpoints Managed | Seats Managed (BHAG) |
|--------|-------------------|----------------------|
| **VM Hosts** | ✅ Counted | ❌ Excluded |
| **Windows Servers** | ✅ Counted | ❌ Excluded |
| **VM Guests** | ❌ Excluded | ❌ Excluded |
| **Spare Devices** | ❌ Excluded | ❌ Excluded |
| **Internal Orgs** | ❌ Excluded | ❌ Excluded |

**Impact:** The primary difference is that BHAG excludes servers and VM hosts via nodeClass filtering, while Endpoints includes them.

---

### Q6: All Servers Must Exclude Spares

**Question (from correction):**
"when you say 'All servers', you still need to exclude any server that has the name 'spare' in the name or is in a location whose name includes spare."

**Understanding Before:**
- Workstations: Exclude spares ✓
- Servers: Include all (incorrect assumption)

**Understanding After:**
- Workstations: Exclude spares ✓
- Servers: Exclude spares ✓
- VM Hosts: Exclude spares ✓
- **ANY device type**: Exclude spares ✓

**Impact:** The spare exclusion is universal across ALL device types, not selective.

---

### Q7: Organization Exclusions Apply to Both Metrics

**Question (from correction):**
"you still need to exclude the same organizations that 'seats' excluded."

**Understanding Before:**
- Seats Managed (BHAG): Exclude internal orgs ✓
- Endpoints Managed: No org exclusions (incorrect assumption)

**Understanding After:**
- Both metrics exclude the same three organizations:
  - "Ener Systems"
  - "Internal Infrastructure"
  - "z_Terese Ashley"

**Impact:** Organization filtering is consistent across both metrics.

---

### Summary of Iterative Refinement

**Iteration 1:** Basic billable definition
- VM guests excluded
- Spares excluded

**Iteration 2:** Clarified spare exclusion applies to ALL device types
- Added: Spare servers excluded
- Added: Spare VM hosts excluded

**Iteration 3:** Added organization exclusions
- Both metrics exclude same internal organizations

**Final Approved Definition:**
The definitions documented in this file represent the fully refined and approved specifications after all clarifications.

---

### Design Intent

**Why These Exclusions?**

1. **VM Guests**: Virtual machines don't represent physical infrastructure investments
2. **Spares**: Not actively deployed, shouldn't count toward managed endpoints
3. **Internal Organizations**: Company's own devices, not client billable services
4. **Servers/VM Hosts in BHAG**: BHAG focuses on end-user seats, not infrastructure

**Why Different Exclusions for Each Metric?**

- **Endpoints Managed**: Represents all physical infrastructure being managed (servers + workstations)
- **Seats Managed (BHAG)**: Represents end-user workstation count for goal-setting purposes

Each metric serves a different business purpose, hence different exclusion rules.

---

### Questions to Ask If Modifying These Definitions

If you need to modify these metrics in the future, ask yourself:

1. **Does this change affect billable counting?** If yes, update Endpoints Managed
2. **Does this change affect BHAG goal calculations?** If yes, update Seats Managed
3. **Should spares of this device type be excluded?** Answer is always YES
4. **Should internal org devices be excluded?** Answer is always YES
5. **Is this a physical device or virtual?** VM guests are never counted in either metric
6. **Is this infrastructure (server/VM host) or end-user equipment?** Affects whether it's in BHAG

---

## Related Documentation

- **QBR Calculation Reference**: `/opt/es-inventory-hub/docs/qbr/shared/CALCULATION_REFERENCE.md`
- **BHAG Calculation**: https://dashboards.enersystems.com/docs/API_NINJA_BHAG_CALCULATION.md
- **Ninja API Documentation**: https://dashboards.enersystems.com/docs/API_NINJA.md
- **Implementation Guide**: `/opt/es-inventory-hub/docs/qbr/IMPLEMENTATION_GUIDE.md`

---

**Version**: v1.22.0  
**Last Updated**: November 16, 2025 02:32 UTC  
**Maintainer**: ES Inventory Hub Team  
**Status**: Official Reference Documentation

# STD_SEAT_ENDPOINT_DEFINITIONS.md

> **AUTHORITY SCOPE**: This document is the **SINGLE SOURCE OF TRUTH** for the definitions of "seat" and "endpoint" in the ES Dashboards project.

## Overview

This document defines the business logic and technical implementation for counting "seats" and "endpoints" in the ES Dashboards project. Both metrics are sourced from **NinjaRMM** but have different filtering rules and serve different purposes.

**Important**: Seats and endpoints are **NOT** synonymous. They represent different filtered device counts with distinct business meanings.

---

## Definitions

### Endpoint

An **endpoint** represents any billable managed device in NinjaRMM, including both workstations AND servers. Endpoints are used in operational metrics like the QBR "# of Endpoints Managed".

**Business Definition**: An endpoint is any device actively managed and monitored through NinjaRMM that is billable to a client.

**Technical Definition**: An endpoint is a device record from the NinjaRMM API that:
- Is NOT a virtual machine guest (`vmguest`)
- Is NOT marked as a "spare" device
- Includes workstations, servers, AND VMware hosts

### Seat

A **seat** represents a countable client **workstation** (user device) that is actively managed and monitored through NinjaRMM. Seats specifically exclude servers and are used for per-seat metrics.

**Business Definition**: A seat is a billable workstation that represents a user's primary work device within a client organization.

**Technical Definition**: A seat is a device record from the NinjaRMM API that:
- Is NOT a server (excludes `WINDOWS_SERVER`)
- Is NOT a virtual machine (excludes `VMWARE_VM_GUEST`, `VMWARE_VM_HOST`)
- Is NOT marked as a "spare" device
- Does NOT belong to excluded internal organizations

---

## Key Differences

| Aspect | Endpoint | Seat |
|--------|----------|------|
| **Includes Servers** | Yes | No |
| **Includes Workstations** | Yes | Yes |
| **Includes VMware Hosts** | Yes | No |
| **Includes VM Guests** | No | No |
| **Includes Spares** | No | No |
| **Excludes Internal Orgs** | Yes | Yes |
| **QBR Metric** | `endpoints_managed` (Operations) | `seats_managed` (General Information) |
| **Primary Use** | Operational metrics | Per-seat ticket ratios |

---

## Endpoint Counting Rules

### Included Devices (Endpoints)

Devices that **ARE** counted as endpoints:

- Desktop workstations (Windows, macOS, Linux)
- Laptop computers
- Servers (Windows Server, Linux servers)
- VMware hosts (ESXi/vSphere)
- Network devices managed in NinjaRMM

### Excluded Devices (Endpoints)

Devices that are **NOT** counted as endpoints:

#### 1. Virtual Machine Exclusions

| Device Type | Description |
|-------------|-------------|
| `vmguest` | Virtual machine guests |

#### 2. Spare Device Exclusions

Devices identified as "spare" are excluded based on:

- **Display Name**: If `displayName` contains "spare" (case-insensitive)
- **Location Name**: If the device's location name contains "spare" (case-insensitive)

### Endpoint Filtering Algorithm

```python
def _classify_billable_status(device):
    """Classify device as billable (endpoint) or excluded"""

    # 1. Exclude VM Guests
    device_type = device.get('deviceType', '').lower()
    if device_type == 'vmguest':
        return 'virtualization'  # Not counted as endpoint

    # 2. Exclude spare devices
    display_name = device.get('displayName', '').lower()
    location_name = device.get('location', {}).get('name', '').lower()

    if 'spare' in display_name or 'spare' in location_name:
        return 'spare'  # Not counted as endpoint

    # Device is a billable endpoint
    return 'billable'
```

---

## Seat Counting Rules

### Included Devices (Seats)

Devices that **ARE** counted as seats:

- Desktop workstations (Windows, macOS, Linux)
- Laptop computers
- User devices actively managed in NinjaRMM

### Excluded Devices (Seats)

Devices that are **NOT** counted as seats:

#### 1. Node Class Exclusions

The following NinjaRMM node classes are excluded:

| Node Class | Description |
|------------|-------------|
| `VMWARE_VM_GUEST` | Virtual machine guests |
| `WINDOWS_SERVER` | Windows Server systems |
| `VMWARE_VM_HOST` | VMware ESXi/vSphere hosts |

#### 2. Spare Device Exclusions

Devices identified as "spare" are excluded based on:

- **Display Name**: If `displayName` contains "spare" (case-insensitive)
- **Location Name**: If the device's location name contains "spare" (case-insensitive)

#### 3. Organization Exclusions

Devices belonging to the following organizations are excluded:

| Organization | Reason |
|--------------|--------|
| `Ener Systems, LLC` | Internal organization |
| `Internal Infrastructure` | Internal infrastructure devices |
| `z_Terese Ashley` | Legacy/test organization |

### Seat Filtering Algorithm

```python
def get_ninjarmm_devices_with_filtering():
    """Get filtered NinjaRMM devices (seats only - workstations)"""

    # Organizations to exclude
    excluded_organizations = ['Ener Systems, LLC', 'Internal Infrastructure', 'z_Terese Ashley']

    # Node classes to exclude (servers and VMs)
    excluded_node_classes = ['VMWARE_VM_GUEST', 'WINDOWS_SERVER', 'VMWARE_VM_HOST']

    filtered_devices = []
    for device in all_devices:
        # 1. Exclude specific node classes (servers/VMs)
        if device.node_class in excluded_node_classes:
            continue

        # 2. Exclude spare devices
        if 'spare' in device.display_name.lower():
            continue
        if 'spare' in device.location_name.lower():
            continue

        # 3. Exclude devices from internal organizations
        if device.organization_name in excluded_organizations:
            continue

        # Device passes all filters - count as a seat
        filtered_devices.append(device)

    return filtered_devices
```

---

## Data Source

Both endpoints and seats are retrieved from the **NinjaRMM API** using the following endpoints:

1. `/api/v2/devices` - Get all device records (basic)
2. `/api/v2/devices-detailed` - Get detailed device records
3. `/api/v2/organizations` - Get organization names for filtering
4. `/api/v2/locations` - Get location names for spare filtering

---

## Usage in Dashboards

### QBR Dashboard

The QBR dashboard uses BOTH metrics in different sections:

| Section | Metric | Definition |
|---------|--------|------------|
| Operations | `endpoints_managed` - "# of Endpoints Managed" | All billable devices (workstations + servers) |
| General Information | `seats_managed` - "# of Seats Managed" | Workstations only |

### Tickets Per Client Per Month Dashboard

The seat count is used to calculate **tickets per seat** metrics:

```
Tickets Per Seat = Monthly Ticket Count / Seat Count
```

#### UI Behavior

| Scenario | Display Value |
|----------|---------------|
| Client has seat count | `tickets / seats` (formatted to 2 decimal places) |
| Client has no matching NinjaRMM org | `U` (Undefined) |
| Seat count is zero | `U` (Undefined) |

### BHAG (BottomLeft) Dashboard

The BHAG gauge uses **seat** counting logic (excludes servers).

---

## API Reference

### Seat Counts API Endpoint

**Endpoint**: `GET /api/seat-counts`

**Response**:
```json
{
    "seatCounts": {
        "Client A": 25,
        "Client B": 42,
        "Client C": 18
    },
    "totalOrganizations": 3,
    "timestamp": "2025-11-25T12:00:00Z"
}
```

---

## Summary Table

| Term | Servers | Workstations | VMware Hosts | VM Guests | Spares | Internal Orgs |
|------|---------|--------------|--------------|-----------|--------|---------------|
| **Endpoint** | Included | Included | Included | Excluded | Excluded | Excluded |
| **Seat** | Excluded | Included | Excluded | Excluded | Excluded | Excluded |

---

## Related Documentation

- **[STD_BUSINESS_LOGIC.md](./STD_BUSINESS_LOGIC.md)** - Business logic standards
- **[API_NINJA.md](./API_NINJA.md)** - NinjaRMM API documentation
- **[API_NINJA_BHAG_CALCULATION.md](./API_NINJA_BHAG_CALCULATION.md)** - BHAG calculation details
- **[STD_DASHBOARD.md](./STD_DASHBOARD.md)** - Dashboard development standards

---

**Version**: v3.70.0
**Last Updated**: November 25, 2025 18:30 UTC
**Maintainer**: ES Dashboards Team
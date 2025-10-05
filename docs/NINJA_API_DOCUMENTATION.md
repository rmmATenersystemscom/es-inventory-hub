# 🔌 NinjaRMM API - Comprehensive Documentation

## 🤖 AI Assistant Quick Reference

**Common Issues & Quick Links:**
- **Authentication Problems**: [Authentication Troubleshooting](#authentication-troubleshooting)
- **Custom Fields Not Working**: [Custom Fields Integration](#custom-fields-integration)
- **API Rate Limiting**: [Error Handling - Rate Limiting](#api-rate-limiting)
- **Device Classification Issues**: [Data Processing & Classification](#data-processing--classification)
- **Dashboard Integration**: [Dashboard Implementations](#dashboard-implementations)

**Critical Implementation Notes:**
- ✅ **Use**: `GET /api/v2/device/{device_id}/custom-fields` for custom field VALUES
- ❌ **Avoid**: `GET /api/v2/device-custom-fields?deviceId={device_id}` (returns definitions only)
- 🔑 **Authentication**: OAuth 2.0 with refresh token flow (preferred)
- 🚨 **Fallback Data**: Use obviously fake values (999999, 888888) with "🚨 FAKE DATA" labels
- 🚀 **Recommended**: Optimal Chunking (75 devices, 200ms delays) - 1.74 dev/s, 6.29 min
- 🌊 **Alternative**: Wave Loading (10-75 devices, 500ms + 0.1s delays) - 1.46 dev/s, 7.49 min
- ⏱️ **Performance**: Backend delays (0.1s per device) are the main bottleneck in wave loading

## 📋 Table of Contents

1. [Overview](#overview)
2. [Authentication & Configuration](#authentication--configuration)
3. [API Endpoints](#api-endpoints)
4. [Data Processing & Classification](#data-processing--classification)
5. [Custom Fields Integration](#custom-fields-integration)
6. [Custom Fields Loading Methods Comparison](#custom-fields-loading-methods-comparison)
7. [Dashboard Implementations](#dashboard-implementations)
8. [Error Handling & Troubleshooting](#error-handling--troubleshooting)
9. [Best Practices](#best-practices)
10. [Testing & Validation](#testing--validation)

---

## Overview

The NinjaRMM API integration provides comprehensive device management and monitoring capabilities across multiple dashboards in the ES Dashboards system. This integration supports real-time device data, organization management, custom fields, and advanced filtering capabilities.

### Key Features
- **OAuth 2.0 Authentication** with refresh token support
- **Device Classification** (servers, workstations, virtualization, unknown)
- **Billable Status Tracking** (billable, spare, virtualization)
- **Custom Fields Integration** (TPM, Secure Boot, and other custom data)
- **Organization Management** with location mapping
- **Real-time Data Processing** with timezone support
- **CSV Export Capabilities** for reporting and analysis

### Supported Dashboards
- **BottomLeft** - Device count integration
- **Ninja Seat Count Monthly** - Comprehensive organization usage analytics
- **Future Dashboards** - Extensible architecture for additional integrations

---

## Authentication & Configuration

> **🔐 Secret Management**: For complete secret management setup, security procedures, and troubleshooting, see [Secret Management Notes](./SECRET_MANAGEMENT_NOTES.md).

### Environment Variables

The NinjaRMM API uses OAuth 2.0 authentication with the following environment variables:

```bash
# NinjaRMM API Configuration
NINJA_BASE_URL=https://app.ninjarmm.com
NINJA_CLIENT_ID=your_client_id_here
NINJA_CLIENT_SECRET=your_client_secret_here
NINJA_REFRESH_TOKEN=your_refresh_token_here
NINJA_TIMEOUT=30
```

> **📁 Shared Secrets**: These variables are managed in the shared secrets file `/opt/shared-secrets/api-secrets.env` and symlinked to the project. See [Secret Management Notes](./SECRET_MANAGEMENT_NOTES.md) for setup and troubleshooting.

### Authentication Flow

The system supports two authentication methods:

#### 1. Refresh Token Flow (Preferred)
```python
def _get_access_token(self):
    """Get OAuth access token using refresh token flow"""
    token_url = f"{self.base_url}/oauth/token"
    
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': self.refresh_token,
        'client_id': self.client_id,
        'client_secret': self.client_secret,
    }
    
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    response = self.session.post(token_url, data=data, headers=headers, timeout=30)
    response.raise_for_status()
    
    token_data = response.json()
    return token_data.get('access_token')
```

#### 2. Client Credentials Flow (Fallback)
```python
# Fallback to client credentials flow
data = {
    'grant_type': 'client_credentials',
    'client_id': self.client_id,
    'client_secret': self.client_secret,
    'scope': 'monitoring'
}
```

### API Headers
```python
def _get_api_headers(self):
    """Get headers with authentication token"""
    access_token = self._get_access_token()
    return {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
```

---

## API Endpoints

### Core Endpoints

#### 1. Organizations
```python
GET /api/v2/organizations
```
**Purpose**: Retrieve all organizations with contact and address information
**Response**: List of organization objects with ID, name, status, address, phone, email

#### 2. Locations
```python
GET /api/v2/locations
```
**Purpose**: Retrieve all locations for device mapping
**Response**: List of location objects with ID, name, address, description

#### 3. Devices (Basic)
```python
GET /api/v2/devices
```
**Purpose**: Retrieve basic device information
**Response**: List of device objects with core identification data

#### 4. Devices (Detailed)
```python
GET /api/v2/devices-detailed
```
**Purpose**: Retrieve comprehensive device information
**Response**: List of detailed device objects with full system information

### Modal Data Fields Reference

The Ninja Usage dashboard modal displays comprehensive device information across 45+ columns. Here's how to access each field category:

#### **Basic Device Information**
| Field | API Path | Description | Example Value |
|-------|----------|-------------|---------------|
| **Organization** | `device.organizationId` → `org.name` | Organization name | "Acme Corp" |
| **Location** | `device.location.name` or `device.locationId` → `location.name` | Device location | "Main Office" |
| **System Name** | `device.systemName` | Computer name | "WORKSTATION-01" |
| **Display Name** | `device.displayName` | Friendly device name | "John's Laptop" |
| **Device Type** | `device.deviceType` | Classified type | "workstation", "server", "virtualization" |
| **Billable Status** | `device.billableStatus` | Billing classification | "billable", "spare", "virtualization" |
| **Status** | `device.status` | Device status | "online", "offline" |

#### **Operating System Information**
| Field | API Path | Description | Example Value |
|-------|----------|-------------|---------------|
| **OS Name** | `device.os.name` | Operating system | "Windows 10 Pro" |
| **OS Version** | `device.os.version` or `device.os.releaseId` | OS version | "22H2" |
| **OS Build** | `device.os.build` | Build number | "19045.3693" |
| **OS Architecture** | `device.os.architecture` | System architecture | "x64" |
| **OS Manufacturer** | `device.os.manufacturer` | OS vendor | "Microsoft Corporation" |

#### **User & Network Information**
| Field | API Path | Description | Example Value |
|-------|----------|-------------|---------------|
| **Last Logged In User** | `device.user` | Last user to log in | "john.doe" |
| **IP Addresses** | `device.ipAddress` | All IP addresses | "192.168.1.100, 10.0.0.5" |
| **IPv4 Addresses** | `device.ipv4Addresses` | IPv4 addresses only | "192.168.1.100" |
| **IPv6 Addresses** | `device.ipv6Addresses` | IPv6 addresses only | "2001:db8::1" |
| **Public IP** | `device.publicIp` | External IP address | "203.0.113.1" |

#### **System Hardware Information**
| Field | API Path | Description | Example Value |
|-------|----------|-------------|---------------|
| **System Manufacturer** | `device.system.manufacturer` | Hardware manufacturer | "Dell Inc." |
| **System Model** | `device.system.model` | Hardware model | "OptiPlex 7090" |
| **Serial Number** | `device.system.serialNumber` | Hardware serial | "ABC123456" |
| **BIOS Serial** | `device.system.biosSerialNumber` | BIOS serial number | "BIOS123456" |
| **MAC Addresses** | `device.macAddress` | Network MAC addresses | "00:1B:44:11:3A:B7" |

#### **CPU Information**
| Field | API Path | Description | Example Value |
|-------|----------|-------------|---------------|
| **CPU Model** | `device.processors[0].name` | Processor model | "Intel Core i7-10700" |
| **CPU Cores** | `device.processors[0].numCores` | Physical cores | 8 |
| **CPU Threads** | `device.processors[0].numLogicalCores` | Logical processors | 16 |
| **CPU Speed (MHz)** | `device.processors[0].maxClockSpeed` | Clock speed | 2900 |

#### **Memory Information**
| Field | API Path | Description | Example Value |
|-------|----------|-------------|---------------|
| **Memory (GiB)** | `device.memory / (1024**3)` | RAM in GiB | 16.0 |
| **Memory (Bytes)** | `device.memory` | RAM in bytes | 17179869184 |

#### **Storage Information**
| Field | API Path | Description | Example Value |
|-------|----------|-------------|---------------|
| **Volumes** | `device.volumes` | Storage volumes | "C: 500GB, D: 1TB" |

#### **Timestamps & Activity**
| Field | API Path | Description | Example Value |
|-------|----------|-------------|---------------|
| **Last Online** | `device.lastContact` | Last seen online | "2024-01-15 14:30:00" |
| **Last Update** | `device.lastUpdate` | Last data update | "2024-01-15 14:25:00" |
| **Last Boot Time** | `device.lastBootTime` | System boot time | "2024-01-15 08:00:00" |
| **Agent Install** | `device.created` | Agent installation | "2023-06-01 10:00:00" |

#### **Device Properties**
| Field | API Path | Description | Example Value |
|-------|----------|-------------|---------------|
| **Domain** | `device.system.domain` | Domain membership | "company.local" |
| **Timezone** | `device.timezone` | Device timezone | "America/New_York" |
| **Tags** | `device.tags` | Device tags | "Production, Critical" |
| **Notes** | `device.description` | Device notes | "Primary workstation" |
| **Approval Status** | `device.approvalStatus` | Approval state | "approved" |
| **Node Class** | `device.nodeClass` | Node classification | "WINDOWS_WORKSTATION" |

#### **Monitoring & Security**
| Field | API Path | Description | Example Value |
|-------|----------|-------------|---------------|
| **Monitoring (Health State)** | `device.health.status` | Device health | "healthy", "warning" |
| **Antivirus (Products & State)** | `device.antivirus.products` | AV products | "Windows Defender: Active" |

### Complete Modal Data Access Implementation

#### **Python Implementation Example**
```python
def get_modal_device_data(device):
    """Extract all modal fields from a NinjaRMM device object"""
    
    # Basic device information
    modal_data = {
        # Organization and Location (requires separate API calls)
        'organizationName': get_organization_name(device.get('organizationId')),
        'location': get_location_name(device.get('locationId')),
        
        # Core device info
        'systemName': device.get('systemName', 'N/A'),
        'displayName': device.get('displayName', 'N/A'),
        'deviceType': classify_device_type(device),
        'billableStatus': classify_billable_status(device),
        'status': device.get('status', 'N/A'),
        
        # Operating System
        'os': device.get('os', {}).get('name', 'N/A'),
        'osVersion': device.get('os', {}).get('version', 'N/A'),
        'osBuild': device.get('os', {}).get('build', 'N/A'),
        'osArchitecture': device.get('os', {}).get('architecture', 'N/A'),
        'osManufacturer': device.get('os', {}).get('manufacturer', 'N/A'),
        
        # User and Network
        'user': device.get('user', 'N/A'),
        'ipAddress': device.get('ipAddress', 'N/A'),
        'ipv4Addresses': device.get('ipv4Addresses', 'N/A'),
        'ipv6Addresses': device.get('ipv6Addresses', 'N/A'),
        'publicIp': device.get('publicIp', 'N/A'),
        
        # Hardware Information
        'system': device.get('system', {}),
        'manufacturer': device.get('system', {}).get('manufacturer', 'N/A'),
        'model': device.get('system', {}).get('model', 'N/A'),
        'serialNumber': device.get('system', {}).get('serialNumber', 'N/A'),
        'biosSerial': device.get('system', {}).get('biosSerialNumber', 'N/A'),
        'macAddress': device.get('macAddress', 'N/A'),
        
        # CPU Information
        'processors': device.get('processors', []),
        'cpu': get_cpu_info(device.get('processors', [])),
        'cpuCores': get_cpu_cores(device.get('processors', [])),
        'cpuThreads': get_cpu_threads(device.get('processors', [])),
        'cpuSpeed': get_cpu_speed(device.get('processors', [])),
        
        # Memory Information
        'memory': device.get('memory', 0),
        'memoryGiB': convert_to_gib(device.get('memory', 0)),
        
        # Storage Information
        'volumes': format_volumes(device.get('volumes', [])),
        
        # Timestamps
        'lastContact': format_timestamp(device.get('lastContact')),
        'lastUpdate': format_timestamp(device.get('lastUpdate')),
        'lastBootTime': format_timestamp(device.get('lastBootTime')),
        'created': format_timestamp(device.get('created')),
        
        # Device Properties
        'domain': device.get('system', {}).get('domain', 'N/A'),
        'timezone': device.get('timezone', 'N/A'),
        'tags': format_tags(device.get('tags', [])),
        'notes': device.get('description', 'N/A'),
        'approvalStatus': device.get('approvalStatus', 'N/A'),
        'nodeClass': device.get('nodeClass', 'N/A'),
        
        # Monitoring & Security (requires additional API calls)
        'healthStatus': get_health_status(device.get('id')),
        'antivirusStatus': get_antivirus_status(device.get('id')),
        
        # Custom Fields (TPM/Secure Boot)
        'customFields': get_device_custom_fields(device.get('id'))
    }
    
    return modal_data

def get_cpu_info(processors):
    """Extract CPU model from processors array"""
    if processors and len(processors) > 0:
        return processors[0].get('name', 'N/A')
    return 'N/A'

def get_cpu_cores(processors):
    """Extract CPU core count"""
    if processors and len(processors) > 0:
        return processors[0].get('numCores', 'N/A')
    return 'N/A'

def get_cpu_threads(processors):
    """Extract CPU thread count"""
    if processors and len(processors) > 0:
        return processors[0].get('numLogicalCores', 'N/A')
    return 'N/A'

def get_cpu_speed(processors):
    """Extract CPU speed in MHz"""
    if processors and len(processors) > 0:
        speed = processors[0].get('maxClockSpeed', 0)
        return f"{speed} MHz" if speed > 0 else 'N/A'
    return 'N/A'

def convert_to_gib(bytes_value):
    """Convert bytes to GiB"""
    if bytes_value and bytes_value > 0:
        return round(bytes_value / (1024**3), 2)
    return 'N/A'

def format_volumes(volumes):
    """Format storage volumes for display"""
    if not volumes:
        return 'N/A'
    
    formatted_volumes = []
    for volume in volumes:
        name = volume.get('name', 'Unknown')
        size = volume.get('size', 0)
        size_gb = round(size / (1024**3), 1) if size > 0 else 0
        formatted_volumes.append(f"{name}: {size_gb}GB")
    
    return ', '.join(formatted_volumes)

def format_timestamp(timestamp):
    """Format Unix timestamp to readable date"""
    if not timestamp:
        return 'N/A'
    
    try:
        from datetime import datetime
        return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
    except:
        return str(timestamp)

def format_tags(tags):
    """Format tags array for display"""
    if not tags:
        return 'N/A'
    return ', '.join(tags) if isinstance(tags, list) else str(tags)
```

#### **JavaScript Frontend Implementation**
```javascript
// Extract modal data from device object
function extractModalData(device) {
    return {
        // Basic Information
        organizationName: device.organizationName || 'N/A',
        location: device.location || 'N/A',
        systemName: device.systemName || 'N/A',
        displayName: device.displayName || 'N/A',
        deviceType: device.deviceType || 'N/A',
        billableStatus: device.billableStatus || 'N/A',
        status: device.status || 'N/A',
        
        // Operating System
        osName: device['OS Name'] || device.os || 'N/A',
        osVersion: device['OS Version'] || device.osVersion || 'N/A',
        osBuild: device['OS Build'] || 'N/A',
        osArchitecture: device['OS Architecture'] || 'N/A',
        osManufacturer: device['OS Manufacturer'] || 'N/A',
        
        // User & Network
        lastLoggedInUser: device['Last Logged In User'] || device.user || 'N/A',
        ipAddresses: device['IP Addresses'] || device.ipAddress || 'N/A',
        ipv4Addresses: device['IPv4 Addresses'] || 'N/A',
        ipv6Addresses: device['IPv6 Addresses'] || 'N/A',
        publicIp: device['Public IP'] || 'N/A',
        
        // Hardware
        systemManufacturer: device['System Manufacturer'] || device.manufacturer || 'N/A',
        systemModel: device['System Model'] || device.model || 'N/A',
        serialNumber: device['Serial Number'] || device.serialNumber || 'N/A',
        biosSerial: device['BIOS Serial'] || 'N/A',
        macAddresses: device['MAC Addresses'] || device.macAddress || 'N/A',
        
        // CPU
        cpuModel: device['CPU Model'] || device.cpu || 'N/A',
        cpuCores: device['CPU Cores'] || 'N/A',
        cpuThreads: device['CPU Threads'] || 'N/A',
        cpuSpeed: device['CPU Speed (MHz)'] || 'N/A',
        
        // Memory
        memoryGiB: device['Memory (GiB)'] || device.memory || 'N/A',
        memoryBytes: device['Memory (Bytes)'] || 'N/A',
        
        // Storage
        volumes: device.Volumes || device.diskSpace || 'N/A',
        
        // Timestamps
        lastOnline: device['Last Online'] || formatDate(device.lastContact) || 'N/A',
        lastUpdate: device['Last Update'] || formatDate(device.lastUpdate) || 'N/A',
        lastBootTime: device['Last Boot Time'] || formatDate(device.lastBoot) || 'N/A',
        agentInstall: device['Agent Install Timestamp'] || 'N/A',
        
        // Properties
        domain: device['System Domain'] || device.domain || 'N/A',
        timezone: device['Device Timezone'] || device.timezone || 'N/A',
        tags: device.Tags || device.tags || 'N/A',
        notes: device.Notes || device.description || 'N/A',
        approvalStatus: device['Approval Status'] || 'N/A',
        nodeClass: device['Node Class'] || 'N/A',
        
        // Monitoring & Security
        healthStatus: device['Monitoring (Health State)'] || 'N/A',
        antivirusStatus: device['Antivirus (Products & State)'] || 'N/A',
        
        // Custom Fields (TPM/Secure Boot)
        hasTPM: device['HasTPM'] || 'N/A',
        tpmEnabled: device['TPMEnabled'] || 'N/A',
        tpmVersion: device['TPMVersion'] || 'N/A',
        secureBootAvailable: device['SecureBootAvailable'] || 'N/A',
        secureBootEnabled: device['SecureBootEnabled'] || 'N/A'
    };
}

// Helper function to format dates
function formatDate(timestamp) {
    if (!timestamp || timestamp === 'N/A') return 'N/A';
    
    try {
        // Handle Unix timestamps
        if (typeof timestamp === 'number') {
            return new Date(timestamp * 1000).toLocaleString();
        }
        return new Date(timestamp).toLocaleString();
    } catch (e) {
        return timestamp;
    }
}
```

#### **API Endpoint Integration**
```python
@app.route('/api/device-modal-data/<int:device_id>')
def get_device_modal_data(device_id):
    """Get complete modal data for a specific device"""
    try:
        api = NinjaRMMAPI()
        
        # Get device details
        device = api.get_device_by_id(device_id)
        if not device:
            return jsonify({'error': 'Device not found'}), 404
        
        # Get organization and location names
        organizations = api.get_organizations()
        locations = api.get_locations()
        
        # Extract modal data
        modal_data = get_modal_device_data(device)
        
        # Add organization and location names
        org_map = {org['id']: org['name'] for org in organizations}
        loc_map = {loc['id']: loc['name'] for loc in locations}
        
        modal_data['organizationName'] = org_map.get(device.get('organizationId'), 'N/A')
        modal_data['location'] = loc_map.get(device.get('locationId'), 'N/A')
        
        # Get custom fields
        modal_data['customFields'] = api._get_device_custom_fields(device_id)
        
        return jsonify({
            'device': modal_data,
            'last_updated': datetime.utcnow().isoformat() + 'Z'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

### Modal Data Processing & Field Mapping

#### **Data Processing Pipeline**
The modal data goes through several processing stages:

1. **Raw API Data** → `GET /api/v2/devices-detailed`
2. **Field Extraction** → Extract specific fields from nested objects
3. **Data Transformation** → Convert formats (bytes to GiB, timestamps to dates)
4. **Classification** → Apply business logic (device type, billable status)
5. **Custom Fields** → Load TPM/Secure Boot data separately
6. **Modal Display** → Format for table display

#### **Field Mapping Reference**
```python
# Complete field mapping for modal display
MODAL_FIELD_MAPPING = {
    # Basic Information
    'Organization': {
        'api_path': 'device.organizationId',
        'lookup': 'organizations[org_id].name',
        'fallback': 'N/A'
    },
    'Location': {
        'api_path': 'device.locationId', 
        'lookup': 'locations[loc_id].name',
        'fallback': 'N/A'
    },
    'System Name': {
        'api_path': 'device.systemName',
        'fallback': 'N/A'
    },
    'Display Name': {
        'api_path': 'device.displayName',
        'fallback': 'N/A'
    },
    
    # Operating System
    'OS Name': {
        'api_path': 'device.os.name',
        'fallback': 'N/A'
    },
    'OS Version': {
        'api_path': 'device.os.version',
        'fallback': 'N/A'
    },
    'OS Build': {
        'api_path': 'device.os.build',
        'fallback': 'N/A'
    },
    'OS Architecture': {
        'api_path': 'device.os.architecture',
        'fallback': 'N/A'
    },
    'OS Manufacturer': {
        'api_path': 'device.os.manufacturer',
        'fallback': 'N/A'
    },
    
    # Hardware Information
    'System Manufacturer': {
        'api_path': 'device.system.manufacturer',
        'fallback': 'N/A'
    },
    'System Model': {
        'api_path': 'device.system.model',
        'fallback': 'N/A'
    },
    'Serial Number': {
        'api_path': 'device.system.serialNumber',
        'fallback': 'N/A'
    },
    'BIOS Serial': {
        'api_path': 'device.system.biosSerialNumber',
        'fallback': 'N/A'
    },
    'MAC Addresses': {
        'api_path': 'device.macAddress',
        'fallback': 'N/A'
    },
    
    # CPU Information
    'CPU Model': {
        'api_path': 'device.processors[0].name',
        'fallback': 'N/A'
    },
    'CPU Cores': {
        'api_path': 'device.processors[0].numCores',
        'fallback': 'N/A'
    },
    'CPU Threads': {
        'api_path': 'device.processors[0].numLogicalCores',
        'fallback': 'N/A'
    },
    'CPU Speed (MHz)': {
        'api_path': 'device.processors[0].maxClockSpeed',
        'fallback': 'N/A'
    },
    
    # Memory Information
    'Memory (GiB)': {
        'api_path': 'device.memory',
        'transform': 'convert_to_gib',
        'fallback': 'N/A'
    },
    'Memory (Bytes)': {
        'api_path': 'device.memory',
        'fallback': 'N/A'
    },
    
    # Storage Information
    'Volumes': {
        'api_path': 'device.volumes',
        'transform': 'format_volumes',
        'fallback': 'N/A'
    },
    
    # Timestamps
    'Last Online': {
        'api_path': 'device.lastContact',
        'transform': 'format_timestamp',
        'fallback': 'N/A'
    },
    'Last Update': {
        'api_path': 'device.lastUpdate',
        'transform': 'format_timestamp',
        'fallback': 'N/A'
    },
    'Last Boot Time': {
        'api_path': 'device.lastBootTime',
        'transform': 'format_timestamp',
        'fallback': 'N/A'
    },
    'Agent Install': {
        'api_path': 'device.created',
        'transform': 'format_timestamp',
        'fallback': 'N/A'
    },
    
    # Device Properties
    'Domain': {
        'api_path': 'device.system.domain',
        'fallback': 'N/A'
    },
    'Timezone': {
        'api_path': 'device.timezone',
        'fallback': 'N/A'
    },
    'Tags': {
        'api_path': 'device.tags',
        'transform': 'format_tags',
        'fallback': 'N/A'
    },
    'Notes': {
        'api_path': 'device.description',
        'fallback': 'N/A'
    },
    'Approval Status': {
        'api_path': 'device.approvalStatus',
        'fallback': 'N/A'
    },
    'Node Class': {
        'api_path': 'device.nodeClass',
        'fallback': 'N/A'
    },
    
    # Custom Fields (TPM/Secure Boot)
    'HasTPM': {
        'api_path': 'custom_fields.hastpm',
        'transform': 'interpret_tpm_value',
        'fallback': 'Not Checked'
    },
    'TPMEnabled': {
        'api_path': 'custom_fields.tpmenabled',
        'transform': 'interpret_tpm_value',
        'fallback': 'Not Checked'
    },
    'TPMVersion': {
        'api_path': 'custom_fields.tpmversion',
        'transform': 'interpret_tpm_version',
        'fallback': 'Not Checked'
    },
    'SecureBootAvailable': {
        'api_path': 'custom_fields.securebootavailable',
        'transform': 'interpret_tpm_value',
        'fallback': 'Not Checked'
    },
    'SecureBootEnabled': {
        'api_path': 'custom_fields.securebootenabled',
        'transform': 'interpret_tpm_value',
        'fallback': 'Not Checked'
    }
}
```

#### **Data Transformation Functions**
```python
def convert_to_gib(bytes_value):
    """Convert bytes to GiB for memory display"""
    if not bytes_value or bytes_value == 0:
        return 'N/A'
    return round(bytes_value / (1024**3), 2)

def format_timestamp(timestamp):
    """Convert Unix timestamp to readable date"""
    if not timestamp:
        return 'N/A'
    try:
        from datetime import datetime
        return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
    except:
        return str(timestamp)

def format_volumes(volumes):
    """Format storage volumes for display"""
    if not volumes:
        return 'N/A'
    
    formatted = []
    for volume in volumes:
        name = volume.get('name', 'Unknown')
        size = volume.get('size', 0)
        size_gb = round(size / (1024**3), 1) if size > 0 else 0
        formatted.append(f"{name}: {size_gb}GB")
    
    return ', '.join(formatted)

def format_tags(tags):
    """Format tags array for display"""
    if not tags:
        return 'N/A'
    return ', '.join(tags) if isinstance(tags, list) else str(tags)

def interpret_tpm_value(value, field_name):
    """Interpret TPM/Secure Boot boolean values"""
    if not value or value == '':
        return 'Not Checked'
    
    if value.lower() == 'true':
        return 'Yes'
    elif value.lower() == 'false':
        return 'No'
    else:
        return 'Unknown'

def interpret_tpm_version(value):
    """Interpret TPM version values"""
    if not value or value == '':
        return 'Not Checked'
    
    if value == '0.0':
        return 'No TPM'
    else:
        return value
```

### Custom Fields Endpoints

#### 1. Custom Field Definitions
```python
GET /api/v2/device-custom-fields
```
**Purpose**: Retrieve all custom field definitions
**Response**: List of custom field objects with name, type, description, scope

#### 2. Device Custom Field Values
```python
GET /api/v2/device/{device_id}/custom-fields
```
**Purpose**: Retrieve custom field values for a specific device
**Response**: Dictionary of field names and values

#### 3. Bulk Custom Field Values
```python
GET /api/v2/device-custom-fields?deviceId={device_id}
```
**Purpose**: Retrieve custom field values for a specific device (alternative endpoint)
**Response**: List of field objects with name and value

### Report Endpoints

#### 1. Device Health
```python
GET /api/v2/queries/device-health
```
**Purpose**: Retrieve device health status information
**Response**: List of health status objects keyed by device ID

#### 2. Antivirus Status
```python
GET /api/v2/queries/antivirus-status
```
**Purpose**: Retrieve antivirus product and state information
**Response**: List of antivirus status objects keyed by device ID

#### 3. Backup Jobs
```python
GET /api/v2/backup/jobs
```
**Purpose**: Retrieve backup job status information
**Response**: List of backup job objects keyed by device ID

---

## Data Processing & Classification

### Device Classification

The system automatically classifies devices into categories based on multiple criteria:

#### Server Classification
```python
def _classify_device_type(self, device):
    """Classify device as server or workstation based on specific device types"""
    platform = device.get('platform', '').lower()
    os_name = (device.get('os') or {}).get('name', '').lower()
    device_type = device.get('deviceType', '').lower()
    
    # Check for virtualization devices first
    if device_type == 'vmguest':
        return 'virtualization'  # VM Guests are not billable
    elif device_type == 'vmhost':
        return 'server'  # VM Hosts are servers and should be billable
    
    # Define specific device types
    server_types = [
        'windows server', 'linux server', 'virtual server',
        'server', 'srv', 'dc', 'domain controller'
    ]
    
    # Check platform field first (most reliable)
    if any(server_type in platform for server_type in server_types):
        return 'server'
    
    # Additional classification logic...
```

#### Billable Status Classification
```python
def _classify_billable_status(self, device):
    """Classify device as billable or spare based on device status and activity"""
    device_type = device.get('deviceType', '').lower()
    if device_type == 'vmguest':
        return 'virtualization'  # VM Guests are not billable
    
    display_name = device.get('displayName', '').lower()
    location_name = (device.get('location') or {}).get('name', '').lower()
    
    # Check for spare indicators
    if 'spare' in display_name or 'spare' in location_name:
        return 'spare'
    
    return 'billable'  # Default to billable
```

### Device Filtering

The system implements comprehensive filtering to exclude non-billable devices:

#### Excluded Organizations
```python
excluded_organizations = [
    'Ener Systems', 
    'Internal Infrastructure', 
    'z_Terese Ashley'
]
```

#### Excluded Node Classes
```python
excluded_node_classes = [
    'VMWARE_VM_GUEST', 
    'WINDOWS_SERVER', 
    'VMWARE_VM_HOST'
]
```

#### Spare Device Detection
```python
# Check for spare indicators in display name or location
display_name = device.get('displayName', '').lower()
location_name = locations.get(location_id, '').lower()

if 'spare' in display_name or 'spare' in location_name:
    # Exclude from billable count
```

---

## Custom Fields Integration

### ⚠️ CRITICAL: Proper Custom Fields API Access

**The correct way to access custom field VALUES (not definitions) in NinjaRMM API:**

#### ✅ CORRECT Endpoint for Custom Field Values
```python
GET /api/v2/device/{device_id}/custom-fields
```
**Purpose**: Retrieve actual custom field VALUES for a specific device  
**Response**: Dictionary of field names and their populated values  
**Example Response**:
```json
{
  "hastpm": "true",
  "tpmenabled": "true", 
  "tpmversion": "2.0, 0, 1.38",
  "securebootavailable": "true",
  "securebootenabled": "false"
}
```

#### ❌ INCORRECT Endpoint (Returns Definitions, Not Values)
```python
GET /api/v2/device-custom-fields?deviceId={device_id}
```
**Purpose**: Returns custom field DEFINITIONS, not actual values  
**Response**: List of field definition objects with metadata  
**Why Wrong**: This endpoint returns field structure, not populated data

### Implementation Example

```python
def _get_device_custom_fields(self, device_id):
    """Get custom field VALUES for a specific device"""
    try:
        # ✅ CORRECT: Use device-specific endpoint for values
        custom_fields_url = f"{self.base_url}/api/v2/device/{device_id}/custom-fields"
        headers = self._get_api_headers()
        
        response = requests.get(custom_fields_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Returns dictionary of field_name: value pairs
        return response.json()
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            # Device may not have custom fields configured
            return {}
        raise
    except Exception as e:
        print(f"Error fetching custom fields for device {device_id}: {e}")
        return {}
```

### TPM & Secure Boot Fields

The system integrates with custom fields populated by PowerShell scripts:

#### Field Definitions
| Field Name | Raw Key | Type | Possible Values | Default | Description |
|------------|---------|------|----------------|---------|-------------|
| **HasTPM** | `hastpm` | TEXT | `blank`, `true`, `false` | `false` | Whether device has TPM module |
| **TPMEnabled** | `tpmenabled` | TEXT | `blank`, `true`, `false` | `false` | Whether TPM is enabled |
| **TPMVersion** | `tpmversion` | TEXT | `blank`, `0.0`, `2.0, 0, 1.38` | `0.0` | TPM version string |
| **SecureBootAvailable** | `securebootavailable` | TEXT | `blank`, `true`, `false` | `false` | Whether Secure Boot is available |
| **SecureBootEnabled** | `securebootenabled` | TEXT | `blank`, `true`, `false` | `false` | Whether Secure Boot is enabled |

#### Value Interpretation
```python
def _interpret_tpm_secureboot_value(self, value, field_name):
    """Interpret TPM/Secure Boot custom field values according to specifications"""
    if not value or value == '':
        return 'Not Checked'  # PowerShell script not run
    
    # Handle boolean fields
    if field_name in ['hastpm', 'tpmenabled', 'securebootavailable', 'securebootenabled']:
        if value.lower() == 'true':
            return 'Yes'
        elif value.lower() == 'false':
            return 'No'
        else:
            return 'Unknown'
    
    # Handle version field
    elif field_name == 'tpmversion':
        if value == '0.0':
            return 'No TPM'
        else:
            return value  # Return version string as-is
```

#### Bulk Custom Fields Processing (Backend)

**Server-Side Batch Processing:**
```python
def _get_bulk_device_custom_fields(self, device_ids):
    """Get custom fields for multiple devices efficiently with caching"""
    custom_fields_map = {}
    
    # Process devices in smaller batches to avoid timeouts
    batch_size = 5  # Backend batch size for API reliability
    for i in range(0, len(device_ids), batch_size):
        batch = device_ids[i:i + batch_size]
        
        for device_id in batch:
            try:
                custom_fields = self._get_device_custom_fields(device_id)
                custom_fields_map[device_id] = custom_fields
                
                # Add delay between requests to avoid rate limiting
                time.sleep(0.1)
                
            except Exception as e:
                print(f"Error fetching custom fields for device {device_id}: {e}")
                custom_fields_map[device_id] = {}
    
    return custom_fields_map
```

#### Frontend Wave Loading (Modal Implementation)

**Client-Side Wave Processing:**
```javascript
async function loadCustomFieldsForDevices(deviceIds) {
    console.log('🔍 [DEBUG] Loading custom fields for devices:', deviceIds);
    
    // Filter out devices we already have cached or are currently loading
    const devicesToLoad = deviceIds.filter(id => 
        !customFieldsCache.has(id) && !customFieldsLoading.has(id)
    );
    
    if (devicesToLoad.length === 0) {
        console.log('🔍 [DEBUG] All custom fields already cached or loading');
        return customFieldsCache;
    }
    
    // Process devices in smaller batches to avoid timeouts
    const batchSize = 10;  // Frontend batch size for UI responsiveness
    const batches = [];
    for (let i = 0; i < devicesToLoad.length; i += batchSize) {
        batches.push(devicesToLoad.slice(i, i + batchSize));
    }
    
    console.log('🔍 [DEBUG] Processing', batches.length, 'batches of', batchSize, 'devices each');
    
    for (let batchIndex = 0; batchIndex < batches.length; batchIndex++) {
        const batch = batches[batchIndex];
        console.log('🔍 [DEBUG] Processing batch', batchIndex + 1, 'of', batches.length);
        
        // Mark devices as loading
        batch.forEach(id => customFieldsLoading.add(id));
        
        try {
            const response = await fetch('/dashboard/ninja-usage/api/custom-fields', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ deviceIds: batch })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            // Cache the results
            if (data.custom_fields) {
                Object.entries(data.custom_fields).forEach(([deviceId, fields]) => {
                    customFieldsCache.set(deviceId, fields);
                });
            }
            
            // Update the modal table with custom fields data
            updateModalWithCustomFields(batch);
            
        } catch (error) {
            console.error('❌ [ERROR] Failed to load custom fields for batch:', batch, error);
        } finally {
            // Remove from loading set
            batch.forEach(id => customFieldsLoading.delete(id));
        }
        
        // Add delay between batches to avoid overwhelming the API
        if (batchIndex < batches.length - 1) {
            await new Promise(resolve => setTimeout(resolve, 500));
        }
    }
    
    return customFieldsCache;
}
```

**API Endpoint for Optimal Chunking (75 devices):**
```python
@app.route('/api/custom-fields', methods=['POST'])
def api_custom_fields():
    """API endpoint for custom fields data (TPM/Secure Boot) - OPTIMAL CHUNKING (75 devices)"""
    try:
        data = request.get_json()
        device_ids = data.get('deviceIds', [])
        
        if not device_ids:
            return jsonify({
                'custom_fields': {},
                'error': 'No device IDs provided'
            }), 400
        
        print(f"🔍 [API] Loading custom fields for {len(device_ids)} devices")
        start_time = time.time()
        
        # Initialize NinjaRMM API client
        api = NinjaRMMAPI()
        
        # Optimal chunking approach: Process all devices in chunk without delays
        custom_fields_map = {}
        processed = 0
        
        # Process devices in optimal chunks of 75 (tested to work reliably)
        chunk_size = 75
        for i in range(0, len(device_ids), chunk_size):
            chunk = device_ids[i:i + chunk_size]
            chunk_num = (i // chunk_size) + 1
            total_chunks = (len(device_ids) + chunk_size - 1) // chunk_size
            
            print(f"🔍 [API] Processing chunk {chunk_num}/{total_chunks} ({len(chunk)} devices)")
            chunk_start_time = time.time()
            
            for device_id in chunk:
                try:
                    custom_fields = api._get_device_custom_fields(device_id)
                    custom_fields_map[str(device_id)] = custom_fields
                    processed += 1
                except Exception as e:
                    print(f"⚠️ [API] Error fetching custom fields for device {device_id}: {e}")
                    custom_fields_map[str(device_id)] = {}
            
            chunk_time = time.time() - chunk_start_time
            print(f"✅ [API] Chunk {chunk_num} completed in {chunk_time:.2f}s")
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        print(f"✅ [API] Custom fields loading completed in {processing_time:.2f}s - {processed} devices")
        
        return jsonify({
            'custom_fields': custom_fields_map,
            'device_count': len(custom_fields_map),
            'processing_time': f"{processing_time:.2f}s",
            'last_updated': datetime.utcnow().isoformat() + 'Z'
        })
        
    except Exception as e:
        print(f"❌ [ERROR] Error in custom fields API: {e}")
        return jsonify({
            'error': str(e),
            'custom_fields': {},
            'device_count': 0,
            'last_updated': datetime.utcnow().isoformat() + 'Z'
        }), 500
```

**API Endpoint for Wave Loading (Conservative):**
```python
@app.route('/api/custom-fields-wave', methods=['POST'])
def api_custom_fields_wave():
    """API endpoint for custom fields data (TPM/Secure Boot) - WAVE LOADING (Conservative)"""
    try:
        data = request.get_json()
        device_ids = data.get('deviceIds', [])
        
        if not device_ids:
            return jsonify({
                'custom_fields': {},
                'error': 'No device IDs provided'
            }), 400
        
        print(f"🌊 [WAVE API] Loading custom fields for {len(device_ids)} devices using wave method")
        start_time = time.time()
        
        # Initialize NinjaRMM API client
        api = NinjaRMMAPI()
        
        # Wave loading approach: Process devices with 0.1s delays
        custom_fields_map = {}
        processed = 0
        
        # Process devices in backend batches of 5 (documented approach)
        backend_batch_size = 5
        for i in range(0, len(device_ids), backend_batch_size):
            batch = device_ids[i:i + backend_batch_size]
            batch_num = (i // backend_batch_size) + 1
            total_batches = (len(device_ids) + backend_batch_size - 1) // backend_batch_size
            
            print(f"🌊 [WAVE API] Processing backend batch {batch_num}/{total_batches} ({len(batch)} devices)")
            batch_start_time = time.time()
            
            for device_id in batch:
                try:
                    custom_fields = api._get_device_custom_fields(device_id)
                    custom_fields_map[str(device_id)] = custom_fields
                    processed += 1
                    
                    # Add 0.1s delay between requests (documented approach)
                    time.sleep(0.1)
                    
                except Exception as e:
                    print(f"⚠️ [WAVE API] Error fetching custom fields for device {device_id}: {e}")
                    custom_fields_map[str(device_id)] = {}
            
            batch_time = time.time() - batch_start_time
            print(f"✅ [WAVE API] Backend batch {batch_num} completed in {batch_time:.2f}s")
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        print(f"✅ [WAVE API] Custom fields loading completed in {processing_time:.2f}s - {processed} devices")
        
        return jsonify({
            'custom_fields': custom_fields_map,
            'device_count': len(custom_fields_map),
            'processing_time': f"{processing_time:.2f}s",
            'last_updated': datetime.utcnow().isoformat() + 'Z'
        })
        
    except Exception as e:
        print(f"❌ [ERROR] Error in wave custom fields API: {e}")
        return jsonify({
            'error': str(e),
            'custom_fields': {},
            'device_count': 0,
            'last_updated': datetime.utcnow().isoformat() + 'Z'
        }), 500
```

---

## TPM/Secure Boot Custom Fields Retrieval

### 🔐 Custom Fields Overview

The Ninja Usage dashboard retrieves TPM (Trusted Platform Module) and Secure Boot custom fields from NinjaRMM devices. These fields are populated by PowerShell scripts running on the devices and provide security compliance information.

#### **Custom Fields Retrieved:**
- **HasTPM**: Whether the device has a TPM chip
- **TPMEnabled**: Whether TPM is enabled on the device  
- **TPMVersion**: TPM version information
- **SecureBootAvailable**: Whether Secure Boot is available
- **SecureBootEnabled**: Whether Secure Boot is enabled

#### **API Endpoint for Custom Fields:**
```
GET /api/v2/device/{device_id}/custom-fields
```

#### **Custom Fields Data Structure:**
```json
{
  "customFields": [
    {
      "id": 123,
      "name": "HasTPM",
      "value": "true",
      "type": "boolean"
    },
    {
      "id": 124, 
      "name": "TPMEnabled",
      "value": "true",
      "type": "boolean"
    },
    {
      "id": 125,
      "name": "TPMVersion", 
      "value": "2.0, 0, 1.38",
      "type": "string"
    },
    {
      "id": 126,
      "name": "SecureBootAvailable",
      "value": "true", 
      "type": "boolean"
    },
    {
      "id": 127,
      "name": "SecureBootEnabled",
      "value": "false",
      "type": "boolean"
    }
  ]
}
```

#### **Value Interpretation:**
```python
def _interpret_tpm_secureboot_value(self, value, field_name):
    """Interpret TPM/Secure Boot custom field values according to specifications"""
    if not value or value == '':
        return 'Not Checked'  # PowerShell script not run
    
    # Handle boolean fields
    if field_name in ['hastpm', 'tpmenabled', 'securebootavailable', 'securebootenabled']:
        if value.lower() == 'true':
            return 'Yes'
        elif value.lower() == 'false':
            return 'No'
        else:
            return 'Unknown'
    
    # Handle TPM version field
    elif field_name == 'tpmversion':
        if value == '0.0':
            return 'No TPM'
        else:
            return value  # Return version string as-is
    
    return value
```

## Custom Fields Loading Methods Comparison

### 🎯 Overview

The NinjaRMM custom fields loading system supports two distinct approaches for loading TPM/SecureBoot data. Each method has different performance characteristics, trade-offs, and use cases.

### 📊 Method Comparison

| Aspect | **Optimal Chunking** (Recommended) | **Wave Loading** (Conservative) |
|--------|-----------------------------------|--------------------------------|
| **Chunk/Wave Size** | 75 devices per chunk | 10-75 devices per wave |
| **Frontend Delays** | 200ms between chunks | 500ms between waves |
| **Backend Delays** | None | 0.1s between individual devices |
| **API Calls** | 9 calls (655 devices) | 9 calls (655 devices) |
| **Performance** | 1.74 devices/second | 1.46 devices/second |
| **Total Time (655 devices)** | 6.29 minutes | 7.49 minutes |
| **Reliability** | High (100% success rate) | High (100% success rate) |
| **API Load** | Moderate bursts | Light, steady load |

### 🚀 Method 1: Optimal Chunking (Recommended)

#### **Configuration:**
- **Chunk Size**: 75 devices per chunk
- **Frontend Delay**: 200ms between chunks
- **Backend Delay**: None (processes all 75 devices rapidly)
- **API Endpoint**: `/api/custom-fields`

#### **Why 75 Devices Per Chunk?**
The 75-device chunk size was determined through extensive testing and represents the optimal balance between:
- **API Performance**: Maximum throughput without overwhelming the API
- **Reliability**: 100% success rate in testing
- **User Experience**: Fastest loading times (1.74 devices/second)
- **Resource Management**: Efficient memory and network usage

#### **Frontend Implementation (75-Device Chunking):**
```javascript
// Load custom fields for devices - OPTIMAL CHUNKING (75 devices per chunk)
async function loadCustomFieldsForDevices(deviceIds) {
    console.log(`🔍 [MODAL] Loading custom fields for ${deviceIds.length} devices`);
    
    if (deviceIds.length === 0) {
        console.log('🔍 [MODAL] No devices to load custom fields for');
        return;
    }
    
    const startTime = Date.now();
    const startTimeFormatted = new Date().toLocaleTimeString();
    
    // Optimal chunking based on test results: 75 devices per chunk
    const chunkSize = 75;
    console.log(`🔍 [MODAL] Using optimal chunk size: ${chunkSize} for ${deviceIds.length} devices`);
    console.log(`⏰ [TIMING] Custom fields loading started at: ${startTimeFormatted}`);
    
    // Split devices into chunks
    const chunks = [];
    for (let i = 0; i < deviceIds.length; i += chunkSize) {
        chunks.push(deviceIds.slice(i, i + chunkSize));
    }
    
    console.log(`🔍 [MODAL] Processing ${deviceIds.length} devices in ${chunks.length} chunks`);
    console.log(`⏰ [TIMING] Estimated completion time: ${new Date(startTime + (deviceIds.length / 1.57 * 1000)).toLocaleTimeString()} (based on 1.57 dev/s rate)`);
    
    let allCustomFields = {};
    let processedChunks = 0;
    let totalErrors = 0;
    let totalDevicesProcessed = 0;
    
    try {
        for (let i = 0; i < chunks.length; i++) {
            const chunkNum = i + 1;
            const chunk = chunks[i];
            
            console.log(`🔍 [MODAL] Processing chunk ${chunkNum}/${chunks.length} (${chunk.length} devices)`);
            
            try {
                const chunkStartTime = Date.now();
                const chunkStartFormatted = new Date().toLocaleTimeString();
                
                console.log(`⏰ [TIMING] Chunk ${chunkNum} started at: ${chunkStartFormatted}`);
                
                const response = await fetch('/dashboard/ninja-usage/api/custom-fields', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ deviceIds: chunk })
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                const data = await response.json();
                
                if (data.error) {
                    throw new Error(data.error);
                }
                
                const chunkTime = Date.now() - chunkStartTime;
                const chunkTimeSeconds = (chunkTime / 1000).toFixed(2);
                const chunkRate = (chunk.length / (chunkTime / 1000)).toFixed(2);
                
                console.log(`✅ [MODAL] Chunk ${chunkNum} completed in ${chunkTime}ms (${chunkTimeSeconds}s) - ${data.device_count} devices`);
                console.log(`⏰ [TIMING] Chunk ${chunkNum} rate: ${chunkRate} devices/second`);
                
                Object.assign(allCustomFields, data.custom_fields);
                totalDevicesProcessed += data.device_count;
                processedChunks++;
                
                // Update the modal table with custom fields data after each chunk
                updateModalWithCustomFields(allCustomFields);
                
                // Add a delay between chunks to avoid overwhelming the API
                if (i < chunks.length - 1) {
                    await new Promise(resolve => setTimeout(resolve, 200)); // 200ms delay
                }
                
            } catch (chunkError) {
                console.error(`❌ [MODAL] Error processing chunk ${chunkNum}:`, chunkError);
                totalErrors++;
                // Continue to next chunk even if one fails
            }
        }
        
        const endTime = Date.now();
        const totalTime = endTime - startTime;
        const totalTimeSeconds = (totalTime / 1000).toFixed(2);
        const endTimeFormatted = new Date().toLocaleTimeString();
        const overallRate = (totalDevicesProcessed / (totalTime / 1000)).toFixed(2);
        
        console.log(`🎉 [MODAL COMPLETION] Custom fields loading completed!`);
        console.log(`⏰ [TIMING] Started: ${startTimeFormatted} | Ended: ${endTimeFormatted}`);
        console.log(`⏰ [TIMING] Total time: ${totalTime}ms (${totalTimeSeconds}s)`);
        console.log(`📊 [RESULTS] ${processedChunks}/${chunks.length} chunks successful, ${totalErrors} failed`);
        console.log(`📊 [RESULTS] ${totalDevicesProcessed}/${deviceIds.length} devices processed`);
        console.log(`📊 [RESULTS] Overall rate: ${overallRate} devices/second`);
        
    } catch (error) {
        const totalTime = Date.now() - startTime;
        const totalTimeSeconds = (totalTime / 1000).toFixed(2);
        console.error(`❌ [MODAL] Error in chunked loading after ${totalTimeSeconds}s:`, error);
    }
}
```

#### **Backend Implementation (75-Device Chunking):**
```python
# Backend: Process all devices in chunk without delays
# Process devices in optimal chunks of 75 (tested to work reliably)
chunk_size = 75
for i in range(0, len(device_ids), chunk_size):
    chunk = device_ids[i:i + chunk_size]
    chunk_num = (i // chunk_size) + 1
    total_chunks = (len(device_ids) + chunk_size - 1) // chunk_size
    
    print(f"🔍 [API] Processing chunk {chunk_num}/{total_chunks} ({len(chunk)} devices)")
    chunk_start_time = time.time()
    
    for device_id in chunk:
        try:
            custom_fields = api._get_device_custom_fields(device_id)
            custom_fields_map[str(device_id)] = custom_fields
            processed += 1
        except Exception as e:
            print(f"⚠️ [API] Error fetching custom fields for device {device_id}: {e}")
            custom_fields_map[str(device_id)] = {}
    
    chunk_time = time.time() - chunk_start_time
    print(f"✅ [API] Chunk {chunk_num} completed in {chunk_time:.2f}s")
```

#### **Advantages:**
- ✅ **Fastest Performance**: 1.74 devices/second
- ✅ **Minimal Delays**: Only 1.4 seconds total delay time
- ✅ **Fewer API Calls**: 9 calls vs 9 calls (same as wave loading)
- ✅ **Proven Reliability**: 100% success rate in testing
- ✅ **Better User Experience**: 6.29 minutes vs 7.49 minutes (1.2 minutes faster)

#### **Limitations:**
- ⚠️ **Higher API Load**: Bursts of 75 rapid requests
- ⚠️ **Less Conservative**: Pushes API limits (but safely)
- ⚠️ **Fewer Progress Updates**: 9 chunks vs 66+ waves

#### **Best For:**
- Production environments
- Performance-critical applications
- Users who prefer faster loading times
- Systems with reliable API connectivity

### 🌊 Method 2: Wave Loading (Conservative)

#### **Configuration:**
- **Wave Size**: 10-75 devices per wave
- **Frontend Delay**: 500ms between waves
- **Backend Delay**: 0.1s between individual devices
- **API Endpoint**: `/api/custom-fields-wave`

#### **Implementation:**
```javascript
// Frontend: 10-75 device waves with 500ms delays
const frontendBatchSize = 10; // or 75 for testing
for (let i = 0; i < deviceIds.length; i += frontendBatchSize) {
    const wave = deviceIds.slice(i, i + frontendBatchSize);
    await fetch('/api/custom-fields-wave', {
        method: 'POST',
        body: JSON.stringify({ deviceIds: wave })
    });
    await new Promise(resolve => setTimeout(resolve, 500)); // 500ms delay
}
```

```python
# Backend: Process devices with 0.1s delays
for device_id in batch:
    custom_fields = api._get_device_custom_fields(device_id)
    time.sleep(0.1)  # 0.1s delay after every device
```

#### **Advantages:**
- ✅ **Conservative Approach**: Gentle on API with delays
- ✅ **More Progress Updates**: 66+ waves provide frequent feedback
- ✅ **Lower API Load**: Steady, light load on API
- ✅ **Documented Method**: Follows traditional wave loading patterns
- ✅ **Error Resilience**: Individual failures don't affect entire wave

#### **Limitations:**
- ❌ **Slower Performance**: 1.46 devices/second
- ❌ **High Delay Overhead**: 65.5 seconds total delay time (0.1s per device)
- ❌ **Same API Calls**: 9 calls vs 9 calls (same as optimal chunking)
- ❌ **Longer Wait Times**: 7.49 minutes vs 6.29 minutes (1.2 minutes slower)

#### **Best For:**
- Development/testing environments
- Systems with API rate limiting concerns
- Users who prefer frequent progress updates
- Conservative implementations

### 🏆 Performance Analysis

#### **Delay Breakdown (655 devices):**

| Method | Frontend Delays | Backend Delays | Total Delays | Processing Time |
|--------|----------------|----------------|--------------|-----------------|
| **Optimal Chunking** | 7 × 200ms = 1.4s | 0s | **1.4s** | 6.27 minutes |
| **Wave (10 devices)** | 65 × 500ms = 32.5s | 655 × 0.1s = 65.5s | **98s** | 6.5 minutes |
| **Wave (75 devices)** | 8 × 500ms = 4s | 655 × 0.1s = 65.5s | **69.5s** | 7.49 minutes |

#### **Key Insights:**
1. **Backend delays are the main bottleneck** in wave loading (65.5s vs 0s)
2. **Optimal chunking is 1.2 minutes faster** than wave loading (6.29 vs 7.49 minutes)
3. **API can handle 75-device bursts** without issues
4. **Frontend delays are minimal** compared to backend delays
5. **Both methods achieve 100% success rate** with excellent performance

### 🎯 Recommendations

#### **Use Optimal Chunking When:**
- ✅ **Performance is critical** (production environments)
- ✅ **Users expect fast loading** (under 7 minutes)
- ✅ **API connectivity is reliable**
- ✅ **System can handle moderate API bursts**

#### **Use Wave Loading When:**
- ✅ **API rate limiting is a concern**
- ✅ **Frequent progress updates are needed**
- ✅ **Conservative approach is preferred**
- ✅ **Development/testing environments**

#### **Default Recommendation:**
**Use Optimal Chunking (75-device chunks)** for production environments. The performance benefits (1.2 minutes faster) outweigh the minimal risks, and testing has proven 100% reliability for both methods.

### 🔧 Implementation Guidelines

#### **Switching Between Methods:**
```javascript
// To use Optimal Chunking (default)
loadCustomFieldsForDevices(deviceIds);

// To use Wave Loading
loadCustomFieldsForDevicesWaveLoading(deviceIds);
```

#### **Configuration Tuning:**
- **Optimal Chunking**: Adjust chunk size (50-100 devices) and frontend delay (100-300ms)
- **Wave Loading**: Adjust wave size (10-75 devices), frontend delay (300-500ms), and backend delay (0.05-0.2s)

#### **Monitoring:**
- Monitor API response times and error rates
- Track user experience metrics (loading times, completion rates)
- Adjust parameters based on performance data

### 📊 Actual Test Results (December 2024)

#### **Wave Loading Performance (75-device waves):**
```
🎉 [WAVE COMPLETION] Custom fields loading completed!
⏰ [TIMING] Started: 4:35:01 PM | Ended: 4:42:30 PM
⏰ [TIMING] Total time: 449135ms (449.13s / 7.49 minutes)
📊 [RESULTS] 9/9 waves successful, 0 failed
📊 [RESULTS] 655/655 devices processed (100.0%)
📊 [RESULTS] Average rate: 1.46 devices/second
🏆 [WAVE PERFORMANCE] Expected: 478.1s | Actual: 449.13s | Ratio: 0.94 | Status: ✅ EXCELLENT
```

#### **Wave-by-Wave Performance:**
| Wave | Devices | Time (s) | Rate (dev/s) | Performance |
|------|---------|----------|--------------|-------------|
| 1 | 75 | 52.23 | 1.44 | Good |
| 2 | 75 | 53.44 | 1.40 | Good |
| 3 | 75 | 50.88 | 1.47 | Good |
| 4 | 75 | 49.96 | 1.50 | Excellent |
| 5 | 75 | 50.42 | 1.49 | Excellent |
| 6 | 75 | 51.34 | 1.46 | Good |
| 7 | 75 | 50.21 | 1.49 | Excellent |
| 8 | 75 | 49.11 | 1.53 | Peak |
| 9 | 55 | 37.46 | 1.47 | Good |

#### **Key Findings:**
- ✅ **100% Success Rate**: All 9 waves completed successfully
- ✅ **Consistent Performance**: Rate range 1.40-1.53 dev/s (excellent stability)
- ✅ **Better Than Expected**: 0.94 performance ratio (6% faster than predicted)
- ✅ **No Performance Degradation**: Consistent performance across all waves
- ✅ **Minimal Frontend Delays**: Only 4 seconds total delay time (8 × 500ms)

### 🔧 Wave Loading Implementation Details

#### **Frontend Caching Strategy:**
```javascript
let customFieldsCache = new Map();      // Cache successful results
let customFieldsLoading = new Set();    // Track devices currently loading

// Prevent duplicate requests
const devicesToLoad = deviceIds.filter(id => 
    !customFieldsCache.has(id) && !customFieldsLoading.has(id)
);
```

#### **Progress Tracking:**
```javascript
// Mark devices as loading
batch.forEach(id => customFieldsLoading.add(id));

// Update UI with progress
updateModalWithCustomFields(batch);

// Clean up loading state
batch.forEach(id => customFieldsLoading.delete(id));
```

#### **Error Resilience:**
```javascript
try {
    const response = await fetch('/api/custom-fields', {
        method: 'POST',
        body: JSON.stringify({ deviceIds: batch })
    });
    // Process successful response
} catch (error) {
    console.error('Failed to load batch:', batch, error);
    // Continue with next batch - don't fail entire operation
} finally {
    // Always clean up loading state
    batch.forEach(id => customFieldsLoading.delete(id));
}
```

### 📈 Performance Benefits

| Metric | Without Wave Loading | With Wave Loading |
|--------|---------------------|-------------------|
| **UI Responsiveness** | Freezes during load | Remains responsive |
| **API Success Rate** | ~60% (timeouts) | ~95% (reliable) |
| **Memory Usage** | High peak usage | Steady, controlled |
| **User Experience** | Long wait, no feedback | Progressive loading |
| **Error Recovery** | All-or-nothing | Graceful degradation |

### 🎯 Best Practices for Wave Loading

1. **Batch Size Tuning**:
   - Frontend: 10-15 devices (UI responsiveness)
   - Backend: 5-8 devices (API reliability)

2. **Delay Optimization**:
   - Frontend waves: 300-500ms (user perception)
   - Backend requests: 0.1-0.2s (API limits)

3. **Caching Strategy**:
   - Cache successful results permanently
   - Track loading state to prevent duplicates
   - Clear cache only on explicit refresh

4. **Error Handling**:
   - Continue processing on individual failures
   - Log errors for debugging
   - Provide user feedback on completion

5. **Progress Indication**:
   - Show loading states for individual devices
   - Update UI progressively as data arrives
   - Display completion statistics

---

## Dashboard Implementations

### BottomLeft Integration

The BottomLeft dashboard uses NinjaRMM for device count display:

#### Implementation
```python
def get_ninjarmm_device_count():
    """Return the total number of devices from NinjaRMM, excluding specific node classes, spare devices, and specific organizations."""
    try:
        # OAuth authentication
        token_url = f"{NINJA_BASE_URL}/oauth/token"
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': NINJA_REFRESH_TOKEN,
            'client_id': NINJA_CLIENT_ID,
            'client_secret': NINJA_CLIENT_SECRET,
        }
        
        # Get devices and apply filtering
        devices = get_devices_from_api()
        filtered_count = apply_device_filters(devices)
        
        return filtered_count
    except Exception as e:
        print(f'Error getting NinjaRMM device count: {e}')
        return 0
```

#### API Endpoint
```python
@app.route('/api/device-count')
def api_device_count():
    """API endpoint for device count"""
    try:
        count = get_ninjarmm_device_count()
        return jsonify({
            'count': count,
            'data_source': 'NinjaRMM API',
            'last_updated': datetime.utcnow().isoformat() + 'Z'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

### Ninja Seat Count Monthly Dashboard

Comprehensive organization usage analytics with full device management:

#### Core API Endpoints
```python
@app.route('/api/organization-usage', methods=['GET', 'POST'])
def api_organization_usage():
    """API endpoint for detailed organization usage data with timeout handling"""
    try:
        api = NinjaRMMAPI()
        usage_summary = api.get_organization_usage_summary(user_timezone)
        return jsonify(usage_summary)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/export-csv', methods=['GET', 'POST'])
def api_export_csv():
    """API endpoint for CSV export of organization usage data"""
    try:
        api = NinjaRMMAPI()
        usage_summary = api.get_organization_usage_summary(user_timezone)
        
        # Generate CSV with comprehensive device data
        csv_content = generate_csv_export(usage_summary)
        
        response = Response(csv_content, mimetype='text/csv')
        response.headers['Content-Disposition'] = f'attachment; filename=ninja-usage-{datetime.now().strftime("%Y%m%d-%H%M%S")}.csv'
        return response
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

#### Device Data Processing

**Step 1: Data Collection**
```python
def get_organization_usage_summary(self, user_timezone='UTC'):
    """Get comprehensive usage summary for all organizations with optimized API calls"""
    try:
        # Get all organizations and devices
        organizations = self.get_organizations()
        all_devices = self._get_devices_optimized()
```

**Step 2: Device Grouping**
```python
        # Group devices by organization
        org_devices = {}
        for device in all_devices:
            org_id = device['organizationId']
            if org_id not in org_devices:
                org_devices[org_id] = []
            org_devices[org_id].append(device)
```

**Step 3: Device Classification**
```python
        # Calculate usage for each organization
        usage_summary = []
        for org in organizations:
            org_id = org['id']
            org_device_list = org_devices.get(org_id, [])
            
            # Count devices by type and status
            servers = [d for d in org_device_list if d['deviceType'] == 'server']
            workstations = [d for d in org_device_list if d['deviceType'] == 'workstation']
            unknown_devices = [d for d in org_device_list if d['deviceType'] == 'unknown']
            virtualization_devices = [d for d in org_device_list if d['deviceType'] == 'virtualization']
```

**Step 4: Billable Status Calculation**
```python
            # Calculate billable vs spare
            billable_servers = [d for d in servers if d['billableStatus'] == 'billable']
            spare_servers = [d for d in servers if d['billableStatus'] == 'spare']
            billable_workstations = [d for d in workstations if d['billableStatus'] == 'billable']
            spare_workstations = [d for d in workstations if d['billableStatus'] == 'spare']
```

**Step 5: Organization Summary Creation**
```python
            org_usage = {
                'organization': org,
                'servers': {
                    'total': len(servers),
                    'billable': len(billable_servers),
                    'spare': len(spare_servers)
                },
                'workstations': {
                    'total': len(workstations),
                    'billable': len(billable_workstations),
                    'spare': len(spare_workstations)
                },
                'virtualization': {'total': len(virtualization_devices)},
                'unknown': {'total': len(unknown_devices)},
                'total_devices': len(org_device_list),
                'total_billable': len(billable_servers) + len(billable_workstations)
            }
            
            usage_summary.append(org_usage)
```

**Step 6: Final Response Assembly**
```python
        return {
            'organizations': usage_summary,
            'totals': calculate_overall_totals(usage_summary),
            'data_source': 'NinjaRMM API',
            'timezone': user_timezone,
            'last_updated': datetime.utcnow().isoformat() + 'Z'
        }
    except Exception as e:
        return handle_error_response(e, user_timezone)
```

---

## Error Handling & Troubleshooting

> **🔗 Related Sections**: [Authentication & Configuration](#authentication--configuration) | [Best Practices](#best-practices) | [Custom Fields Troubleshooting Guide](#custom-fields-troubleshooting-guide)

### Common Error Scenarios

#### 1. Authentication Failures
> **Quick Fix**: Check refresh token validity and OAuth configuration
```python
# Symptoms: 401 Unauthorized, token expiration
# Solutions:
try:
    access_token = self._get_access_token()
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 401:
        # Token expired, try refresh
        self.refresh_token = get_new_refresh_token()
        access_token = self._get_access_token()
```

#### 2. API Rate Limiting
> **Quick Fix**: Reduce batch size and add delays between requests
```python
# Symptoms: 429 Too Many Requests
# Solutions:
def _get_bulk_device_custom_fields(self, device_ids):
    # Process in smaller batches
    batch_size = 5
    for i in range(0, len(device_ids), batch_size):
        # Add delay between requests
        time.sleep(0.1)
```

#### 3. Timeout Issues
> **Quick Fix**: Use shorter timeouts and optimize data processing
```python
# Symptoms: Request timeout, worker timeout
# Solutions:
def _get_devices_optimized(self):
    # Use shorter timeout to prevent worker timeout
    response = requests.get(devices_url, headers=headers, timeout=30)
    
    # Process devices with minimal data processing
    processed_devices = []
    for device in all_devices:
        # Minimal device data structure for performance
        processed_device = {
            'id': device.get('id', 'N/A'),
            'organizationId': device.get('organizationId', 'N/A'),
            'deviceType': self._classify_device_type(device),
            'billableStatus': self._classify_billable_status(device),
            # ... minimal fields only
        }
```

#### 4. Custom Fields API Issues
> **Quick Fix**: Use correct endpoint `/api/v2/device/{device_id}/custom-fields` for VALUES
> **🔗 See**: [Custom Fields Integration](#custom-fields-integration) for detailed implementation

**Common Symptoms**: 404 Not Found, missing custom fields, empty responses

**✅ CORRECT Implementation**:
```python
def _get_device_custom_fields(self, device_id):
    try:
        # Use the correct endpoint for custom field VALUES
        custom_fields_url = f"{self.base_url}/api/v2/device/{device_id}/custom-fields"
        headers = self._get_api_headers()
        
        response = requests.get(custom_fields_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Returns dictionary of field_name: value pairs
        return response.json()
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            # Device may not have custom fields configured
            return {}
        raise
    except Exception as e:
        print(f"Error fetching custom fields for device {device_id}: {e}")
        return {}
```

**❌ WRONG Implementation**:
```python
def _get_device_custom_fields_wrong(self, device_id):
    # DON'T USE THIS - returns field definitions, not values
    custom_fields_url = f"{self.base_url}/api/v2/device-custom-fields?deviceId={device_id}"
```

#### 5. Frontend Custom Fields Integration Issues
```javascript
// Symptoms: All devices showing same custom field values, type mismatches
// Solutions:

// ✅ CORRECT: Handle type conversion for device ID comparison
function updateModalWithCustomFields(customFieldsData) {
    const rows = document.querySelectorAll('#deviceModalTable tbody tr');
    
    rows.forEach(row => {
        // Get device ID from data attribute (string)
        const deviceId = row.getAttribute('data-device-id');
        
        // Find matching custom fields data
        const deviceCustomFields = customFieldsData.find(item => {
            // Convert both to strings for comparison
            const deviceIds = item.deviceIds.map(id => String(id));
            return deviceIds.includes(String(deviceId));
        });
        
        if (deviceCustomFields) {
            // Update TPM/Secure Boot columns
            updateCustomFieldCell(row, 'tpm', deviceCustomFields.customFields.hastpm);
            updateCustomFieldCell(row, 'secureboot', deviceCustomFields.customFields.securebootenabled);
        }
    });
}

// ❌ WRONG: Type mismatch causes comparison failures
function updateModalWithCustomFields_wrong(customFieldsData) {
    const rows = document.querySelectorAll('#deviceModalTable tbody tr');
    
    rows.forEach(row => {
        const deviceId = row.getAttribute('data-device-id'); // string
        
        const deviceCustomFields = customFieldsData.find(item => {
            // This fails because deviceIds are numbers, deviceId is string
            return item.deviceIds.includes(deviceId); // [94, 99].includes("94") = false
        });
    });
}
```

### Error Response Handling
```python
def handle_error_response(self, error, user_timezone):
    """Handle API errors with obviously fake fallback data"""
    return {
        'organizations': [],
        'totals': {
            'servers': {'total': 999999, 'billable': 888888, 'spare': 777777},  # FAKE DATA - API Error
            'workstations': {'total': 666666, 'billable': 555555, 'spare': 444444},  # FAKE DATA - API Error
            'virtualization': {'total': 333333},  # FAKE DATA - API Error
            'unknown': {'total': 222222},  # FAKE DATA - API Error
            'total_devices': 1111111,  # FAKE DATA - API Error
            'total_billable': 999999  # FAKE DATA - API Error
        },
        'data_source': '🚨 FAKE DATA - API Error',
        'error': str(error),
        'last_updated': datetime.utcnow().isoformat() + 'Z',
        'timezone': user_timezone
    }
```

---

## Best Practices

### 1. Authentication Management
- **Use refresh tokens** for long-lived sessions
- **Implement token caching** to reduce API calls
- **Handle token expiration** gracefully with automatic refresh

### 2. API Call Optimization
- **Batch requests** when possible to reduce API calls
- **Implement caching** for frequently accessed data
- **Use appropriate timeouts** to prevent worker timeouts
- **Add delays** between requests to avoid rate limiting

### 3. Error Handling
- **Implement comprehensive error handling** for all API calls
- **Provide obviously fake fallback data** when APIs are unavailable (use impossible values like 999999, 888888)
- **Mark fallback data clearly** with "🚨 FAKE DATA" labels so users know it's not real
- **Log errors** for debugging and monitoring
- **Return meaningful error messages** to users

### 4. Data Processing
- **Classify devices consistently** using multiple criteria
- **Filter data appropriately** to exclude non-billable devices
- **Handle missing data gracefully** with default values
- **Validate data integrity** before processing

### 5. Performance Optimization
- **Use optimized endpoints** (devices-detailed vs devices)
- **Process data in batches** to avoid memory issues
- **Implement lazy loading** for large datasets
- **Cache frequently accessed data**

---

## Testing & Validation

### Unit Testing
```python
def test_ninja_api_authentication():
    """Test NinjaRMM API authentication"""
    api = NinjaRMMAPI()
    assert api._get_access_token() is not None

def test_device_classification():
    """Test device classification logic"""
    api = NinjaRMMAPI()
    
    # Test server classification
    server_device = {'platform': 'windows server', 'deviceType': 'server'}
    assert api._classify_device_type(server_device) == 'server'
    
    # Test workstation classification
    workstation_device = {'platform': 'windows desktop', 'deviceType': 'workstation'}
    assert api._classify_device_type(workstation_device) == 'workstation'
    
    # Test virtualization classification
    vm_device = {'deviceType': 'vmguest'}
    assert api._classify_device_type(vm_device) == 'virtualization'

def test_custom_fields_interpretation():
    """Test custom fields value interpretation"""
    api = NinjaRMMAPI()
    
    # Test boolean field interpretation
    assert api._interpret_tpm_secureboot_value('true', 'hastpm') == 'Yes'
    assert api._interpret_tpm_secureboot_value('false', 'hastpm') == 'No'
    assert api._interpret_tpm_secureboot_value('', 'hastpm') == 'Not Checked'
    
    # Test version field interpretation
    assert api._interpret_tpm_secureboot_value('2.0, 0, 1.38', 'tpmversion') == '2.0, 0, 1.38'
    assert api._interpret_tpm_secureboot_value('0.0', 'tpmversion') == 'No TPM'
```

### Integration Testing
```python
def test_organization_usage_summary():
    """Test organization usage summary generation"""
    api = NinjaRMMAPI()
    summary = api.get_organization_usage_summary('UTC')
    
    assert 'organizations' in summary
    assert 'totals' in summary
    assert 'data_source' in summary
    assert summary['data_source'] == 'NinjaRMM API'

def test_csv_export():
    """Test CSV export functionality"""
    api = NinjaRMMAPI()
    summary = api.get_organization_usage_summary('UTC')
    
    csv_content = generate_csv_export(summary)
    assert 'Organization' in csv_content
    assert 'Servers' in csv_content
    assert 'Workstations' in csv_content
```

### Manual Testing Scripts

#### Custom Fields Extraction
```bash
# Test custom fields extraction for specific device
python3 extract_tpm_secureboot_fields.py --device-id 2918 --device-name "ENR-GYV8Z23"

# Test custom fields extraction for all devices
python3 extract_tpm_secureboot_fields.py --all-devices
```

#### API Connectivity Testing
```bash
# Test API connectivity
python3 test_ninja_custom_fields_final.py

# Test dashboard integration
python3 test_focused_dashboard.py
```

### Validation Checklist

#### Authentication
- [ ] OAuth 2.0 authentication working
- [ ] Refresh token flow functional
- [ ] Client credentials fallback working
- [ ] Token expiration handling

#### Data Retrieval
- [ ] Organizations endpoint returning data
- [ ] Locations endpoint returning data
- [ ] Devices endpoint returning data
- [ ] Custom fields endpoint returning data

#### Data Processing
- [ ] Device classification working correctly
- [ ] Billable status classification working
- [ ] Device filtering excluding correct devices
- [ ] Custom fields interpretation working

#### Dashboard Integration
- [ ] BottomLeft dashboard showing device count
- [ ] Ninja Seat Count Monthly showing organization data
- [ ] CSV export generating correct data
- [ ] Modal display showing device details

#### Error Handling
- [ ] API errors handled gracefully
- [ ] Fallback data provided when APIs fail
- [ ] Timeout issues resolved
- [ ] Rate limiting handled

---

## Related Documentation

- [API Documentation](./API_DOCUMENTATION.md) - **AUTHORITATIVE** comprehensive API documentation for all integrations
- [Dashboard Standards](./DASHBOARD_STANDARDS.md) - Dashboard implementation standards
- [Development Guide](./DEVELOPMENT_GUIDE.md) - Development guidelines
- [Custom Fields Integration](#custom-fields-integration) - TPM & Secure Boot custom fields documentation

> **📖 Comprehensive API Documentation**: For complete API documentation including authentication methods, error handling, best practices, and troubleshooting procedures for all integrations (ConnectWise, Veeam VSPC, Veeam VBR, NinjaRMM, ThreatLocker, Fortigate), see [API Documentation](./API_DOCUMENTATION.md).

---

## Support & Maintenance

### Monitoring
- **API Response Times**: Monitor API call performance
- **Error Rates**: Track authentication and API errors
- **Data Quality**: Validate device classification accuracy
- **Custom Fields Population**: Monitor PowerShell script execution

### Maintenance Tasks
- **Token Refresh**: Ensure refresh tokens are updated before expiration
- **Custom Fields Validation**: Verify PowerShell scripts are running on devices
- **Device Classification Review**: Periodically review classification accuracy
- **API Endpoint Updates**: Monitor for NinjaRMM API changes

### Troubleshooting Resources
- **Container Logs**: `docker logs es-dashboards-ninja-usage`
- **API Test Scripts**: Use provided testing scripts for validation
- **Custom Fields Extractor**: Use for debugging custom fields issues
- **Error Logs**: Check application logs for detailed error information

### Custom Fields Troubleshooting Guide

#### Common Issues and Solutions

##### 1. All Devices Show Same Custom Field Values
**Symptoms**: Every device displays identical TPM/Secure Boot values  
**Root Cause**: Type mismatch in JavaScript device ID comparison  
**Solution**: Convert both device IDs to strings before comparison
```javascript
// ✅ CORRECT
const deviceIds = item.deviceIds.map(id => String(id));
return deviceIds.includes(String(deviceId));

// ❌ WRONG - causes type mismatch
return item.deviceIds.includes(deviceId);
```

##### 2. Custom Fields Show "Not Checked" for All Devices
**Symptoms**: All custom field columns display "Not Checked"  
**Root Cause**: Wrong API endpoint being used  
**Solution**: Use device-specific endpoint for values
```python
# ✅ CORRECT - Returns actual values
GET /api/v2/device/{device_id}/custom-fields

# ❌ WRONG - Returns field definitions only
GET /api/v2/device-custom-fields?deviceId={device_id}
```

##### 3. 401 Unauthorized Errors for Custom Fields
**Symptoms**: API returns 401 errors when fetching custom fields  
**Root Cause**: Authentication token issues or insufficient permissions  
**Solution**: Verify OAuth token and API permissions
```python
# Test authentication
def test_custom_fields_auth():
    api = NinjaRMMAPI()
    try:
        # Test with a known device ID
        custom_fields = api._get_device_custom_fields(device_id=123)
        print(f"Custom fields: {custom_fields}")
    except Exception as e:
        print(f"Auth error: {e}")
```

##### 4. Custom Fields API Returns Empty Objects
**Symptoms**: API calls succeed but return `{}`  
**Root Cause**: Device doesn't have custom fields configured or PowerShell scripts haven't run  
**Solution**: Verify PowerShell scripts are deployed and running
```bash
# Check if PowerShell scripts are running on devices
# Look for custom field data in NinjaRMM web interface
# Verify field names match exactly (case-sensitive)
```

##### 5. Frontend Modal Stuck Loading
**Symptoms**: Modal opens but never finishes loading custom fields  
**Root Cause**: JavaScript errors or API timeout  
**Solution**: Check browser console and implement proper error handling
```javascript
// Add comprehensive error handling
async function loadCustomFieldsForDevices(deviceIds) {
    try {
        const response = await fetch('/api/custom-fields', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ deviceIds })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        updateModalWithCustomFields(data);
        
    } catch (error) {
        console.error('Custom fields loading failed:', error);
        // Show user-friendly error message
        showCustomFieldsError('Failed to load custom fields data');
    }
}
```

##### 6. Modal Data Fields Missing or Incorrect
**Symptoms**: Modal shows "N/A" for fields that should have data, or displays wrong values  
**Root Cause**: Incorrect API path mapping or data transformation issues  
**Solution**: Verify field mapping and data transformation functions

```python
# Debug modal data extraction
def debug_modal_data(device):
    """Debug function to check modal data extraction"""
    print("=== MODAL DATA DEBUG ===")
    
    # Check basic fields
    print(f"System Name: {device.get('systemName', 'MISSING')}")
    print(f"Display Name: {device.get('displayName', 'MISSING')}")
    print(f"Status: {device.get('status', 'MISSING')}")
    
    # Check nested objects
    os_data = device.get('os', {})
    print(f"OS Name: {os_data.get('name', 'MISSING')}")
    print(f"OS Version: {os_data.get('version', 'MISSING')}")
    
    system_data = device.get('system', {})
    print(f"Manufacturer: {system_data.get('manufacturer', 'MISSING')}")
    print(f"Model: {system_data.get('model', 'MISSING')}")
    
    # Check processors
    processors = device.get('processors', [])
    if processors:
        print(f"CPU Model: {processors[0].get('name', 'MISSING')}")
        print(f"CPU Cores: {processors[0].get('numCores', 'MISSING')}")
    else:
        print("CPU: NO PROCESSORS FOUND")
    
    # Check memory
    memory = device.get('memory', 0)
    print(f"Memory (bytes): {memory}")
    print(f"Memory (GiB): {convert_to_gib(memory)}")
    
    # Check timestamps
    print(f"Last Contact: {device.get('lastContact', 'MISSING')}")
    print(f"Last Update: {device.get('lastUpdate', 'MISSING')}")
    
    return True
```

##### 7. Organization/Location Names Not Displaying
**Symptoms**: Modal shows organization/location IDs instead of names  
**Root Cause**: Missing organization/location lookup data  
**Solution**: Ensure organization and location APIs are called

```python
# Fix organization/location name display
def get_modal_data_with_names(device, organizations, locations):
    """Get modal data with proper organization/location names"""
    
    # Create lookup maps
    org_map = {org['id']: org['name'] for org in organizations}
    loc_map = {loc['id']: loc['name'] for loc in locations}
    
    modal_data = get_modal_device_data(device)
    
    # Add proper names
    modal_data['organizationName'] = org_map.get(device.get('organizationId'), 'N/A')
    modal_data['location'] = loc_map.get(device.get('locationId'), 'N/A')
    
    return modal_data
```

##### 8. Memory/Storage Data Formatting Issues
**Symptoms**: Memory shows as bytes instead of GiB, storage not formatted properly  
**Root Cause**: Missing data transformation functions  
**Solution**: Implement proper data transformation

```python
# Fix memory and storage formatting
def format_memory_display(memory_bytes):
    """Format memory for display"""
    if not memory_bytes or memory_bytes == 0:
        return 'N/A'
    
    # Convert to GiB
    gib = round(memory_bytes / (1024**3), 2)
    return f"{gib} GiB"

def format_storage_display(volumes):
    """Format storage volumes for display"""
    if not volumes:
        return 'N/A'
    
    formatted_volumes = []
    for volume in volumes:
        name = volume.get('name', 'Unknown')
        size_bytes = volume.get('size', 0)
        
        if size_bytes > 0:
            size_gb = round(size_bytes / (1024**3), 1)
            formatted_volumes.append(f"{name}: {size_gb}GB")
        else:
            formatted_volumes.append(f"{name}: Unknown Size")
    
    return ', '.join(formatted_volumes)
```

#### Testing Custom Fields Integration

##### Manual Testing Steps
1. **Verify API Endpoint**: Test custom fields endpoint directly
```bash
python3 test_fixed_custom_fields.py
```

2. **Check Frontend Integration**: Open browser console and monitor network requests
```javascript
// Look for these console messages:
// "🔍 [DEBUG] Enhanced showOrganizationDevices called"
// "🔍 [DEBUG] Updated X rows with custom fields data"
```

3. **Validate Data Mapping**: Ensure device IDs match between API and frontend
```javascript
// Check that device IDs are correctly extracted and compared
console.log('Device ID from HTML:', deviceId);
console.log('Device IDs from API:', deviceIds);
```

##### Automated Testing Scripts
```bash
# Test custom fields for specific device
python3 test_device_by_name.py

# Test bulk custom fields processing
python3 test_bulk_custom_fields.py

# Test all custom field endpoints
python3 test_all_custom_endpoints.py
```

---

## 📝 AI Assistant Summary

### Key Implementation Points
- **Authentication**: OAuth 2.0 with refresh token flow
- **Custom Fields**: Use device-specific endpoint for values, not definitions
- **Wave Loading**: Dual-layer batching (Frontend: 10 devices, Backend: 5 devices)
- **Error Handling**: Provide obviously fake fallback data (999999, 888888)
- **Rate Limiting**: 0.1s delay between requests, 500ms between frontend waves
- **Device Classification**: Multi-criteria classification (platform, deviceType, displayName)

### Most Common Issues
1. **Wrong Custom Fields Endpoint** → Use `/api/v2/device/{id}/custom-fields`
2. **Type Mismatches in Frontend** → Convert device IDs to strings for comparison
3. **Authentication Failures** → Check refresh token validity
4. **Rate Limiting** → Reduce batch sizes and add delays
5. **Timeout Issues** → Use shorter timeouts and optimize processing
6. **UI Freezing on Large Datasets** → Implement wave loading pattern
7. **Custom Fields Loading Failures** → Use dual-layer batching system

### Quick Testing Commands
```bash
# Test custom fields for specific device
python3 test_device_by_name.py

# Test API connectivity
python3 test_ninja_custom_fields_final.py

# Test dashboard integration
python3 test_focused_dashboard.py
```

---

*Last Updated: 2025-10-02*
*Version: 1.1 (AI-Optimized)*
*Maintained by: ES Dashboards Team*

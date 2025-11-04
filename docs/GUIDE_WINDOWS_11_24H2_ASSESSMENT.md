# Windows 11 24H2 Capability Assessment

## Overview

The Windows 11 24H2 Capability Assessment is an automated system that evaluates Windows devices for compatibility with Windows 11 24H2 based on Microsoft's hardware requirements. This assessment runs automatically after the Ninja collector completes data collection and provides detailed compatibility reports for IT administrators.

## Table of Contents

1. [Data Collection](#data-collection)
2. [Assessment Logic](#assessment-logic)
3. [Results Storage](#results-storage)
4. [API Integration](#api-integration)
5. [Automation](#automation)
6. [Usage Examples](#usage-examples)

## Data Collection

### Input Data Sources

The assessment relies on hardware data collected from the **NinjaRMM API** and stored in the `device_snapshot` table. The data collection process follows this flow:

```
NinjaRMM API → Ninja Collector → Database → Assessment Script → Results
```

### Required Fields

The assessment script retrieves the following fields from the `device_snapshot` table:

| Field | Type | Description | Source |
|-------|------|-------------|---------|
| `id` | Integer | Device ID | Database primary key |
| `hostname` | String | Device hostname | Ninja API: `system.name` |
| `os_architecture` | String | OS architecture (e.g., "64-bit") | Ninja API: `os.architecture` |
| `memory_gib` | Float | Total RAM in GiB | Ninja API: `memory.capacity` (converted) |
| `volumes` | String | Storage information with capacity | Ninja API: `volumes[]` array |
| `cpu_model` | String | CPU model (e.g., "Intel(R) Core(TM) i7-8565U") | Ninja API: `processors[].name` |
| `has_tpm` | Boolean | TPM presence indicator | Ninja API: Custom field or system detection |
| `tpm_enabled` | Boolean | TPM enabled status | Ninja API: Custom field or system detection |
| `tpm_version` | String | TPM version (e.g., "2.0, 1.38, 0") | Ninja API: Custom field or system detection |
| `secure_boot_available` | Boolean | Secure Boot support | Ninja API: Custom field or system detection |
| `secure_boot_enabled` | Boolean | Secure Boot enabled status | Ninja API: Custom field or system detection |
| `organization_name` | String | Organization name | Ninja API: `organization.name` |
| `display_name` | String | Device display name | Ninja API: `system.displayName` |

### Ninja API Data Mapping

The data is collected from the NinjaRMM API using the following mappings (as documented in `/opt/es-inventory-hub/docs/API_NINJA.md`):

#### CPU Information
- **API Path**: `processors[].name`
- **Example**: `"Intel(R) Core(TM) i7-8565U CPU @ 2.10GHz"`
- **Mapping**: Extracted via `_get_cpu_model()` function

#### Memory Information
- **API Path**: `memory.capacity`
- **Example**: `34292776960` (bytes)
- **Mapping**: Converted to GiB via `_convert_memory_to_gib()`

#### Storage Information
- **API Path**: `volumes[]` array
- **Example**: `[{"name": "C:", "capacity": 2999731613696}]`
- **Mapping**: Formatted as `"C: 2793.7GB"` via `_format_volumes()`

#### OS Architecture
- **API Path**: `os.architecture`
- **Example**: `"64-bit"`
- **Mapping**: Direct assignment

#### TPM and Secure Boot
- **API Path**: Custom fields or system detection
- **Mapping**: Extracted from device security features

## Assessment Logic

The Windows 11 24H2 assessment evaluates devices based on the following criteria:

### Pre-Assessment Checks

Before evaluating hardware requirements, the assessment performs these checks:

1. **Non-Windows Devices**: If the device is not running any version of Windows, the 24H2 assessment does not apply
2. **Windows Server**: If the device is running Windows Server, the 24H2 assessment does not apply  
3. **Already Installed**: If the device already has Windows 11 24H2 installed, it is automatically marked as compatible

### Hardware Requirements Assessment

For Windows client devices that don't already have Windows 11 24H2, the assessment evaluates **6 critical requirements** based on Microsoft's official hardware requirements:

### 1. 64-bit Operating System
- **Field**: `os_architecture`
- **Requirement**: Must be "64-bit"
- **Logic**: Direct string comparison
- **Status**: ✅ PASS / ❌ FAIL
- **Remediation**: Reinstall with 64-bit Windows

### 2. Memory (RAM) Requirement
- **Field**: `memory_gib`
- **Requirement**: ≥ 4 GiB (8 GiB recommended)
- **Logic**: Numeric comparison
- **Status**: ✅ PASS / ❌ FAIL / ⚠️ INSUFFICIENT_DATA
- **Remediation**: Add more RAM to meet minimum requirement

### 3. Storage Requirement
- **Field**: `volumes` (parsed for total capacity)
- **Requirement**: ≥ 64 GB
- **Logic**: Parse volume strings and sum capacity
- **Status**: ✅ PASS / ❌ FAIL / ⚠️ INSUFFICIENT_DATA
- **Remediation**: Add more storage or free up space

### 4. CPU Support Requirement
- **Field**: `cpu_model`
- **Requirements**:
  - **Intel**: 8th generation or newer (i7-8000+ series)
  - **Intel Core Ultra**: All series supported
  - **AMD**: Zen 2+ (Ryzen 3000/4000/5000+ series)
  - **Qualcomm**: Snapdragon processors
- **Logic**: Pattern matching and generation detection
- **Status**: ✅ PASS / ❌ FAIL
- **Remediation**: Hardware upgrade required

#### CPU Assessment Logic Details

```python
def assess_cpu_support(cpu_model: str) -> Tuple[bool, str]:
    # Intel CPU support (8th gen or newer)
    if 'intel' in cpu_lower:
        # Check for Intel Core Ultra series
        if 'ultra' in cpu_lower:
            return True, "Intel Core Ultra series meets requirement"
        
        # Parse CPU model number (e.g., i7-8565U)
        match = re.search(r'i[3579]-(\d{4})', cpu_model)
        if match:
            cpu_number = int(match.group(1))
            if cpu_number >= 8000:  # 8th gen or newer
                return True, f"Intel CPU {cpu_number} meets requirement"
            else:
                return False, f"Intel CPU {cpu_number} is below minimum requirement"
    
    # AMD CPU support (Zen 2+)
    elif 'amd' in cpu_lower or 'ryzen' in cpu_lower:
        if any(gen in cpu_lower for gen in ['3000', '4000', '5000', '6000', '7000']):
            return True, "AMD Ryzen generation meets requirement"
    
    # Qualcomm/ARM support
    elif 'qualcomm' in cpu_lower or 'snapdragon' in cpu_lower:
        return True, "Qualcomm Snapdragon meets requirement"
```

### 5. TPM 2.0 Requirement
- **Fields**: `has_tpm`, `tpm_enabled`, `tpm_version`
- **Requirements**:
  - TPM must be present (`has_tpm = true`)
  - TPM must be enabled (`tpm_enabled = true`)
  - TPM version must be 2.0 or higher
- **Logic**: Boolean checks and version parsing
- **Status**: ✅ PASS / ❌ FAIL
- **Remediation**: Enable TPM in BIOS/UEFI or hardware upgrade

### 6. Secure Boot Requirement
- **Fields**: `secure_boot_available`, `secure_boot_enabled`
- **Requirements**:
  - Secure Boot must be supported (`secure_boot_available = true`)
  - Secure Boot must be enabled (`secure_boot_enabled = true`)
- **Logic**: Boolean checks
- **Status**: ✅ PASS / ❌ FAIL
- **Remediation**: Enable Secure Boot in BIOS/UEFI or hardware upgrade

## Results Storage

### Database Schema

Assessment results are stored in the `device_snapshot` table with the following additional fields:

```sql
-- Windows 11 24H2 Assessment Fields
ALTER TABLE device_snapshot
ADD COLUMN windows_11_24h2_capable BOOLEAN DEFAULT NULL,
ADD COLUMN windows_11_24h2_deficiencies JSONB DEFAULT '{}';
```

### Result Structure

The `windows_11_24h2_deficiencies` field contains a JSONB object with the following structure:

```json
{
  "verdict": "Yes|No",
  "deficiencies": [
    {
      "requirement": "CPU Support",
      "status": "FAIL",
      "current_value": "Intel(R) Core(TM) i7-4600U",
      "required": "Intel 8th gen+, AMD Zen 2+, or Qualcomm Snapdragon",
      "reason": "Intel CPU 4600 is below minimum requirement (8th gen)",
      "remediation": "Hardware upgrade required - cannot be resolved via software"
    }
  ],
  "passed_requirements": [
    {
      "requirement": "64-bit OS",
      "status": "PASS",
      "current_value": "64-bit"
    }
  ],
  "assessment_date": "2025-10-03T00:52:25Z"
}
```

### Status Values

- **`verdict`**: Overall compatibility result
  - `"Yes"`: Device is compatible with Windows 11 24H2
  - `"No"`: Device is not compatible
  - `"N/A"`: Assessment does not apply (Windows Server or already has 24H2)
- **`status`**: Individual requirement status
  - `"PASS"`: Requirement met
  - `"FAIL"`: Requirement not met
  - `"INSUFFICIENT_DATA"`: Data not available for assessment
  - `"N/A"`: Not applicable (Windows Server or already installed)

## API Integration

### REST API Endpoints

The assessment results are exposed through the following API endpoints:

#### 1. Status Summary
- **Endpoint**: `GET /api/windows-11-24h2/status`
- **Description**: Get overall compatibility statistics
- **Response**:
```json
{
  "total_windows_devices": 634,
  "compatible_devices": 296,
  "incompatible_devices": 338,
  "not_assessed_devices": 0,
  "compatibility_rate": 46.7,
  "last_assessment": "2025-10-03T00:52:31Z"
}
```

#### 2. Incompatible Devices
- **Endpoint**: `GET /api/windows-11-24h2/incompatible`
- **Description**: Get list of incompatible devices with detailed deficiencies
- **Response**:
```json
[
  {
    "hostname": "ENERSYS-PC00FY6",
    "display_name": "ENERSYS-PC00FY6",
    "organization_name": "Example Corp",
    "os_name": "Windows 11 Professional",
    "cpu_model": "Intel(R) Core(TM) i7-4600U",
    "system_manufacturer": "Dell Inc.",
    "system_model": "OptiPlex 7090",
    "last_contact": "2025-10-05T16:28:26Z",
    "deficiencies": [
      {
        "requirement": "CPU Support",
        "status": "FAIL",
        "current_value": "Intel(R) Core(TM) i7-4600U",
        "required": "Intel 8th gen+, AMD Zen 2+, or Qualcomm Snapdragon",
        "reason": "Intel CPU 4600 is below minimum requirement (8th gen)",
        "remediation": "Hardware upgrade required - cannot be resolved via software"
      }
    ]
  }
]
```

#### 3. Compatible Devices
- **Endpoint**: `GET /api/windows-11-24h2/compatible`
- **Description**: Get list of compatible devices
- **Response**: Similar structure to incompatible devices but with `passed_requirements` array instead of `deficiencies`
- **Additional Fields**: Includes `cpu_model`, `last_contact`, `system_manufacturer`, and `system_model` fields for hardware and connectivity information

### **Date Field Distinctions:**
- **`last_contact`**: When the device was last online/active (from Ninja RMM)
- **`last_update`**: When we last updated this device record in our database
- **`assessment_date`**: When the Windows 11 24H2 compatibility assessment was performed

## Automation

### Systemd Service Configuration

The assessment runs automatically via systemd service and timer:

#### Service File: `/opt/es-inventory-hub/ops/systemd/windows-11-24h2-assessment.service`
```ini
[Unit]
Description=Windows 11 24H2 Capability Assessment
After=ninja-collector.service
Requires=ninja-collector.service

[Service]
Type=oneshot
User=postgres
Group=postgres
WorkingDirectory=/opt/es-inventory-hub
ExecStart=/opt/es-inventory-hub/.venv/bin/python3 /opt/es-inventory-hub/collectors/assessments/windows_11_24h2_assessment.py
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

#### Timer File: `/opt/es-inventory-hub/ops/systemd/windows-11-24h2-assessment.timer`
```ini
[Unit]
Description=Run Windows 11 24H2 Assessment 45 minutes after Ninja collection

[Timer]
OnCalendar=*-*-* 23:45:00
Persistent=true

[Install]
WantedBy=timers.target
```

### Execution Schedule

- **Trigger**: 45 minutes after Ninja collector completion
- **Frequency**: Daily at 23:45 (after 23:00 Ninja collection)
- **Dependencies**: Requires successful Ninja data collection

## Usage Examples

### Manual Assessment Execution

```bash
# Run assessment manually
cd /opt/es-inventory-hub
source .venv/bin/activate
python collectors/assessments/windows_11_24h2_assessment.py
```

### API Usage Examples

```bash
# Get compatibility status
curl https://db-api.enersystems.com:5400/api/windows-11-24h2/status

# Get incompatible devices
curl https://db-api.enersystems.com:5400/api/windows-11-24h2/incompatible

# Get compatible devices
curl https://db-api.enersystems.com:5400/api/windows-11-24h2/compatible
```

### Database Queries

```sql
-- Get all assessment results
SELECT hostname, windows_11_24h2_capable, windows_11_24h2_deficiencies
FROM device_snapshot
WHERE snapshot_date = CURRENT_DATE
AND windows_11_24h2_capable IS NOT NULL;

-- Get incompatible devices only
SELECT hostname, windows_11_24h2_deficiencies
FROM device_snapshot
WHERE windows_11_24h2_capable = false
AND snapshot_date = CURRENT_DATE;

-- Get compatibility statistics
SELECT
  COUNT(*) as total_devices,
  COUNT(CASE WHEN windows_11_24h2_capable = true THEN 1 END) as compatible,
  COUNT(CASE WHEN windows_11_24h2_capable = false THEN 1 END) as incompatible
FROM device_snapshot
WHERE snapshot_date = CURRENT_DATE
AND windows_11_24h2_capable IS NOT NULL;
```

## Troubleshooting

### Common Issues

1. **Hardware Data Missing**
   - Ensure Ninja collector is running successfully
   - Check that devices are online and reporting data
   - Verify Ninja API credentials and permissions

2. **Assessment Not Running**
   - Check systemd service status: `systemctl status windows-11-24h2-assessment.service`
   - Verify timer is enabled: `systemctl status windows-11-24h2-assessment.timer`
   - Check logs: `journalctl -u windows-11-24h2-assessment.service`

3. **Incorrect Results**
   - Verify hardware data is populated in database
   - Check assessment logic against Microsoft requirements
   - Review deficiency details for specific issues

### Log Files

- **Assessment Logs**: `/opt/es-inventory-hub/logs/windows_11_24h2_assessment.log`
- **Systemd Logs**: `journalctl -u windows-11-24h2-assessment.service`
- **Database Logs**: PostgreSQL logs in `/var/log/postgresql/`

## References

- [Microsoft Windows 11 System Requirements](https://www.microsoft.com/en-us/windows/windows-11-specifications)
- [NinjaRMM API Documentation](./API_NINJA.md)
- [Database Integration Guide](./GUIDE_DATABASE_INTEGRATION.md)

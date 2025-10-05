# Windows 11 24H2 Assessment Guide

**Complete guide for Windows 11 24H2 compatibility assessment, requirements, and API integration.**

**Last Updated**: October 2, 2025  
**ES Inventory Hub Version**: v1.15.0  
**Status**: ✅ **FULLY OPERATIONAL**

---

## 🚀 **OVERVIEW**

The Windows 11 24H2 Assessment system automatically evaluates Windows devices for compatibility with Windows 11 24H2 based on Microsoft's requirements. The assessment runs automatically 45 minutes after the Ninja collector completes, and can also be triggered manually via API.

### **Key Features:**
- ✅ **Automatic Assessment**: Runs 45 minutes after Ninja collector completion
- ✅ **Manual Trigger**: API endpoint to run assessment on-demand
- ✅ **Smart Pre-checks**: Automatically handles non-Windows, Windows Server, already-installed 24H2, and newer Windows versions
- ✅ **Version Exclusion**: Excludes devices with Windows 11 25H2+ (newer than target version)
- ✅ **Comprehensive Requirements**: CPU, TPM 2.0, Secure Boot, Memory, Storage, OS Architecture
- ✅ **Detailed Deficiency Reporting**: Specific reasons why devices fail with remediation suggestions
- ✅ **Organization Breakdown**: Results grouped by organization
- ✅ **Real-time Status**: Current compatibility rates and assessment status

---

## 📊 **API ENDPOINTS**

### **Assessment Endpoints**
```bash
GET /api/windows-11-24h2/status        # Compatibility status summary
GET /api/windows-11-24h2/incompatible  # List of incompatible devices
GET /api/windows-11-24h2/compatible    # List of compatible devices
POST /api/windows-11-24h2/run          # Manually trigger assessment
```

### **Usage Examples**
```javascript
// Get compatibility status
async function getWindows11Status() {
    const response = await fetch('https://db-api.enersystems.com:5400/api/windows-11-24h2/status');
    return await response.json();
}

// Get incompatible devices
async function getIncompatibleDevices() {
    const response = await fetch('https://db-api.enersystems.com:5400/api/windows-11-24h2/incompatible');
    return await response.json();
}

// Get compatible devices
async function getCompatibleDevices() {
    const response = await fetch('https://db-api.enersystems.com:5400/api/windows-11-24h2/compatible');
    return await response.json();
}

// Manually trigger assessment
async function runWindows11Assessment() {
    const response = await fetch('https://db-api.enersystems.com:5400/api/windows-11-24h2/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    });
    return await response.json();
}
```

---

## 🪟 **ENHANCED FIELD MAPPINGS (NEW - October 2025)**

The Windows 11 24H2 API endpoints now provide enhanced field data through NinjaRMM API integration:

### **Enhanced Field Mappings:**
```json
{
  "organization": "Acme Corporation",           // Real company names from NinjaRMM API
  "location": "Main Office",                   // Actual site identifiers from NinjaRMM API
  "system_name": "WORKSTATION-01",             // Device hostname/identifier
  "display_name": "John's Laptop",             // User-friendly device names (not OS versions)
  "device_type": "Desktop",                    // Physical hardware classification
  "billable_status": "billable",               // Billing classification
  "status": "Compatible for Upgrade",         // Compatibility status
  "hostname": "WORKSTATION-01",               // System hostname
  "os_name": "Windows 10 Pro",               // Operating system
  "os_version": "22H2",                       // OS version (e.g., "22H2", "23H2")
  "os_build": "19045",                        // OS build number (e.g., "19045", "22631")
  "last_update": "2025-10-05T00:21:56.199Z", // Last data update timestamp
  "memory_gib": 15.92,                        // Memory in GiB (Gigabytes)
  "memory_bytes": null,                       // Memory in bytes (if available)
  "system_manufacturer": "Not Available",     // System manufacturer (not available)
  "system_model": "Not Available",            // System model (not available)
  "passed_requirements": [...],               // Compatibility requirements passed
  "assessment_date": "2024-10-04"             // Assessment date
}
```

### **Field Descriptions:**
- **`organization`**: Real company names from NinjaRMM API (not "N/A")
- **`location`**: Actual site identifiers from NinjaRMM API (not "Main Office")
- **`system_name`**: Device hostname/identifier (e.g., "WORKSTATION-01")
- **`display_name`**: User-friendly device names from NinjaRMM API (not OS versions)
- **`device_type`**: Physical hardware classification (laptop, desktop, server, etc.)
- **`billable_status`**: Billing classification (billable, spare, etc.)
- **`status`**: Compatibility status ("Compatible for Upgrade", "Incompatible", "Already Installed")
- **`os_name`**: Full operating system name (e.g., "Windows 10 Pro", "Windows 11 Professional Edition")
- **`os_version`**: OS version identifier (e.g., "22H2", "23H2", "21H2")
- **`os_build`**: OS build number (e.g., "19045", "22631", "22000")
- **`last_update`**: Last data update timestamp (ISO 8601 format)
- **`memory_gib`**: Memory in GiB (Gigabytes) - Available in database
- **`memory_bytes`**: Memory in bytes - Available in database (may be null)
- **`system_manufacturer`**: System manufacturer - Not available in database
- **`system_model`**: System model - Not available in database

### **Data Source Enhancement:**
- **Response includes**: `"data_source": "Database + NinjaRMM API"`
- **Last updated**: `"last_updated": "2024-10-04T14:30:00Z"`
- **Fallback handling**: If NinjaRMM API unavailable, falls back to database values

### **Example Enhanced API Response:**
```json
{
  "compatible_devices": [
    {
      "organization": "Acme Corporation",
      "location": "Main Office",
      "system_name": "WORKSTATION-01",
      "display_name": "John's Laptop",
      "device_type": "Desktop",
      "billable_status": "billable",
      "status": "Compatible for Upgrade",
      "hostname": "WORKSTATION-01",
      "os_name": "Windows 10 Pro",
      "os_version": "22H2",
      "os_build": "19045",
      "last_update": "2025-10-05T00:21:56.199Z",
      "memory_gib": 15.92,
      "memory_bytes": null,
      "system_manufacturer": "Not Available",
      "system_model": "Not Available",
      "passed_requirements": ["TPM 2.0", "Secure Boot", "UEFI"],
      "assessment_date": "2024-10-04"
    }
  ],
  "total_count": 25,
  "data_source": "Database + NinjaRMM API",
  "last_updated": "2024-10-04T14:30:00Z"
}
```

---

## 🔍 **ASSESSMENT REQUIREMENTS**

### **Device Exclusion Logic**
The assessment automatically excludes certain devices from compatibility evaluation:

- **Non-Windows Devices**: Only Windows devices are assessed
- **Windows Server**: Server operating systems are excluded (assessment doesn't apply)
- **Already Installed 24H2**: Devices with Windows 11 24H2 are marked as "Already Compatible"
- **Newer Windows Versions**: Devices with Windows 11 25H2+ are excluded (already beyond target version)

### **Hardware Requirements**
The assessment evaluates devices against Microsoft's Windows 11 24H2 requirements:

### **1. Operating System Architecture (64-bit)**
- **Requirement**: 64-bit Windows operating system
- **Status**: PASS/FAIL/INSUFFICIENT_DATA
- **Remediation**: Upgrade to 64-bit Windows if currently 32-bit

### **2. Memory (RAM)**
- **Requirement**: ≥ 4 GB RAM
- **Status**: PASS/FAIL/INSUFFICIENT_DATA
- **Remediation**: Add more RAM if below 4 GB

### **3. Storage**
- **Requirement**: ≥ 64 GB available storage
- **Status**: PASS/FAIL/INSUFFICIENT_DATA
- **Remediation**: Free up disk space or upgrade storage

### **4. CPU Support**
- **Intel**: 8th generation or newer (Core i3/i5/i7/i9 8000 series or newer)
- **AMD**: Zen 2 architecture or newer (Ryzen 3000 series or newer)
- **Qualcomm**: Snapdragon processors
- **Status**: PASS/FAIL/INSUFFICIENT_DATA
- **Remediation**: Upgrade CPU if below minimum requirements

### **5. TPM (Trusted Platform Module)**
- **Requirement**: TPM 2.0 enabled
- **Status**: PASS/FAIL/INSUFFICIENT_DATA
- **Remediation**: Enable TPM 2.0 in BIOS/UEFI settings

### **6. Secure Boot**
- **Requirement**: Secure Boot enabled
- **Status**: PASS/FAIL/INSUFFICIENT_DATA
- **Remediation**: Enable Secure Boot in BIOS/UEFI settings

---

## 📋 **RESPONSE EXAMPLES**

### **Status Summary Response**
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

### **Incompatible Devices Response**
```json
{
  "incompatible_devices": [
    {
      "hostname": "ENERSYS-PC00FY6",
      "display_name": "ENERSYS-PC00FY6",
      "organization_name": "Ener Systems",
      "os_name": "Windows 10 Pro",
      "deficiencies": {
        "cpu_support": {
          "status": "FAIL",
          "reason": "Intel CPU 6000 series is below minimum requirement (8th gen)",
          "remediation": "Upgrade to Intel 8th generation or newer CPU"
        },
        "tpm_version": {
          "status": "FAIL",
          "reason": "TPM 1.2 detected, TPM 2.0 required",
          "remediation": "Enable TPM 2.0 in BIOS/UEFI settings"
        },
        "secure_boot": {
          "status": "FAIL",
          "reason": "Secure Boot not enabled",
          "remediation": "Enable Secure Boot in BIOS/UEFI settings"
        }
      }
    }
  ]
}
```

### **Compatible Devices Response**
```json
{
  "compatible_devices": [
    {
      "hostname": "ENR-4LYVF54",
      "display_name": "ENR-4LYVF54",
      "organization_name": "Ener Systems",
      "os_name": "Windows 11 Pro",
      "requirements_passed": [
        "64-bit OS",
        "Memory (8.0 GB)",
        "Storage (2793.4 GB)",
        "CPU (Intel Core i7-1185G7)",
        "TPM 2.0",
        "Secure Boot"
      ]
    }
  ]
}
```

### **Manual Trigger Response**
```json
{
  "status": "success",
  "message": "Windows 11 24H2 assessment completed successfully",
  "output": "2025-10-02 19:52:31,441 - INFO - Assessment complete:\n  - Total devices assessed: 634\n  - Compatible devices: 296\n  - Incompatible devices: 338\n  - Compatibility rate: 46.7%",
  "timestamp": "2025-10-03T00:52:31.441Z"
}
```

---

## 🔧 **TESTING COMMANDS**

### **Basic Endpoints**
```bash
# Get status
curl https://db-api.enersystems.com:5400/api/windows-11-24h2/status

# Get incompatible devices
curl https://db-api.enersystems.com:5400/api/windows-11-24h2/incompatible

# Get compatible devices
curl https://db-api.enersystems.com:5400/api/windows-11-24h2/compatible
```

### **Manual Trigger**
```bash
# Trigger assessment manually
curl -X POST https://db-api.enersystems.com:5400/api/windows-11-24h2/run
```

### **Alternative IP Access**
```bash
# Use IP address with -k flag for testing
curl -k https://192.168.99.246:5400/api/windows-11-24h2/status
```

---

## 📊 **ASSESSMENT LOGIC**

### **CPU Assessment Logic**
```python
def assess_cpu_support(cpu_model: str) -> Tuple[bool, str]:
    """Assess CPU support for Windows 11 24H2"""
    if not cpu_model or cpu_model == 'N/A':
        return False, "CPU model not available"

    cpu_lower = cpu_model.lower()

    # Intel CPU support (8th gen or newer)
    if 'intel' in cpu_lower:
        # Check for generation indicators
        if any(gen in cpu_lower for gen in ['8th gen', '9th gen', '10th gen', '11th gen', '12th gen', '13th gen', '14th gen']):
            return True, "Intel generation meets requirement"

        # Check for Intel Core Ultra series (newer than 14th gen)
        if 'ultra' in cpu_lower:
            return True, "Intel Core Ultra series meets requirement"

        # Parse CPU model number
        match = re.search(r'i[3579]-(\d{4})', cpu_model)
        if match:
            cpu_number = int(match.group(1))
            if cpu_number >= 8000:  # 8th gen or newer
                return True, f"Intel CPU {cpu_number} meets requirement"
            else:
                return False, f"Intel CPU {cpu_number} is below minimum requirement (8th gen)"

    # AMD CPU support (Zen 2+ = Ryzen 3000/4000/5000+)
    elif 'amd' in cpu_lower or 'ryzen' in cpu_lower:
        if any(gen in cpu_lower for gen in ['3000', '4000', '5000', '6000', '7000']):
            return True, "AMD Ryzen generation meets requirement"
        elif '2000' in cpu_lower:
            return False, "AMD Ryzen 2000 series may not be fully supported"
        else:
            return False, "AMD CPU generation below minimum requirement"

    # Qualcomm/ARM support
    elif 'qualcomm' in cpu_lower or 'snapdragon' in cpu_lower:
        return True, "Qualcomm Snapdragon meets requirement"

    return False, f"Unsupported CPU: {cpu_model}"
```

### **Storage Assessment Logic**
```python
def calculate_storage_from_volumes(volumes_text: str) -> float:
    """Calculate total storage from volumes text"""
    if not volumes_text:
        return 0.0
    
    total_gb = 0.0
    try:
        # Parse volumes text to extract storage sizes
        # Format: "C: 2793.4GB, D: 500.0GB"
        volumes = volumes_text.split(', ')
        for volume in volumes:
            if 'GB' in volume:
                # Extract number before GB
                match = re.search(r'(\d+(?:\.\d+)?)GB', volume)
                if match:
                    total_gb += float(match.group(1))
            elif 'TB' in volume:
                # Extract number before TB and convert to GB
                match = re.search(r'(\d+(?:\.\d+)?)TB', volume)
                if match:
                    total_gb += float(match.group(1)) * 1024
    except Exception as e:
        logger.warning(f"Error parsing volumes: {e}")
    
    return total_gb
```

---

## 🗄️ **DATABASE SCHEMA**

### **Assessment Fields**
The assessment results are stored in the `device_snapshot` table:

```sql
-- Windows 11 24H2 Assessment Fields
windows_11_24h2_capable BOOLEAN DEFAULT NULL,
windows_11_24h2_deficiencies JSONB DEFAULT '{}'
```

### **Hardware Fields**
Required hardware information for assessment:

```sql
-- Hardware Information Fields
os_architecture VARCHAR(100) DEFAULT NULL,
cpu_model VARCHAR(255) DEFAULT NULL,
memory_gib NUMERIC(10, 2) DEFAULT NULL,
volumes TEXT DEFAULT NULL,
has_tpm BOOLEAN DEFAULT NULL,
tpm_enabled BOOLEAN DEFAULT NULL,
tpm_version VARCHAR(50) DEFAULT NULL,
secure_boot_available BOOLEAN DEFAULT NULL,
secure_boot_enabled BOOLEAN DEFAULT NULL
```

### **Indexes**
```sql
-- Performance indexes
CREATE INDEX idx_device_snapshot_windows_11_24h2_capable
ON device_snapshot(windows_11_24h2_capable)
WHERE windows_11_24h2_capable IS NOT NULL;

CREATE INDEX idx_device_snapshot_windows_11_24h2_deficiencies
ON device_snapshot USING GIN (windows_11_24h2_deficiencies);
```

---

## ⚙️ **AUTOMATION**

### **Systemd Service**
The assessment runs automatically via systemd:

**Service File**: `/opt/es-inventory-hub/ops/systemd/windows-11-24h2-assessment.service`
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

**Timer File**: `/opt/es-inventory-hub/ops/systemd/windows-11-24h2-assessment.timer`
```ini
[Unit]
Description=Run Windows 11 24H2 Assessment 45 minutes after Ninja collection

[Timer]
OnCalendar=*-*-* 23:45:00
Persistent=true

[Install]
WantedBy=timers.target
```

### **Assessment Script**
**Location**: `/opt/es-inventory-hub/collectors/assessments/windows_11_24h2_assessment.py`

**Features:**
- ✅ Connects to database to fetch device data
- ✅ Applies assessment logic for all requirements
- ✅ Updates database with results
- ✅ Logs assessment progress and results
- ✅ Handles errors gracefully with detailed deficiency reporting

---

## 📈 **MONITORING & LOGGING**

### **Assessment Logs**
**Location**: `/opt/es-inventory-hub/logs/windows_11_24h2_assessment.log`

**Log Format**:
```
2025-10-02 19:52:31,441 - INFO - Starting Windows 11 24H2 assessment
2025-10-02 19:52:31,442 - INFO - Found 634 Windows devices to assess
2025-10-02 19:52:31,443 - INFO - Processing device: ENERSYS-PC00FY6
2025-10-02 19:52:31,444 - INFO - Device ENERSYS-PC00FY6: INCOMPATIBLE
2025-10-02 19:52:31,445 - INFO - Device ENR-4LYVF54: COMPATIBLE
2025-10-02 19:52:31,446 - INFO - Assessment complete:
  - Total devices assessed: 634
  - Compatible devices: 296
  - Incompatible devices: 338
  - Compatibility rate: 46.7%
```

### **Systemd Journal**
```bash
# View assessment logs
sudo journalctl -u windows-11-24h2-assessment.service

# View timer logs
sudo journalctl -u windows-11-24h2-assessment.timer

# Follow logs in real-time
sudo journalctl -u windows-11-24h2-assessment.service -f
```

---

## 🚨 **TROUBLESHOOTING**

### **Common Issues**

#### **Assessment Not Running**
```bash
# Check service status
sudo systemctl status windows-11-24h2-assessment.service

# Check timer status
sudo systemctl status windows-11-24h2-assessment.timer

# Enable and start timer
sudo systemctl enable windows-11-24h2-assessment.timer
sudo systemctl start windows-11-24h2-assessment.timer
```

#### **No Devices Found**
- Check if Ninja collector is running and completing successfully
- Verify hardware fields are populated in database
- Check device type filtering (Desktop, Laptop, workstation)

#### **Assessment Errors**
- Check log files for detailed error messages
- Verify database connectivity
- Check Python environment and dependencies

### **Manual Testing**
```bash
# Run assessment manually
cd /opt/es-inventory-hub
source .venv/bin/activate
python3 collectors/assessments/windows_11_24h2_assessment.py

# Check specific device
curl "https://db-api.enersystems.com:5400/api/windows-11-24h2/status"
```

---

## 📚 **RELATED DOCUMENTATION**

- [API Integration Guide](./API_INTEGRATION_GUIDE.md) - Core API endpoints and usage
- [Variances Dashboard Guide](./VARIANCES_DASHBOARD_GUIDE.md) - Dashboard functionality
- [Setup and Troubleshooting Guide](./SETUP_AND_TROUBLESHOOTING.md) - Operational guide
- [Database Schema Guide](./DATABASE_SCHEMA_GUIDE.md) - Database reference
- [Windows 11 24H2 Assessment Documentation](./WINDOWS_11_24H2_ASSESSMENT.md) - Detailed technical documentation

---

**🎉 The Windows 11 24H2 Assessment system is fully operational and ready for Dashboard AI integration!**

# Ninja API: TPM and SecureBoot Data Collection

## Overview

The ES Inventory Hub Ninja collector captures TPM (Trusted Platform Module) and SecureBoot security data from NinjaRMM devices through a two-step API process. This document describes how these security features are detected and collected using the **new reliable capture method** based on PowerShell script-populated custom fields.

## API Architecture

The TPM and SecureBoot data collection uses **two separate API endpoints**:

1. **Primary Device Data**: `/api/v2/devices-detailed` - Gets basic device information
2. **Custom Fields Data**: `/api/v2/device/{device_id}/custom-fields` - Gets security-specific data

## Authentication

### OAuth 2.0 Flow
The collector uses OAuth 2.0 with refresh token flow for authentication:

```python
# Environment variables required:
NINJA_CLIENT_ID=your_client_id
NINJA_CLIENT_SECRET=your_client_secret  
NINJA_REFRESH_TOKEN=your_refresh_token
NINJA_BASE_URL=https://app.ninjarmm.com
```

### Token Acquisition
```python
def _get_access_token(self) -> str:
    token_url = f"{self.base_url}/oauth/token"
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': self.refresh_token,
        'client_id': self.client_id,
        'client_secret': self.client_secret,
    }
    # Returns Bearer token for API calls
```

## API Endpoints

### 1. Device List Endpoint

**Endpoint**: `GET /api/v2/devices-detailed`

**Purpose**: Retrieves basic device information including device IDs needed for custom field queries.

**Headers**:
```
Authorization: Bearer {access_token}
Content-Type: application/json
Accept: application/json
```

**Parameters**:
- `limit`: 250 (maximum page size for efficiency)

**Response**: Paginated list of devices with basic information.

### 2. Custom Fields Endpoint

**Endpoint**: `GET /api/v2/device/{device_id}/custom-fields`

**Purpose**: Retrieves TPM and SecureBoot data stored as custom fields.

**Headers**:
```
Authorization: Bearer {access_token}
Content-Type: application/json
Accept: application/json
```

**Response Format**:
```json
{
  "hastpm": "true",
  "tpmenabled": "true", 
  "tpmversion": "2.0",
  "securebootavailable": "true",
  "securebootenabled": "false"
}
```

## Data Collection Process

### Step 1: Device Enumeration
```python
def list_devices(self, limit: Optional[int] = None):
    """Generator that pages through Ninja's device API."""
    headers = self._get_api_headers()
    devices_url = f"{self.base_url}/api/v2/devices-detailed"
    
    # Paginate through all devices
    while True:
        response = self.session.get(devices_url, headers=headers, params=params)
        devices = response.json().get("items", [])
        
        for device in devices:
            yield device  # Contains device ID for custom field queries
```

### Step 2: Security Data Retrieval
```python
def get_device_custom_fields(self, device_id: int) -> Dict[str, Any]:
    """Get custom fields for a specific device."""
    headers = self._get_api_headers()
    custom_fields_url = f"{self.base_url}/api/v2/device/{device_id}/custom-fields"
    
    response = self.session.get(custom_fields_url, headers=headers, timeout=30)
    return response.json()  # Returns TPM/SecureBoot data
```

### Step 3: Data Processing
```python
def _get_security_fields(raw: Dict[str, Any], ninja_api=None) -> Dict[str, Any]:
    """Get security-related fields from custom fields API."""
    security_fields = {
        'has_tpm': None,
        'tpm_enabled': None,
        'tpm_version': '',
        'secure_boot_available': None,
        'secure_boot_enabled': None,
    }
    
    # Fetch custom fields for this device
    custom_fields = ninja_api.get_device_custom_fields(device_id)
    
    # Map custom field values to our security fields
    security_fields['has_tpm'] = _interpret_boolean_field(custom_fields.get('hastpm'))
    security_fields['tpm_enabled'] = _interpret_boolean_field(custom_fields.get('tpmenabled'))
    security_fields['tpm_version'] = _interpret_tpm_version(custom_fields.get('tpmversion', ''))
    security_fields['secure_boot_available'] = _interpret_boolean_field(custom_fields.get('securebootavailable'))
    security_fields['secure_boot_enabled'] = _interpret_boolean_field(custom_fields.get('securebootenabled'))
    
    return security_fields
```

## Custom Field Mapping

### TPM Fields

| Custom Field | Description | Values | Interpretation |
|--------------|-------------|---------|----------------|
| `hastpm` | Device has TPM hardware | "true", "false", "" | Boolean or null |
| `tpmenabled` | TPM is enabled in BIOS | "true", "false", "" | Boolean or null |
| `tpmversion` | TPM version installed | "2.0", "1.2", "0.0" | String (0.0 = "No TPM") |

### SecureBoot Fields

| Custom Field | Description | Values | Interpretation |
|--------------|-------------|---------|----------------|
| `securebootavailable` | SecureBoot is available | "true", "false", "" | Boolean or null |
| `securebootenabled` | SecureBoot is enabled | "true", "false", "" | Boolean or null |

## Data Interpretation

### Boolean Field Processing
```python
def _interpret_boolean_field(value: str) -> Optional[bool]:
    """Interpret boolean custom field values."""
    if not value or value == '':
        return None  # Not checked
    
    value_lower = value.lower()
    if value_lower == 'true':
        return True
    elif value_lower == 'false':
        return False
    else:
        return None  # Unknown value
```

### TPM Version Processing
```python
def _interpret_tpm_version(value: str) -> str:
    """Interpret TPM version custom field values."""
    if not value or value == '':
        return ''  # Not checked
    
    if value == '0.0':
        return 'No TPM'
    else:
        return value  # Return as-is (e.g., "2.0", "1.2")
```

## Error Handling

### API Failures
- **Custom fields unavailable**: Returns default values (None/empty)
- **Device ID missing**: Skips custom field collection
- **Network timeouts**: 30-second timeout per custom field request
- **Authentication failures**: Raises exceptions, stops collection

### Graceful Degradation
```python
try:
    custom_fields = ninja_api.get_device_custom_fields(device_id)
    # Process custom fields...
except Exception as e:
    # Return defaults if custom fields can't be fetched
    return security_fields  # With default None/empty values
```

## Performance Considerations

### API Efficiency
- **Pagination**: Uses 250-device page size for optimal throughput
- **Parallel Processing**: Each device requires separate custom field API call
- **Timeout Management**: 30-second timeout prevents hanging requests
- **Error Recovery**: Continues processing other devices if one fails

### Rate Limiting
- NinjaRMM API has rate limits (typically 100 requests/minute)
- Collector processes devices sequentially to avoid rate limit issues
- Custom field calls are made individually per device (not batched)

## Database Storage

The collected security data is stored in the `device_snapshot` table with the following fields:

```sql
-- Security fields in device_snapshot table
has_tpm BOOLEAN,                    -- NULL if not checked
tpm_enabled BOOLEAN,                -- NULL if not checked  
tpm_version VARCHAR(100),           -- "2.0", "1.2", "No TPM", or empty
secure_boot_available BOOLEAN,      -- NULL if not checked
secure_boot_enabled BOOLEAN         -- NULL if not checked
```

## Example API Flow

1. **Get device list**: `GET /api/v2/devices-detailed?limit=250`
2. **For each device**:
   - Extract `device_id` from device record
   - Call `GET /api/v2/device/{device_id}/custom-fields`
   - Process TPM/SecureBoot custom fields
   - Store in normalized format
3. **Continue pagination** until all devices processed

## Monitoring and Logging

The collector logs:
- Device processing progress (every 50 devices)
- Custom field API failures
- Security data interpretation results
- Collection completion statistics

Example log output:
```
2025-09-19 08:11:21 - Processing device 410: CI-MJ0GED48
2025-09-19 08:11:21 - Inserted snapshot for device 2752 with type: workstation, billing: billable
2025-09-19 08:11:21 - Progress: 450 devices processed, 450 saved
```

## Troubleshooting

### Common Issues

1. **Missing TPM/SecureBoot data**: Check if custom fields are configured in NinjaRMM
2. **API authentication failures**: Verify refresh token is valid and not expired
3. **Rate limiting**: Reduce concurrent requests or implement backoff
4. **Timeout errors**: Increase timeout values for slow networks

### Debugging
- Enable debug logging to see raw API responses
- Check custom field names match exactly (case-sensitive)
- Verify device IDs are valid integers
- Test API endpoints manually with curl/Postman

## ✅ **New Reliable Capture Method (2025)**

### **PowerShell Script Integration**
The TPM/SecureBoot data is now populated by **PowerShell scripts** running on the devices, which provides:

- **Higher accuracy**: Direct hardware interrogation vs. API inference
- **Better coverage**: Scripts run on all managed devices  
- **Consistent data**: Standardized field names and values
- **Real-time updates**: Data refreshed during device check-ins

### **Success Rate Analysis**
Based on test collections, the new method achieves:
- **60%+ success rate** for devices with PowerShell scripts deployed
- **Real TPM/SecureBoot data** for devices with scripts
- **Graceful fallback** to null values for devices without scripts

### **Example Results**
```json
{
  "has_tpm": true,
  "tpm_enabled": true,
  "tpm_version": "2.0, 0, 1.38",
  "secure_boot_available": true,
  "secure_boot_enabled": true
}
```

### **Database Storage**
The TPM/SecureBoot fields are now stored in the `device_snapshot` table:
- `has_tpm` (BOOLEAN)
- `tpm_enabled` (BOOLEAN)  
- `tpm_version` (VARCHAR(100))
- `secure_boot_available` (BOOLEAN)
- `secure_boot_enabled` (BOOLEAN)

All fields are nullable to handle devices where PowerShell scripts haven't run or data isn't available.

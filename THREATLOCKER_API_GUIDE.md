# ThreatLocker API Guide: Accessing Computer Details

## Overview

This guide explains how to access the ThreatLocker API to retrieve comprehensive computer details that are displayed in the dashboard modals. The ThreatLocker dashboard shows detailed computer information including security status, deny counts, operating systems, and more.

## API Authentication

### Environment Variables Required

The ThreatLocker API requires the following environment variables to be set in your `.env` file:

```bash
# ThreatLocker API Configuration
THREATLOCKER_API_KEY=your_threatlocker_api_key_here
THREATLOCKER_ORGANIZATION_ID=your_main_organization_id_here
```

### Authentication Headers

The API uses a simple API key authentication method:

```python
headers = {
    "authorization": api_key,  # Lowercase, no 'Bearer' prefix
    "content-type": "application/json"  # Lowercase
}

# Add organization ID if needed
if organization_id:
    headers["managedorganizationid"] = organization_id
```

## Base URL

```python
base_url = "https://portalapi.g.threatlocker.com"
```

## Computer Data Endpoints

### 1. Get All Computers (Main Organization)

**Endpoint:** `POST /portalApi/Computer/ComputerGetByAllParameters`

**Purpose:** Retrieve all computers from the main organization with comprehensive details.

**Request:**
```python
url = f"{base_url}/portalApi/Computer/ComputerGetByAllParameters"

data = {
    "pageSize": 500,
    "pageNumber": 1,
    "searchText": "",
    "orderBy": "lastcheckin",
    "childOrganizations": False,
    "showLastCheckIn": True
}

response = requests.post(url, headers=headers, json=data, timeout=30)
```

**Response Fields Available:**
```json
{
  "computerName": "DESKTOP-ABC123",
  "hostname": "DESKTOP-ABC123",
  "group": "Default Group",
  "operatingSystem": "Windows 10 Pro",
  "mode": "Learning",
  "lastCheckin": "2025-09-01T02:15:57.435815Z",
  "denyCountOneDay": 5,
  "denyCountThreeDays": 23,
  "denyCountSevenDays": 89,
  "organizationId": "dd850352-ee85-436b-8e41-818bdb52712c",
  "computerId": "12345678-1234-1234-1234-123456789012",
  "ipAddress": "192.168.1.100",
  "macAddress": "00:11:22:33:44:55",
  "username": "DOMAIN\\username",
  "isOnline": true,
  "isLockedOut": false,
  "isIsolated": false,
  "hasUnknownVersion": false,
  "targetThreatLockerVersion": "10.3.4",
  "isDeleted": false
}
```

### 2. Get Computers by Specific Organization

**Endpoint:** `POST /portalApi/Computer/ComputerGetByAllParameters`

**Purpose:** Retrieve computers for a specific organization by setting the organization ID in headers.

**Request:**
```python
# Set organization ID in headers
headers_with_org = headers.copy()
headers_with_org["managedorganizationid"] = organization_id

data = {
    "pageSize": 500,
    "pageNumber": 1,
    "searchText": "",
    "orderBy": "lastcheckin",
    "childOrganizations": False,
    "showLastCheckIn": True
}

response = requests.post(url, headers=headers_with_org, json=data, timeout=30)
```

### 3. Get All Computers from All Child Organizations

**Endpoint:** `POST /portalApi/Computer/ComputerGetByAllParameters`

**Purpose:** Retrieve computers from all child organizations in a single call.

**Request:**
```python
data = {
    "pageSize": 500,
    "pageNumber": 1,
    "searchText": "",
    "orderBy": "lastcheckin",
    "childOrganizations": True,  # Key difference
    "showLastCheckIn": True
}

response = requests.post(url, headers=headers, json=data, timeout=30)
```

## Computer Analytics Data

### Computer Analytics Endpoint

**Endpoint:** `/api/computer-analytics/{organization_id}`

**Purpose:** Get aggregated analytics for computers in a specific organization.

**Response:**
```json
{
  "status": "success",
  "data": {
    "total_computers": 43,
    "computer_groups": {
      "Default Group": 35,
      "Servers": 8
    },
    "operating_systems": {
      "Windows 10 Pro": 25,
      "Windows 11 Pro": 12,
      "Windows Server 2019": 6
    },
    "security_status": {
      "Learning": 30,
      "Enforcement": 13
    },
    "recent_activity": 28,
    "deny_counts": {
      "one_day": 156,
      "three_days": 892,
      "seven_days": 2341
    }
  }
}
```

## Organization Data

### Get Organizations with Computer Counts

**Endpoint:** `POST /portalApi/Organization/OrganizationGetChildOrganizationsByParameters`

**Purpose:** Retrieve all organizations with their computer counts and deny statistics.

**Request:**
```python
url = f"{base_url}/portalApi/Organization/OrganizationGetChildOrganizationsByParameters"

data = {
    "pageSize": 25,
    "pageNumber": 1,
    "includeProductBundles": False
}

response = requests.post(url, headers=headers, json=data, timeout=30)
```

**Response Fields:**
```json
{
  "organizationId": "dd850352-ee85-436b-8e41-818bdb52712c",
  "displayName": "Ener Systems",
  "name": "ener-systems",
  "computerCount": 43,
  "activeCount": 0,
  "dateAdded": "2021-01-01T00:00:00Z",
  "computerDenyCountDtos": [
    {
      "oneDay": 156,
      "threeDays": 892,
      "sevenDays": 2341,
      "organizationId": "dd850352-ee85-436b-8e41-818bdb52712c"
    }
  ],
  "products": [
    {
      "name": "defaultdeny",
      "displayName": "Allowlisting",
      "isThreatLockerProtect": true
    },
    {
      "name": "ringfencing",
      "displayName": "Ringfencing",
      "isThreatLockerProtect": true
    }
  ]
}
```

## Complete Python Implementation

### ThreatLocker API Client Class

```python
#!/usr/bin/env python3
"""
ThreatLocker API Client for Computer Details
"""

import requests
import json
from datetime import datetime
from typing import Dict, Any, Optional
import os

class ThreatLockerAPIClient:
    """ThreatLocker API client for computer data retrieval"""
    
    def __init__(self):
        # Load environment variables
        from dotenv import load_dotenv
        load_dotenv()
        
        self.base_url = "https://portalapi.g.threatlocker.com"
        self.api_key = os.getenv("THREATLOCKER_API_KEY", "")
        self.organization_id = os.getenv("THREATLOCKER_ORGANIZATION_ID", "")
        
        # Headers for API requests
        self.headers = {
            "authorization": self.api_key,
            "content-type": "application/json"
        }
        
        if self.organization_id:
            self.headers["managedorganizationid"] = self.organization_id
    
    def get_computers(self, organization_id: Optional[str] = None) -> Dict[str, Any]:
        """Get list of computers with full details"""
        try:
            url = f"{self.base_url}/portalApi/Computer/ComputerGetByAllParameters"
            
            # Headers with optional organization ID override
            headers = self.headers.copy()
            if organization_id:
                headers["managedorganizationid"] = organization_id
            
            data = {
                "pageSize": 500,
                "pageNumber": 1,
                "searchText": "",
                "orderBy": "lastcheckin",
                "childOrganizations": False,
                "showLastCheckIn": True
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                computers = response.json()
                return {
                    "status": "success",
                    "data": computers,
                    "count": len(computers),
                    "organization_id": organization_id or self.organization_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to get computers: {response.status_code}",
                    "status_code": response.status_code,
                    "error": response.text,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error getting computers: {str(e)}",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def get_all_computers_with_child_organizations(self) -> Dict[str, Any]:
        """Get all computers from all child organizations"""
        try:
            url = f"{self.base_url}/portalApi/Computer/ComputerGetByAllParameters"
            
            data = {
                "pageSize": 500,
                "pageNumber": 1,
                "searchText": "",
                "orderBy": "lastcheckin",
                "childOrganizations": True,  # Get all child org computers
                "showLastCheckIn": True
            }
            
            response = requests.post(url, headers=self.headers, json=data, timeout=30)
            
            if response.status_code == 200:
                computers = response.json()
                return {
                    "status": "success",
                    "data": computers,
                    "count": len(computers),
                    "message": "All computers from all child organizations retrieved",
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to get all computers: {response.status_code}",
                    "status_code": response.status_code,
                    "error": response.text,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error getting all computers: {str(e)}",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def get_organizations(self) -> Dict[str, Any]:
        """Get list of organizations with computer counts"""
        try:
            url = f"{self.base_url}/portalApi/Organization/OrganizationGetChildOrganizationsByParameters"
            
            all_organizations = []
            page_number = 1
            page_size = 25
            
            while True:
                data = {
                    "pageSize": page_size,
                    "pageNumber": page_number,
                    "includeProductBundles": False
                }
                
                response = requests.post(url, headers=self.headers, json=data, timeout=30)
                
                if response.status_code == 200:
                    response_data = response.json()
                    
                    if isinstance(response_data, list):
                        organizations = response_data
                    elif isinstance(response_data, dict) and 'data' in response_data:
                        organizations = response_data['data']
                    else:
                        organizations = []
                    
                    if not organizations:
                        break
                    
                    all_organizations.extend(organizations)
                    
                    if len(organizations) < page_size:
                        break
                    
                    page_number += 1
                else:
                    return {
                        "status": "error",
                        "message": f"Failed to get organizations - Status {response.status_code}",
                        "status_code": response.status_code,
                        "error": response.text,
                        "timestamp": datetime.utcnow().isoformat()
                    }
            
            return {
                "status": "success",
                "message": f"Organizations retrieved successfully (Total: {len(all_organizations)})",
                "status_code": 200,
                "data": all_organizations,
                "timestamp": datetime.utcnow().isoformat()
            }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error getting organizations: {str(e)}",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def test_authentication(self) -> Dict[str, Any]:
        """Test API authentication and connectivity"""
        try:
            url = f"{self.base_url}/portalApi/Organization/OrganizationGetChildOrganizationsByParameters"
            
            data = {
                "pageSize": 25,
                "pageNumber": 1,
                "includeProductBundles": False
            }
            
            response = requests.post(url, headers=self.headers, json=data, timeout=30)
            
            if response.status_code == 200:
                return {
                    "status": "success",
                    "message": "Authentication successful",
                    "status_code": response.status_code,
                    "data": response.json() if response.content else None,
                    "timestamp": datetime.utcnow().isoformat()
                }
            elif response.status_code == 401:
                return {
                    "status": "error",
                    "message": "Authentication failed - Invalid API key",
                    "status_code": response.status_code,
                    "error": "Unauthorized",
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                return {
                    "status": "error",
                    "message": f"API request failed with status {response.status_code}",
                    "status_code": response.status_code,
                    "error": response.text,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Unexpected error: {str(e)}",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

# Example Usage
def main():
    """Example usage of the ThreatLocker API client"""
    client = ThreatLockerAPIClient()
    
    # Test authentication
    print("Testing authentication...")
    auth_result = client.test_authentication()
    print(f"Auth status: {auth_result['status']}")
    
    if auth_result['status'] == 'success':
        # Get organizations
        print("\nGetting organizations...")
        orgs_result = client.get_organizations()
        if orgs_result['status'] == 'success':
            print(f"Found {len(orgs_result['data'])} organizations")
            
            # Get computers for first organization
            if orgs_result['data']:
                first_org = orgs_result['data'][0]
                org_id = first_org['organizationId']
                org_name = first_org['displayName']
                
                print(f"\nGetting computers for {org_name}...")
                computers_result = client.get_computers(org_id)
                if computers_result['status'] == 'success':
                    print(f"Found {computers_result['count']} computers")
                    
                    # Show first computer details
                    if computers_result['data']:
                        first_computer = computers_result['data'][0]
                        print(f"\nFirst computer details:")
                        print(f"  Name: {first_computer.get('computerName', 'Unknown')}")
                        print(f"  OS: {first_computer.get('operatingSystem', 'Unknown')}")
                        print(f"  Mode: {first_computer.get('mode', 'Unknown')}")
                        print(f"  Last Checkin: {first_computer.get('lastCheckin', 'Never')}")
                        print(f"  Deny Count (1 day): {first_computer.get('denyCountOneDay', 0)}")
                        print(f"  Deny Count (3 days): {first_computer.get('denyCountThreeDays', 0)}")
                        print(f"  Deny Count (7 days): {first_computer.get('denyCountSevenDays', 0)}")

if __name__ == "__main__":
    main()
```

## Dashboard Modal Data Structure

### Computer Details Displayed in Modals

The dashboard modals display the following computer information:

1. **Basic Information:**
   - Computer Name
   - Hostname
   - Group
   - Operating System
   - Security Mode (Learning/Enforcement)

2. **Activity Information:**
   - Last Check-in Time
   - Online Status
   - Lockout Status
   - Isolation Status

3. **Security Metrics:**
   - Deny Count (1 day)
   - Deny Count (3 days)
   - Deny Count (7 days)
   - ThreatLocker Version

4. **Network Information:**
   - IP Address
   - MAC Address
   - Username

5. **Analytics Aggregated by:**
   - Operating Systems
   - Security Status
   - Computer Groups
   - Deny Counts (totaled)

## Error Handling

### Common Error Responses

1. **401 Unauthorized:**
   - Invalid API key
   - Check `THREATLOCKER_API_KEY` environment variable

2. **403 Forbidden:**
   - Invalid organization ID
   - Insufficient permissions
   - Check `THREATLOCKER_ORGANIZATION_ID` environment variable

3. **404 Not Found:**
   - Endpoint not found
   - Organization doesn't exist

4. **500 Internal Server Error:**
   - Server-side issue
   - Try again later

### Best Practices

1. **Always test authentication first** before making other API calls
2. **Use pagination** for large datasets (default page size is 500)
3. **Handle timeouts** (recommended 30 seconds)
4. **Cache organization data** to avoid repeated calls
5. **Use childOrganizations=True** to get all computers across all organizations
6. **Format dates properly** for display (lastCheckin is in ISO format)

## Testing the API

### Quick Test Script

```python
# Quick test to verify API access
import os
from dotenv import load_dotenv
import requests

load_dotenv()

api_key = os.getenv("THREATLOCKER_API_KEY")
org_id = os.getenv("THREATLOCKER_ORGANIZATION_ID")

headers = {
    "authorization": api_key,
    "content-type": "application/json"
}

if org_id:
    headers["managedorganizationid"] = org_id

# Test authentication
url = "https://portalapi.g.threatlocker.com/portalApi/Organization/OrganizationGetChildOrganizationsByParameters"
data = {"pageSize": 1, "pageNumber": 1, "includeProductBundles": False}

response = requests.post(url, headers=headers, json=data, timeout=30)
print(f"Status: {response.status_code}")
print(f"Response: {response.json() if response.status_code == 200 else response.text}")
```

This guide provides everything needed to access the ThreatLocker API and retrieve the computer details that are displayed in the dashboard modals.

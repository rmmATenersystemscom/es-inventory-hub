# Dashboard AI Connection Guide

## 🎯 ES Inventory Hub Connection Information

**Server**: 192.168.99.246  
**Last Updated**: September 29, 2025  
**Status**: ✅ Fully Operational

---

## 🌐 API Server Access (Recommended)

The ES Inventory Hub provides a REST API that's the easiest way to access data:

### **API Server Details**
- **Base URL**: http://192.168.99.246:5400
- **Status Endpoint**: http://192.168.99.246:5400/api/status
- **Documentation**: http://192.168.99.246:5400/api/docs
- **OpenAPI Spec**: http://192.168.99.246:5400/api/openapi.json

### **Key API Endpoints**
```
GET  /api/status                    # Check API health
GET  /api/devices                   # Get all devices (1,339 devices)
GET  /api/devices/ninja             # Get NinjaRMM devices (763 devices)
GET  /api/devices/threatlocker      # Get ThreatLocker devices (576 devices)
GET  /api/sites                     # Get all sites/organizations
GET  /api/vendors                   # Get all vendors
GET  /api/exceptions                # Get current exceptions (0 currently)
GET  /api/exceptions/stats          # Get exception statistics
POST /api/collectors/run            # Trigger collectors manually
```

### **Example API Usage**
```bash
# Check system health
curl http://192.168.99.246:5400/api/status

# Get all devices
curl http://192.168.99.246:5400/api/devices

# Get device counts by vendor
curl http://192.168.99.246:5400/api/devices/stats

# Get exception statistics
curl http://192.168.99.246:5400/api/exceptions/stats
```

---

## 🗄️ Database Access (Alternative)

If you need direct database access:

### **Connection Details**
```
Host: 192.168.99.246
Port: 5432
Database: es_inventory_hub
Username: postgres
Password: mK2D282lRrs6bTpXWe7
```

### **Connection String**
```
postgresql://postgres:mK2D282lRrs6bTpXWe7@192.168.99.246:5432/es_inventory_hub
```

### **Key Tables**
- `device_snapshot` - Main device inventory data
- `exceptions` - Cross-vendor consistency check results
- `vendor` - Data source vendors (Ninja, ThreatLocker)
- `site` - Organizations/sites
- `billing_status` - Device billing classifications

---

## 📊 Current Data Status

### **Device Inventory**
- **Total Devices**: 1,339 devices
- **NinjaRMM Devices**: 763 devices (vendor_id = 3)
- **ThreatLocker Devices**: 576 devices (vendor_id = 4)
- **Data Quality**: ✅ Clean (0 exceptions found)

### **Collection Schedule**
- **Data Collection**: Daily at 11:00 PM Central Time
- **Cross-Vendor Checks**: Automated after collection
- **Database Backup**: Daily at 9:30 AM Central Time
- **Timezone**: Central Time (automatic DST handling)

### **Data Freshness**
- **Last Collection**: Today (September 29, 2025)
- **Next Collection**: Tonight at 11:00 PM Central
- **Update Frequency**: Daily automated collection

---

## 🚀 Quick Start for Dashboard AI

### **Option 1: Use API (Recommended)**
```python
import requests

# Check API health
response = requests.get('http://192.168.99.246:5400/api/status')
print(response.json())

# Get all devices
devices = requests.get('http://192.168.99.246:5400/api/devices').json()
print(f"Total devices: {len(devices)}")

# Get exception statistics
stats = requests.get('http://192.168.99.246:5400/api/exceptions/stats').json()
print(f"Exception stats: {stats}")
```

### **Option 2: Direct Database Access**
```python
import psycopg2
import pandas as pd

# Connect to database
conn = psycopg2.connect(
    host='192.168.99.246',
    port=5432,
    database='es_inventory_hub',
    user='postgres',
    password='mK2D282lRrs6bTpXWe7'
)

# Query devices
devices_df = pd.read_sql("""
    SELECT ds.*, v.name as vendor_name, s.name as site_name
    FROM device_snapshot ds
    JOIN vendor v ON ds.vendor_id = v.id
    LEFT JOIN site s ON ds.site_id = s.id
    WHERE ds.snapshot_date = CURRENT_DATE
""", conn)

print(f"Total devices: {len(devices_df)}")
```

---

## 📋 Available Data for Dashboards

### **Device Data**
- Device hostnames and display names
- Operating system information
- Organization/site assignments
- Billing status (billable, spare, unknown)
- Last online timestamps
- Device status and health

### **Exception Data**
- Cross-vendor consistency issues
- Missing devices between vendors
- Spare device mismatches
- Site assignment conflicts
- Data quality issues

### **Analytics Capabilities**
- Device counts by vendor
- Device counts by organization
- Exception trends over time
- Billing status analysis
- Cross-vendor variance reporting

---

## 🔧 System Requirements

### **Network Access**
- Ensure 192.168.99.246 is accessible from your network
- Port 5400 (API) and 5432 (Database) should be open
- No authentication required for API access

### **Dependencies**
```bash
# For API access
pip install requests

# For database access
pip install psycopg2-binary pandas sqlalchemy
```

---

## 📞 Support Information

### **System Status**
- **API Server**: ✅ Running and operational
- **Database**: ✅ PostgreSQL 16 active
- **Collectors**: ✅ Automated daily collection
- **Cross-Vendor Checks**: ✅ 0 exceptions found

### **Monitoring**
- **API Health**: http://192.168.99.246:5400/api/status
- **Collection Logs**: Available via API endpoints
- **System Logs**: `/var/log/es-inventory-hub/`

---

**Ready to build your dashboard! The ES Inventory Hub is fully operational with 1,339 devices and clean data quality.**

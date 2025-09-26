# ES Inventory Hub API - Dashboard AI Integration Prompt

## **System Overview**

You are integrating with the **ES Inventory Hub** system, which manages device inventory data from NinjaRMM and ThreatLocker, with automated variance detection and cross-vendor consistency checks.

**Base API URL**: `http://localhost:5400`
**Port Range**: 5400-5499 (ES Inventory Hub)

---

## **🚀 Getting Started**

### **1. Start the API Server**
```bash
cd /opt/es-inventory-hub
python3 api/api_server.py
```
**Server runs on**: `http://localhost:5400`

### **2. Verify API is Running**
```bash
curl http://localhost:5400/api/health
```
**Expected Response**: `{"status": "healthy"}`

---

## **📊 Core API Endpoints**

### **System Status & Health**
```bash
GET /api/health                    # Health check
GET /api/status                    # Overall system status  
GET /api/collectors/status         # Collector service status
```

### **Variance Reports (Primary Use Case)**
```bash
GET /api/variance-report/latest    # Latest variance report
GET /api/variance-report/filtered # Filtered report (unresolved exceptions only)
GET /api/variance-report/2025-09-24 # Specific date report
```

### **Manual Collector Control**
```bash
POST /api/collectors/run           # Trigger collectors and cross-vendor checks
```

### **Exception Management**
```bash
GET /api/exceptions                # All exceptions with filtering
POST /api/exceptions/{id}/resolve  # Mark exception as resolved
POST /api/exceptions/bulk-update  # Bulk operations
```

---

## **🎯 Primary Use Cases for Dashboard AI**

### **1. Get Current Variance Status**
```bash
curl http://localhost:5400/api/variance-report/filtered
```
**Use this for**: Dashboard display of current variance issues

### **2. Trigger Fresh Variance Analysis**
```bash
curl -X POST http://localhost:5400/api/collectors/run \
  -H "Content-Type: application/json" \
  -d '{"collector": "both", "run_cross_vendor": true}'
```
**Use this for**: Manual refresh of variance data

### **3. Run Cross-Vendor Checks Only (No Data Collection)**
```bash
curl -X POST http://localhost:5400/api/collectors/run \
  -H "Content-Type: application/json" \
  -d '{"collector": "none", "run_cross_vendor": true}'
```
**Use this for**: Re-analyze existing data without collecting new data

---

## **📋 API Request/Response Examples**

### **Get Latest Variance Report**
```bash
curl http://localhost:5400/api/variance-report/latest
```

**Response Structure**:
```json
{
  "report_date": "2025-09-24",
  "summary": {
    "total_exceptions": 116,
    "unresolved_count": 116
  },
  "by_type": {
    "MISSING_NINJA": 3,
    "DISPLAY_NAME_MISMATCH": 66,
    "DUPLICATE_TL": 1,
    "SITE_MISMATCH": 0,
    "SPARE_MISMATCH": 46
  },
  "exceptions": {
    "MISSING_NINJA": [
      {
        "id": 123,
        "hostname": "WORKSTATION-01",
        "details": "Device in ThreatLocker but not found in Ninja",
        "resolved": false
      }
    ]
  }
}
```

### **Trigger Manual Collection + Variance Analysis**
```bash
curl -X POST http://localhost:5400/api/collectors/run \
  -H "Content-Type: application/json" \
  -d '{"collector": "both", "run_cross_vendor": true}'
```

**Response Structure**:
```json
{
  "success": true,
  "results": {
    "ninja": {
      "success": true,
      "stdout": "Collection completed successfully",
      "stderr": ""
    },
    "threatlocker": {
      "success": true,
      "stdout": "Collection completed successfully", 
      "stderr": ""
    },
    "cross_vendor": {
      "success": true,
      "results": {
        "MISSING_NINJA": 3,
        "DISPLAY_NAME_MISMATCH": 66,
        "DUPLICATE_TL": 1,
        "SITE_MISMATCH": 0,
        "SPARE_MISMATCH": 46
      }
    }
  }
}
```

---

## **🔧 Collector Control Options**

### **Available Collector Types**
- `"both"` - Run both Ninja and ThreatLocker collectors
- `"ninja"` - Run only Ninja collector
- `"threatlocker"` - Run only ThreatLocker collector  
- `"none"` - Skip data collection, run only cross-vendor checks

### **Cross-Vendor Options**
- `"run_cross_vendor": true` - Run variance analysis after collection
- `"run_cross_vendor": false` - Skip variance analysis

---

## **📈 Variance Types Detected**

The system automatically detects these variance types:

- **MISSING_NINJA**: Devices in ThreatLocker but not in Ninja
- **DUPLICATE_TL**: Duplicate hostnames in ThreatLocker
- **SITE_MISMATCH**: Same device assigned to different sites
- **SPARE_MISMATCH**: Spare devices still present in ThreatLocker
- **DISPLAY_NAME_MISMATCH**: Display name inconsistencies

---

## **⏰ Automated Schedule**

**Daily Collection Schedule**:
- **Ninja Collector**: 2:10 AM Central Time
- **ThreatLocker Collector**: 2:31 AM Central Time  
- **Cross-Vendor Checks**: Run automatically after ThreatLocker collection
- **Backup Timer**: 3:00 AM Central Time (dedicated cross-vendor timer)

---

## **🛠️ Troubleshooting**

### **API Server Not Running**
```bash
cd /opt/es-inventory-hub
python3 api/api_server.py
```

### **Check System Status**
```bash
curl http://localhost:5400/api/status
```

### **Check Collector Status**
```bash
curl http://localhost:5400/api/collectors/status
```

### **Test All Endpoints**
```bash
cd /opt/es-inventory-hub
python3 api/test_api.py
```

---

## **💡 Best Practices for Dashboard AI**

### **1. Regular Variance Monitoring**
- Use `GET /api/variance-report/filtered` for dashboard display
- This endpoint returns only unresolved exceptions (clean data)

### **2. Manual Refresh When Needed**
- Use `POST /api/collectors/run` with `"run_cross_vendor": true` for fresh analysis
- Use `"collector": "none"` to avoid unnecessary data collection

### **3. Exception Management**
- Use `POST /api/exceptions/{id}/resolve` to mark issues as resolved
- Use `GET /api/exceptions` with filters for specific variance types

### **4. Error Handling**
- Always check the `"success"` field in responses
- Handle cases where API server is not running
- Monitor system status with `/api/status` endpoint

---

## **🔗 Integration Examples**

### **Dashboard Widget: Current Variances**
```javascript
// Get current variance status
const response = await fetch('http://localhost:5400/api/variance-report/filtered');
const data = await response.json();

// Display in dashboard
console.log(`Total unresolved variances: ${data.summary.unresolved_count}`);
console.log(`Missing from Ninja: ${data.by_type.MISSING_NINJA}`);
```

### **Manual Refresh Button**
```javascript
// Trigger fresh variance analysis
const response = await fetch('http://localhost:5400/api/collectors/run', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    collector: 'none',
    run_cross_vendor: true
  })
});

const result = await response.json();
if (result.success) {
  console.log('Variance analysis completed');
}
```

---

## **📚 Additional Resources**

- **Full API Documentation**: `/opt/es-inventory-hub/docs/API_QUICK_REFERENCE.md`
- **Dashboard Integration Guide**: `/opt/es-inventory-hub/docs/DASHBOARD_INTEGRATION_GUIDE.md`
- **Database Schema**: `/opt/es-inventory-hub/docs/DATABASE_ACCESS_GUIDE.md`

---

## **🎯 Quick Start Checklist**

1. ✅ Start API server: `python3 api/api_server.py`
2. ✅ Test health: `curl http://localhost:5400/api/health`
3. ✅ Get current variances: `curl http://localhost:5400/api/variance-report/filtered`
4. ✅ Test manual refresh: `curl -X POST http://localhost:5400/api/collectors/run -H "Content-Type: application/json" -d '{"collector": "none", "run_cross_vendor": true}'`

**You now have full programmatic control over the ES Inventory Hub variance detection system!**



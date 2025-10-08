# ES Inventory Hub API - Quick Reference

## 🚀 **Start API Server**
```bash
cd /opt/es-inventory-hub
python3 api/api_server.py
# Server runs on https://db-api.enersystems.com:5400
```

## 📊 **Core Endpoints**

### **System Status**
```bash
GET /api/health                    # Health check
GET /api/status                    # Overall system status
GET /api/collectors/status         # Collector service status
```

### **Variance Reports**
```bash
GET /api/variance-report/latest    # Latest variance report
GET /api/variance-report/2025-09-21  # Specific date report
GET /api/variance-report/filtered  # Filtered report for dashboard (unresolved only)
```

### **Exception Management**
```bash
GET /api/exceptions                # All exceptions
GET /api/exceptions?type=MISSING_NINJA&resolved=false  # Filtered
POST /api/exceptions/123/resolve   # Mark as resolved
```

### **Collector Control**
```bash
POST /api/collectors/run           # Trigger collectors
GET /api/collectors/status         # Collector service status
GET /api/collectors/history        # Collection history (last 10 runs)
GET /api/collectors/progress       # Real-time collection progress
# Body: {"collector": "both|ninja|threatlocker", "run_cross_vendor": true}
```

### **Variances Dashboard (NEW)**
```bash
# Historical Analysis
GET /api/variances/available-dates # Get available analysis dates
GET /api/variances/historical/{date} # Historical variance data
GET /api/variances/trends          # Trend analysis over time

# Export Functionality
GET /api/variances/export/csv      # Export variance data to CSV
GET /api/variances/export/pdf      # Export variance data to PDF
GET /api/variances/export/excel    # Export variance data to Excel
```

## 🔧 **Quick Test Commands**
```bash
# Test API server
curl https://db-api.enersystems.com:5400/api/health

# Get latest variance report
curl https://db-api.enersystems.com:5400/api/variance-report/latest

# Get filtered variance report (dashboard format)
curl https://db-api.enersystems.com:5400/api/variance-report/filtered

# Run both collectors
curl -X POST https://db-api.enersystems.com:5400/api/collectors/run \
  -H "Content-Type: application/json" \
  -d '{"collector": "both", "run_cross_vendor": true}'
```

## 📋 **Response Examples**

### **System Status Response**
```json
{
  "data_status": {
    "status": "current",
    "message": "Data is current",
    "latest_date": "2025-09-21"
  },
  "device_counts": {
    "Ninja": "~750+ (updated daily at 02:10 AM)",
    "ThreatLocker": "~400+ (updated daily at 02:31 AM)"
  },
  "exception_counts": {
    "SPARE_MISMATCH": 73,
    "MISSING_NINJA": 26,
    "DUPLICATE_TL": 1
  },
  "total_exceptions": 100
}
```

### **Variance Report Response**
```json
{
  "report_date": "2025-09-21",
  "summary": {
    "total_exceptions": 100,
    "unresolved_count": 100,
    "resolved_count": 0
  },
  "exception_counts": {
    "SPARE_MISMATCH": 73,
    "MISSING_NINJA": 26,
    "DUPLICATE_TL": 1
  },
  "exceptions_by_type": {
    "MISSING_NINJA": [
      {
        "id": 123,
        "hostname": "CHI-1P397H2 | SPARE - was Blake Thomas",
        "details": {
          "tl_hostname": "CHI-1P397H2 | SPARE - was Blake Thomas",
          "tl_org_name": "ChillCo"
        },
        "resolved": false
      }
    ]
  }
}
```

## 🎯 **Common Use Cases**

### **Dashboard Integration**
```javascript
// Get latest variance data
const response = await fetch('https://db-api.enersystems.com:5400/api/variance-report/latest');
const data = await response.json();

// Display exception counts
console.log(`Total exceptions: ${data.summary.total_exceptions}`);
console.log(`Unresolved: ${data.summary.unresolved_count}`);
```

### **Trigger Collection**
```bash
# Run collectors and cross-vendor checks
curl -X POST https://db-api.enersystems.com:5400/api/collectors/run \
  -H "Content-Type: application/json" \
  -d '{"collector": "both", "run_cross_vendor": true}'
```

### **Exception Management**
```bash
# Get unresolved exceptions
curl "https://db-api.enersystems.com:5400/api/exceptions?resolved=false&limit=10"

# Resolve an exception
curl -X POST https://db-api.enersystems.com:5400/api/exceptions/123/resolve \
  -H "Content-Type: application/json" \
  -d '{"resolved_by": "admin", "notes": "Fixed in Ninja"}'
```

## 🔍 **Error Handling**

### **Common Status Codes**
- `200` - Success
- `400` - Bad Request (invalid parameters)
- `404` - Not Found (exception ID not found)
- `500` - Internal Server Error

### **Error Response Format**
```json
{
  "error": "Error message",
  "status": "error_type"
}
```

## 📝 **Notes**
- All dates use `YYYY-MM-DD` format
- Exception types: `MISSING_NINJA`, `DUPLICATE_TL`, `SITE_MISMATCH`, `SPARE_MISMATCH` (DevicesThatShouldNotHaveThreatlocker)
- Data status: `current`, `stale_data`, `out_of_sync`
- API server must be running for endpoints to work

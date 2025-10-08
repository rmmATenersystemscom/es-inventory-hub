# ES Inventory Hub Integration Guide

**Master integration guide for Dashboard AI to connect with the Database AI's ES Inventory Hub system.**

**Last Updated**: October 2, 2025  
**ES Inventory Hub Version**: v1.15.0  
**Status**: ✅ **FULLY OPERATIONAL**

---

## 🚀 **QUICK START**

### **For Dashboard AI (Recommended)**
Start with: **[API Integration Guide](./API_INTEGRATION_GUIDE.md)** - Complete API reference and usage examples

### **For Database AI**
Start with: **[Database Schema Guide](./DATABASE_SCHEMA_GUIDE.md)** - Database reference and direct access

---

## 📚 **FOCUSED DOCUMENTATION**

### **🎯 [API Integration Guide](./API_INTEGRATION_GUIDE.md)**
**Complete API reference for Dashboard AI**
- Quick Start & Connection Information
- Complete API Endpoints Reference
- Dashboard Functionality (Run Collectors, Historical View, Export Report, Windows 11 24H2)
- Response Examples
- Testing Commands
- Critical Notes for Dashboard AI

### **📊 [Variances Dashboard Guide](./VARIANCES_DASHBOARD_GUIDE.md)**
**Dashboard-specific functionality and enhanced capabilities**
- Enhanced API Capabilities (October 2025)
- Variances Dashboard Functionality
- Enhanced Modal Functionality
- Data Quality Fixes
- Export Functionality
- Historical Analysis

### **🪟 [Windows 11 24H2 Guide](./WINDOWS_11_24H2_GUIDE.md)**
**Windows 11 compatibility assessment**
- Assessment Requirements
- API Endpoints
- Assessment Logic
- Database Schema
- Automation (Systemd)
- Monitoring & Logging
- **NEW**: Enhanced Field Mappings with NinjaRMM API Integration

### **🔧 [Setup and Troubleshooting Guide](./SETUP_AND_TROUBLESHOOTING_GUIDE.md)**
**Operational guide for system maintenance**
- Setup Instructions
- HTTPS Configuration
- Troubleshooting Common Issues
- Performance Monitoring
- Maintenance Tasks
- Emergency Procedures

### **🗄️ [Database Schema Guide](./DATABASE_SCHEMA_GUIDE.md)**
**Database reference for direct access**
- Database Overview
- Primary Tables
- Essential Queries
- Performance Indexes
- Schema Migrations
- Data Analysis Queries

---

## 🔗 **INTEGRATION OPTIONS**

### **Option 1: REST API Server (Recommended for Dashboard AI)**

**🚨 CRITICAL FOR DASHBOARD AI:**
- **Your Server**: 192.168.99.245 (Dashboard AI)
- **Database AI Server**: 192.168.99.246 (API Server)
- **NEVER use localhost** - Dashboard AI has no local API server
- **ALWAYS use external URLs** to connect to Database AI's API server

**API Base URL for Dashboard AI:** 
- **Production HTTPS**: `https://db-api.enersystems.com:5400` (Let's Encrypt Certificate) ✅ **RECOMMENDED**
- **IP Access**: `https://192.168.99.246:5400` (HTTPS - Use `-k` flag for testing) ✅ **ALTERNATIVE**

**Documentation**: See [API Integration Guide](./API_INTEGRATION_GUIDE.md) for complete API reference

### **Option 2: Direct Database Access (Database AI Only)**

**⚠️ YOU (Dashboard AI) SHOULD NEVER USE THIS OPTION!**

This is for Database AI internal operations only. You (Dashboard AI) must use the API server.

**Documentation**: See [Database Schema Guide](./DATABASE_SCHEMA_GUIDE.md) for database reference

---

## 🎯 **DASHBOARD AI INTEGRATION PATH**

### **Step 1: API Integration**
1. Read [API Integration Guide](./API_INTEGRATION_GUIDE.md)
2. Test basic endpoints: `curl https://db-api.enersystems.com:5400/api/health`
3. Implement API calls in your dashboard

### **Step 2: Dashboard Functionality**
1. Read [Variances Dashboard Guide](./VARIANCES_DASHBOARD_GUIDE.md)
2. Implement Run Collectors, Historical View, Export Report functionality
3. Test enhanced modal functionality

### **Step 3: Windows 11 24H2 Assessment**
1. Read [Windows 11 24H2 Guide](./WINDOWS_11_24H2_GUIDE.md)
2. Implement compatibility assessment features
3. Test manual trigger functionality

### **Step 4: Troubleshooting (if needed)**
1. Read [Setup and Troubleshooting Guide](./SETUP_AND_TROUBLESHOOTING_GUIDE.md)
2. Use debugging commands and monitoring tools
3. Contact support if issues persist

---

## 📊 **QUICK REFERENCE**

### **Essential API Endpoints**
```bash
# Health & Status
GET /api/health
GET /api/status

# Variances Dashboard
GET /api/variance-report/latest
GET /api/variances/available-dates
GET /api/variances/historical/{date}
GET /api/variances/export/csv

# Collectors
POST /api/collectors/run
GET /api/collectors/status

# Windows 11 24H2
GET /api/windows-11-24h2/status
POST /api/windows-11-24h2/run
```

### **Test Commands**
```bash
# Basic health check
curl https://db-api.enersystems.com:5400/api/health

# Latest variance report
curl https://db-api.enersystems.com:5400/api/variance-report/latest

# Windows 11 24H2 status
curl https://db-api.enersystems.com:5400/api/windows-11-24h2/status

# Windows 11 24H2 compatible devices (with enhanced field mappings)
curl https://db-api.enersystems.com:5400/api/windows-11-24h2/compatible

# Windows 11 24H2 incompatible devices (with enhanced field mappings)
curl https://db-api.enersystems.com:5400/api/windows-11-24h2/incompatible
```

---

## 🪟 **WINDOWS 11 24H2 ENHANCED FIELD MAPPINGS (NEW)**

The Windows 11 24H2 API endpoints now provide enhanced field data through NinjaRMM API integration:

### **Enhanced Fields Available:**
- **`organization`**: Real company names from NinjaRMM API (not "N/A")
- **`location`**: Actual site identifiers from NinjaRMM API (not "Main Office")
- **`system_name`**: Device hostname/identifier
- **`display_name`**: User-friendly device names (not OS versions)
- **`device_type`**: Physical hardware classification
- **`billable_status`**: Billing classification
- **`status`**: Compatibility status
- **`os_name`**: Full operating system name
- **`os_version`**: OS version identifier (e.g., "22H2", "23H2")
- **`os_build`**: OS build number

### **Data Source Enhancement:**
- **Response includes**: `"data_source": "Database + NinjaRMM API"`
- **Fallback handling**: If NinjaRMM API unavailable, falls back to database values

**📚 For complete field mappings, examples, and detailed documentation, see [Windows 11 24H2 Guide](./WINDOWS_11_24H2_GUIDE.md)**

---

## 🚨 **CRITICAL NOTES**

### **Connection Requirements**
- **ALWAYS use HTTPS URLs** - Never use HTTP
- **Use production URL**: `https://db-api.enersystems.com:5400` (recommended)
- **Certificate**: Valid Let's Encrypt certificate (no `-k` flag needed for production)
- **IP Access**: Use `-k` flag only for testing with IP addresses

### **Data Status Handling**
- **Current** (`status: "current"`) - Data is ≤1 day old, show normal report
- **Stale Data** (`status: "stale_data"`) - Data is >1 day old, show warning
- **Out of Sync** (`status: "out_of_sync"`) - No matching data between vendors

### **Error Handling**
- All endpoints return JSON responses
- Check HTTP status codes (200 = success, 4xx = client error, 5xx = server error)
- Error responses include `error` field with details

---

## 📞 **SUPPORT & TROUBLESHOOTING**

### **Common Issues**
1. **API Server Not Running**: Check if `python3 api/api_server.py` is running
2. **Database Connection Failed**: Verify PostgreSQL is running and accessible
3. **Export Dependencies Missing**: Install `pip install reportlab openpyxl xlsxwriter`
4. **Permission Denied**: Check systemd service permissions for collectors

### **Debug Commands**
```bash
# Check API server status (from Dashboard AI server 192.168.99.245)
curl -k https://192.168.99.246:5400/api/health

# Check database connection (from Dashboard AI server 192.168.99.245)
psql postgresql://username:password@hostname:port/database_name

# Test collectors (from Dashboard AI server 192.168.99.245)
curl -k -X POST https://192.168.99.246:5400/api/collectors/run \
  -H "Content-Type: application/json" \
  -d '{"collector": "both", "run_cross_vendor": true}'
```

### **Documentation References**
- **API Issues**: See [API Integration Guide](./API_INTEGRATION_GUIDE.md)
- **Dashboard Issues**: See [Variances Dashboard Guide](./VARIANCES_DASHBOARD_GUIDE.md)
- **Windows 11 Issues**: See [Windows 11 24H2 Guide](./WINDOWS_11_24H2_GUIDE.md)
- **System Issues**: See [Setup and Troubleshooting Guide](./SETUP_AND_TROUBLESHOOTING_GUIDE.md)
- **Database Issues**: See [Database Schema Guide](./DATABASE_SCHEMA_GUIDE.md)

---

## 🎉 **OCTOBER 2025 ENHANCEMENTS SUMMARY**

### **✅ NEW CAPABILITIES DELIVERED**

1. **Enhanced Variance Report Structure**
   - Complete `by_organization` data structure for all variance types
   - Detailed device information (hostname, vendor, display_name, organization, billing_status, action)
   - Full modal functionality support

2. **Enhanced Export Functionality**
   - New `variance_type` parameter for filtering exports
   - Support for all variance types: `missing_in_ninja`, `threatlocker_duplicates`, `ninja_duplicates`, `display_name_mismatches`
   - Backward compatibility with existing `type` parameter

3. **Enhanced Historical Data**
   - Historical endpoints now include complete organization breakdown
   - Same detailed structure as latest variance report
   - Enhanced trend analysis capabilities

4. **Complete Modal Functionality**
   - Users can view detailed device breakdowns by organization
   - Complete device information for each variance
   - Action recommendations for each device
   - Organization grouping for easy management

5. **Windows 11 24H2 Assessment**
   - Automatic assessment 45 minutes after Ninja collector completion
   - Manual trigger via API endpoint
   - Comprehensive compatibility requirements
   - Detailed deficiency reporting
   - Organization breakdown of results

6. **Data Quality Fixes**
   - **Missing in Ninja**: Fixed organization field showing "Unknown" → now shows actual ThreatLocker organization names
   - **ThreatLocker Duplicates**: Fixed organization field showing "Unknown" → now shows actual ThreatLocker organization names
   - **DevicesThatShouldNotHaveThreatlocker**: Fixed organization field showing "Unknown" → now shows actual organization names from both Ninja and ThreatLocker
   - **All Variance Types**: Organization data is now properly populated and accurate

### **🎯 DASHBOARD AI INTEGRATION READY**

The ES Inventory Hub API at `https://db-api.enersystems.com:5400` now provides:

- **Complete Modal Functionality**: Detailed device breakdowns by organization
- **Enhanced Export Capabilities**: Multi-format exports with variance type filtering
- **Historical Analysis**: Complete historical data with organization breakdown
- **Data Quality**: All variance types now show accurate organization information
- **Windows 11 24H2 Assessment**: Complete compatibility assessment system
- **Better User Experience**: Full dashboard functionality as designed

### **📊 VERIFICATION COMPLETE**

- ✅ Enhanced variance reports with organization data
- ✅ Export functionality (CSV, PDF, Excel)
- ✅ Historical variance data with trends
- ✅ Complete modal functionality
- ✅ Missing in Ninja organization data fixed
- ✅ ThreatLocker Duplicates organization data fixed
- ✅ DevicesThatShouldNotHaveThreatlocker organization data fixed
- ✅ All variance types have accurate organization information
- ✅ Windows 11 24H2 Assessment system operational
- ✅ Manual trigger functionality working

---

**🎉 The ES Inventory Hub system is fully operational and ready for Dashboard AI integration!**

**📚 All requested enhancements have been successfully implemented and are ready for Dashboard AI integration!**
# ES Inventory Hub Documentation

**Complete documentation for the ES Inventory Hub system - a cross-vendor device inventory management platform.**

---

## 📚 **Documentation Overview**

This directory contains comprehensive documentation for the ES Inventory Hub system, which collects and analyzes device inventory data from NinjaRMM and ThreatLocker to identify discrepancies and maintain data consistency.

### **🔗 Shared Documentation (Symbolic Links)**

**Important**: Some files in this directory are **symbolic links** to shared documentation across multiple projects. These files serve as a **single source of truth** and should **never be copied** or edited directly.

**Shared Files:**
- **`CHECK_IN_PROCESS.md`** → `/opt/dashboard-project/docs/CHECK_IN_PROCESS.md`
- **`NINJA_API_DOCUMENTATION.md`** → `/opt/dashboard-project/docs/NINJA_API_DOCUMENTATION.md`
- **`THREATLOCKER_API_GUIDE.md`** → `/opt/dashboard-project/docs/THREATLOCKER_API_GUIDE.md`

**⚠️ To modify shared documentation**: Edit the source files in `/opt/dashboard-project/docs/` - changes will automatically appear in all projects.

---

## 🚀 **Quick Start Guides**

### **For Dashboard Developers**
- **[DASHBOARD_INTEGRATION_GUIDE.md](./DASHBOARD_INTEGRATION_GUIDE.md)** - Complete integration guide for building variance dashboards
- **[AI_PROMPT_FOR_DASHBOARD.md](./AI_PROMPT_FOR_DASHBOARD.md)** - AI prompt for dashboard development

### **For Database Access**
- **[DATABASE_ACCESS_GUIDE.md](./DATABASE_ACCESS_GUIDE.md)** - Complete database connection guide with schemas and queries
- **[DEVICE_MATCHING_LOGIC.md](./DEVICE_MATCHING_LOGIC.md)** - How devices are matched between vendors

### **For API Integration**
- **[API_QUICK_REFERENCE.md](./API_QUICK_REFERENCE.md)** - Quick reference for API endpoints and usage
- **[../api/README.md](../api/README.md)** - API server and testing utilities
- **[../api/api_server.py](../api/api_server.py)** - REST API server for variance data and collector management
- **[../api/test_api.py](../api/test_api.py)** - API testing script

---

## 🔧 **System Administration**

### **Service Management**
- **[SYSTEMD.md](./SYSTEMD.md)** - Systemd service setup and management
- **[CRON.md](./CRON.md)** - Cron job configuration (alternative to systemd)

### **Network Configuration**
- **Port Range**: ES Inventory Hub uses ports 5400-5499
- **Dashboard Project**: Reserved ports 5000-5499
- **API Server**: Currently running on port 5400

### **Data Collection**
- **[NINJA_API_DOCUMENTATION.md](./NINJA_API_DOCUMENTATION.md)** - NinjaRMM API integration details
- **[THREATLOCKER_API_GUIDE.md](./THREATLOCKER_API_GUIDE.md)** - ThreatLocker API integration details

### **Migration & Updates**
- **[MIGRATION_COMPLETED.md](./MIGRATION_COMPLETED.md)** - Database migration summary
- **[SCHEMA_UPDATE_SUMMARY.md](./SCHEMA_UPDATE_SUMMARY.md)** - Recent schema changes
- **[CHECK_IN_PROCESS.md](./CHECK_IN_PROCESS.md)** - Data collection process details

### **System Configuration**
- **[SYSTEM_BACKUPS.md](./SYSTEM_BACKUPS.md)** - System backup files and configuration management
- **[SHARED_DOCUMENTATION.md](./SHARED_DOCUMENTATION.md)** - Guide to symbolic links and shared documentation
- **[PORT_CONFIGURATION.md](./PORT_CONFIGURATION.md)** - Network port allocation and management
- **[ENVIRONMENT_CONFIGURATION.md](./ENVIRONMENT_CONFIGURATION.md)** - Environment variable management and troubleshooting

---

## 📊 **System Architecture**

### **Core Components**
1. **Data Collectors** - Automated daily collection from NinjaRMM and ThreatLocker
2. **Cross-Vendor Analysis** - Identifies discrepancies between vendor inventories
3. **Variance Reporting** - Tracks and manages inventory inconsistencies
4. **REST API** - Provides programmatic access to variance data
5. **Dashboard Integration** - Web interface for variance management

### **Data Flow**
```
NinjaRMM (02:10 AM) → Database → Cross-Vendor Analysis → Variance Report
ThreatLocker (02:31 AM) → Database → Cross-Vendor Analysis → Variance Report
```

### **Variance Types**
- **MISSING_NINJA** - Devices in ThreatLocker but not in NinjaRMM
- **DUPLICATE_TL** - Duplicate hostnames in ThreatLocker
- **SITE_MISMATCH** - Same device assigned to different sites
- **SPARE_MISMATCH** - Devices marked as spare in Ninja but still in ThreatLocker

---

## 🔗 **API Endpoints**

### **System Status**
- `GET /api/health` - Health check
- `GET /api/status` - Overall system status
- `GET /api/collectors/status` - Collector service status

### **Variance Reports**
- `GET /api/variance-report/latest` - Latest variance report
- `GET /api/variance-report/{date}` - Specific date variance report
- `GET /api/exceptions` - Exception data with filtering

### **Collector Management**
- `POST /api/collectors/run` - Trigger collector runs
- `POST /api/exceptions/{id}/resolve` - Mark exceptions as resolved

---

## 🗄️ **Database Schema**

### **Primary Tables**
- **`exceptions`** - Variance data and cross-vendor discrepancies
- **`device_snapshot`** - Device inventory from both vendors
- **`vendor`** - Vendor information (Ninja, ThreatLocker)
- **`device_identity`** - Unique device identifiers
- **`device_type`** - Device type classifications

### **Connection Details**
```
Host: localhost
Port: 5432
Database: es_inventory_hub
Username: postgres
Password: Xat162gT2Qsg4WDlO5r
```

---

## 📈 **Current System Status**

- **Live Device Count**: 1,100+ devices (updated daily at 02:10 AM and 02:31 AM)
- **Active Exceptions**: 100+ variance issues
- **Collection Schedule**: Daily at 02:10 AM (Ninja) and 02:31 AM (ThreatLocker)
- **Data Freshness**: Real-time variance detection
- **API Status**: Fully operational

---

## 🛠️ **Getting Started**

### **1. For Dashboard Developers**
```bash
# Read the integration guide
cat docs/DASHBOARD_INTEGRATION_GUIDE.md

# Start the API server
cd /opt/es-inventory-hub
python3 api/api_server.py

# Test the API
python3 api/test_api.py
```

### **2. For System Administrators**
```bash
# Check service status
systemctl status ninja-collector.service
systemctl status threatlocker-collector@rene.service

# View logs
journalctl -u ninja-collector.service
journalctl -u threatlocker-collector@rene.service
```

### **3. For Database Access**
```bash
# Connect to database
psql postgresql://postgres:Xat162gT2Qsg4WDlO5r@localhost:5432/es_inventory_hub

# Run variance queries (see DATABASE_ACCESS_GUIDE.md)
```

---

## 📞 **Support & Troubleshooting**

### **Common Issues**
1. **Collectors not running** - Check systemd service status
2. **No variance data** - Verify both vendors have data for the same date
3. **API connection issues** - Ensure API server is running on port 5000
4. **Database connection** - Verify PostgreSQL is running and accessible

### **Log Locations**
- **Systemd logs**: `journalctl -u <service-name>`
- **Application logs**: `/var/log/es-inventory-hub/`
- **API server logs**: Console output when running `api_server.py`

### **Useful Commands**
```bash
# Check collector status
systemctl list-timers | grep -E "(ninja|threatlocker)"

# View recent exceptions
psql -d es_inventory_hub -c "SELECT * FROM exceptions ORDER BY date_found DESC LIMIT 10;"

# Test API endpoints
curl http://localhost:5400/api/health
curl http://localhost:5400/api/variance-report/latest
```

---

## 📝 **Documentation Maintenance**

This documentation is maintained as part of the ES Inventory Hub project. When making changes:

1. **Update relevant documentation files**
2. **Test API endpoints** using `test_api.py`
3. **Verify database queries** in the access guide
4. **Update this README** if adding new documentation

---

## 🎯 **Next Steps**

- **Dashboard Development** - Use the integration guide to build variance dashboards
- **API Integration** - Implement REST API endpoints in your applications
- **Monitoring** - Set up alerts for collector failures and data quality issues
- **Automation** - Implement automated exception resolution workflows

**The ES Inventory Hub system is fully operational and ready for integration!** 🚀
# 🚨 EMERGENCY RECOVERY CHECKLIST

**Critical recovery procedures for ES Inventory Hub system failures.**

**Last Updated**: October 9, 2025  
**ES Inventory Hub Version**: v1.19.5  
**Status**: ✅ **EMERGENCY PROCEDURES READY**

---

## 🚨 **IMMEDIATE ACTIONS (First 5 Minutes)**

### **Step 1: Assess the Situation**
```bash
# Check if server is responsive
ping -c 3 localhost

# Check system resources
free -h
df -h
top -n 1
```

### **Step 2: Check Core Services**
```bash
# Check PostgreSQL
sudo systemctl status postgresql
sudo systemctl start postgresql  # if not running

# Check API server
sudo systemctl status es-inventory-api.service
sudo systemctl start es-inventory-api.service  # if not running

# Check if port is in use
sudo netstat -tlnp | grep :5400
```

### **Step 3: Test Basic Connectivity**
```bash
# Test API health
curl -k https://localhost:5400/api/health

# Test database connection
psql postgresql://es_inventory_hub:your_password@localhost:5432/es_inventory_hub -c "SELECT 1;"
```

---

## 🔧 **COMMON FAILURE SCENARIOS**

### **Scenario 1: API Server Down**
**Symptoms**: Connection refused, timeout errors
**Quick Fix**:
```bash
# Restart API server
sudo systemctl restart es-inventory-api.service

# Check logs
sudo journalctl -u es-inventory-api.service --since "5 minutes ago"

# If still failing, check port conflicts
sudo pkill -f api_server.py
sudo systemctl start es-inventory-api.service
```

### **Scenario 2: Database Connection Failed**
**Symptoms**: 500 errors, database connection errors
**Quick Fix**:
```bash
# Check PostgreSQL status
sudo systemctl status postgresql
sudo systemctl start postgresql

# Check database user
sudo -u postgres psql -c "SELECT 1 FROM pg_roles WHERE rolname='es_inventory_hub';"

# Create user if missing
sudo -u postgres psql -c "CREATE ROLE es_inventory_hub WITH PASSWORD 'your_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE es_inventory_hub TO es_inventory_hub;"
```

### **Scenario 3: Database Schema Missing**
**Symptoms**: "relation does not exist" errors
**Quick Fix**:
```bash
# Set environment and create schema
export DB_DSN="postgresql://es_inventory_hub:your_password@localhost:5432/es_inventory_hub"
cd /opt/es-inventory-hub
python3 -c "from storage.schema import Base; from storage.database import get_engine; Base.metadata.create_all(get_engine())"
```

### **Scenario 4: All Services Down**
**Symptoms**: Complete system failure
**Quick Fix**:
```bash
# Run automated recovery
sudo /opt/es-inventory-hub/scripts/reboot_recovery.sh
```

---

## 🔄 **FULL SYSTEM RECOVERY**

### **Step 1: Stop All Services**
```bash
# Stop API server
sudo systemctl stop es-inventory-api.service

# Stop all timers
sudo systemctl stop es-inventory-ninja.timer
sudo systemctl stop es-inventory-threatlocker.timer
sudo systemctl stop es-inventory-crossvendor.timer
sudo systemctl stop windows-11-24h2-assessment.timer
```

### **Step 2: Database Recovery**
```bash
# Check database status
sudo systemctl status postgresql

# If database is corrupted, recreate
sudo -u postgres dropdb es_inventory_hub
sudo -u postgres createdb es_inventory_hub

# Create user and grant privileges
sudo -u postgres psql -c "CREATE ROLE es_inventory_hub WITH PASSWORD 'your_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE es_inventory_hub TO es_inventory_hub;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO es_inventory_hub;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO es_inventory_hub;"
```

### **Step 3: Schema Recreation**
```bash
# Set environment variable
export DB_DSN="postgresql://es_inventory_hub:your_password@localhost:5432/es_inventory_hub"

# Create schema
cd /opt/es-inventory-hub
python3 -c "from storage.schema import Base; from storage.database import get_engine; Base.metadata.create_all(get_engine())"
```

### **Step 4: Restart Services**
```bash
# Start API server
sudo systemctl start es-inventory-api.service
sudo systemctl enable es-inventory-api.service

# Start all timers
sudo systemctl start es-inventory-ninja.timer
sudo systemctl start es-inventory-threatlocker.timer
sudo systemctl start es-inventory-crossvendor.timer
sudo systemctl start windows-11-24h2-assessment.timer

# Enable all timers
sudo systemctl enable es-inventory-ninja.timer
sudo systemctl enable es-inventory-threatlocker.timer
sudo systemctl enable es-inventory-crossvendor.timer
sudo systemctl enable windows-11-24h2-assessment.timer
```

### **Step 5: Data Collection**
```bash
# Trigger manual data collection
curl -k -X POST https://localhost:5400/api/collectors/run \
  -H "Content-Type: application/json" \
  -d '{"collector": "both", "run_cross_vendor": true}'

# Run Windows 11 24H2 assessment
curl -k -X POST https://localhost:5400/api/windows-11-24h2/run
```

---

## 🧪 **VERIFICATION CHECKLIST**

### **Critical Endpoints**
```bash
# Test all critical endpoints
curl -k https://localhost:5400/api/health
curl -k https://localhost:5400/api/status
curl -k https://localhost:5400/api/collectors/status
curl -k https://localhost:5400/api/windows-11-24h2/status
```

### **Service Status**
```bash
# Check all services are running
sudo systemctl status es-inventory-api.service
sudo systemctl status es-inventory-ninja.timer
sudo systemctl status es-inventory-threatlocker.timer
sudo systemctl status es-inventory-crossvendor.timer
sudo systemctl status windows-11-24h2-assessment.timer
```

### **Database Verification**
```bash
# Check if data exists
psql postgresql://es_inventory_hub:your_password@localhost:5432/es_inventory_hub -c "
SELECT 
  COUNT(*) as total_devices,
  COUNT(CASE WHEN vendor_id = 1 THEN 1 END) as ninja_devices,
  COUNT(CASE WHEN vendor_id = 2 THEN 1 END) as threatlocker_devices
FROM device_snapshot;
"
```

---

## 📋 **RECOVERY TIME ESTIMATES**

| Scenario | Time to Recovery | Complexity |
|----------|------------------|------------|
| API Server Down | 2-5 minutes | Low |
| Database Connection Failed | 5-10 minutes | Medium |
| Database Schema Missing | 10-15 minutes | Medium |
| Complete System Failure | 15-30 minutes | High |
| Full System Rebuild | 30-60 minutes | Very High |

---

## 🚨 **EMERGENCY CONTACTS**

### **Internal Support**
- **Database AI**: Primary system administrator
- **Dashboard AI**: API consumer and integration support
- **System Administrator**: Infrastructure and system maintenance

### **Critical Information**
- **Database**: PostgreSQL on localhost:5432
- **API Server**: HTTPS on localhost:5400
- **Service User**: svc_es-hub
- **Log Directory**: /var/log/es-inventory-hub/
- **Configuration**: /opt/es-inventory-hub/

---

## 📚 **RELATED DOCUMENTATION**

- [Reboot Recovery Guide](./TROUBLESHOOT_REBOOT_RECOVERY.md) - Complete recovery procedures
- [Quick Start Recovery](./TROUBLESHOOT_QUICK_START_RECOVERY.md) - Fast recovery procedures
- [Setup and Troubleshooting Guide](./TROUBLESHOOT_SETUP.md) - General troubleshooting

---

**🎉 This checklist ensures quick recovery from any system failure!**

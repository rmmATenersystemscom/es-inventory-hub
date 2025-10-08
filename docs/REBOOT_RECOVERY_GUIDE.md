# 🚨 REBOOT RECOVERY GUIDE

**Complete recovery procedures for ES Inventory Hub after server reboots.**

**Last Updated**: October 8, 2025  
**ES Inventory Hub Version**: v1.19.3  
**Status**: ✅ **RECOVERY PROCEDURES DOCUMENTED**

---

## 🚨 **IMMEDIATE POST-REBOOT CHECKLIST**

### **Step 1: Verify Core Services**
```bash
# Check PostgreSQL status
sudo systemctl status postgresql
sudo systemctl start postgresql  # if not running

# Check API server status
sudo systemctl status es-inventory-api.service
sudo systemctl start es-inventory-api.service  # if not running

# Check collector timers
sudo systemctl status es-inventory-ninja.timer
sudo systemctl status es-inventory-threatlocker.timer
sudo systemctl status es-inventory-crossvendor.timer
sudo systemctl status windows-11-24h2-assessment.timer
```

### **Step 2: Test API Connectivity**
```bash
# Test basic API health
curl -k https://localhost:5400/api/health

# Test system status
curl -k https://localhost:5400/api/status

# Test Windows 11 24H2 endpoints
curl -k https://localhost:5400/api/windows-11-24h2/status
```

### **Step 3: Verify Database Schema**
```bash
# Check if database exists and has data
psql postgresql://es_inventory_hub:your_password@localhost:5432/es_inventory_hub -c "SELECT COUNT(*) FROM device_snapshot;"

# Check if tables exist
psql postgresql://es_inventory_hub:your_password@localhost:5432/es_inventory_hub -c "\dt"
```

---

## 🔧 **COMMON POST-REBOOT ISSUES & FIXES**

### **Issue 1: Database Connection Failed**
**Symptoms**: API returns 500 errors, database connection errors
**Root Cause**: Database user doesn't exist or wrong password
**Fix**:
```bash
# Create database user if missing
sudo -u postgres psql -c "CREATE ROLE es_inventory_hub WITH PASSWORD 'your_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE es_inventory_hub TO es_inventory_hub;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO es_inventory_hub;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO es_inventory_hub;"
```

### **Issue 2: Database Schema Missing**
**Symptoms**: "relation does not exist" errors, empty database
**Root Cause**: Alembic migrations not applied or database recreated
**Fix**:
```bash
# Set environment variable
export DB_DSN="postgresql://es_inventory_hub:your_password@localhost:5432/es_inventory_hub"

# Apply migrations
cd /opt/es-inventory-hub
alembic upgrade head

# If migrations fail, create schema manually
python3 -c "
from storage.schema import Base
from storage.database import get_engine
engine = get_engine()
Base.metadata.create_all(engine)
print('Schema created successfully')
"
```

### **Issue 3: API Server Not Starting**
**Symptoms**: API server fails to start, port conflicts
**Root Cause**: Missing dependencies, wrong port, or service configuration
**Fix**:
```bash
# Check if port is in use
sudo netstat -tlnp | grep :5400

# Kill any conflicting processes
sudo pkill -f api_server.py

# Restart API server
sudo systemctl restart es-inventory-api.service

# Check logs
sudo journalctl -u es-inventory-api.service -f
```

### **Issue 4: Missing Environment Variables**
**Symptoms**: "DB_DSN environment variable is not set" errors
**Root Cause**: Environment variables not loaded in systemd service
**Fix**:
```bash
# Check service environment
sudo systemctl show es-inventory-api.service | grep Environment

# Edit service file if needed
sudo systemctl edit es-inventory-api.service

# Add environment variables
[Service]
Environment=DB_DSN=postgresql://es_inventory_hub:your_password@localhost:5432/es_inventory_hub
Environment=NINJA_CLIENT_ID=your_client_id
Environment=NINJA_CLIENT_SECRET=your_client_secret
Environment=THREATLOCKER_API_KEY=your_api_key

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart es-inventory-api.service
```

### **Issue 5: Missing Database Columns**
**Symptoms**: "column does not exist" errors in API endpoints
**Root Cause**: Database schema not up to date
**Fix**:
```bash
# Check current schema version
alembic current

# Apply any pending migrations
alembic upgrade head

# If specific columns are missing, add them manually
psql postgresql://es_inventory_hub:your_password@localhost:5432/es_inventory_hub -c "
ALTER TABLE device_snapshot ADD COLUMN IF NOT EXISTS windows_11_24h2_capable BOOLEAN;
ALTER TABLE device_snapshot ADD COLUMN IF NOT EXISTS windows_11_24h2_deficiencies TEXT;
"
```

---

## 🔄 **FULL SYSTEM RECOVERY PROCEDURE**

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

# If database is corrupted, recreate it
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

# Create schema using SQLAlchemy
cd /opt/es-inventory-hub
python3 -c "
from storage.schema import Base
from storage.database import get_engine
engine = get_engine()
Base.metadata.create_all(engine)
print('Database schema created successfully')
"
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

## 🔍 **VERIFICATION CHECKLIST**

### **API Health Check**
```bash
# Test all critical endpoints
curl -k https://localhost:5400/api/health
curl -k https://localhost:5400/api/status
curl -k https://localhost:5400/api/collectors/status
curl -k https://localhost:5400/api/windows-11-24h2/status
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

### **Service Status Check**
```bash
# Check all services are running
sudo systemctl status es-inventory-api.service
sudo systemctl status es-inventory-ninja.timer
sudo systemctl status es-inventory-threatlocker.timer
sudo systemctl status es-inventory-crossvendor.timer
sudo systemctl status windows-11-24h2-assessment.timer
```

---

## 📋 **PREVENTION MEASURES**

### **1. Backup Critical Files**
```bash
# Backup systemd service files
sudo cp /etc/systemd/system/es-inventory-*.service /opt/es-inventory-hub/backups/
sudo cp /etc/systemd/system/es-inventory-*.timer /opt/es-inventory-hub/backups/

# Backup environment configuration
sudo cp /opt/es-inventory-hub/.env /opt/es-inventory-hub/backups/
```

### **2. Document Current State**
```bash
# Document current configuration
echo "=== ES Inventory Hub Configuration ===" > /opt/es-inventory-hub/backups/current_config.txt
echo "Date: $(date)" >> /opt/es-inventory-hub/backups/current_config.txt
echo "" >> /opt/es-inventory-hub/backups/current_config.txt

echo "=== Service Status ===" >> /opt/es-inventory-hub/backups/current_config.txt
sudo systemctl status es-inventory-api.service >> /opt/es-inventory-hub/backups/current_config.txt
sudo systemctl status es-inventory-ninja.timer >> /opt/es-inventory-hub/backups/current_config.txt
sudo systemctl status es-inventory-threatlocker.timer >> /opt/es-inventory-hub/backups/current_config.txt

echo "=== Database Schema ===" >> /opt/es-inventory-hub/backups/current_config.txt
psql postgresql://es_inventory_hub:your_password@localhost:5432/es_inventory_hub -c "\dt" >> /opt/es-inventory-hub/backups/current_config.txt
```

### **3. Create Recovery Script**
```bash
# Create automated recovery script
cat > /opt/es-inventory-hub/scripts/reboot_recovery.sh << 'EOF'
#!/bin/bash
echo "=== ES Inventory Hub Reboot Recovery ==="
echo "Date: $(date)"
echo ""

# Set environment variables
export DB_DSN="postgresql://es_inventory_hub:your_password@localhost:5432/es_inventory_hub"

# Start PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

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

# Test API
echo "Testing API..."
curl -k https://localhost:5400/api/health

echo "Recovery complete!"
EOF

chmod +x /opt/es-inventory-hub/scripts/reboot_recovery.sh
```

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

- [Setup and Troubleshooting Guide](./SETUP_AND_TROUBLESHOOTING_GUIDE.md) - General troubleshooting
- [Database Schema Guide](./DATABASE_SCHEMA_GUIDE.md) - Database reference
- [API Integration Guide](./API_INTEGRATION_GUIDE.md) - API endpoints
- [Windows 11 24H2 Guide](./WINDOWS_11_24H2_GUIDE.md) - Assessment system

---

**🎉 This guide ensures quick recovery from any reboot scenario!**

# 🚀 QUICK START RECOVERY

**Fast recovery procedures for ES Inventory Hub after server reboots.**

**Last Updated**: October 8, 2025  
**ES Inventory Hub Version**: v1.19.3  
**Status**: ✅ **QUICK RECOVERY READY**

---

## ⚡ **ONE-COMMAND RECOVERY**

```bash
# Run the automated recovery script
sudo /opt/es-inventory-hub/scripts/reboot_recovery.sh
```

**This single command will:**
- ✅ Start PostgreSQL database
- ✅ Create database user if missing
- ✅ Verify database schema
- ✅ Start API server
- ✅ Start all collector timers
- ✅ Test all API endpoints
- ✅ Trigger data collection
- ✅ Run Windows 11 24H2 assessment

---

## 🔧 **MANUAL QUICK FIXES**

### **If API Server Won't Start**
```bash
# Check logs
sudo journalctl -u es-inventory-api.service --since "5 minutes ago"

# Restart service
sudo systemctl restart es-inventory-api.service

# Check status
sudo systemctl status es-inventory-api.service
```

### **If Database Connection Fails**
```bash
# Create missing user
sudo -u postgres psql -c "CREATE ROLE es_inventory_hub WITH PASSWORD 'your_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE es_inventory_hub TO es_inventory_hub;"

# Test connection
psql postgresql://es_inventory_hub:your_password@localhost:5432/es_inventory_hub -c "SELECT 1;"
```

### **If Database Schema Missing**
```bash
# Set environment and create schema
export DB_DSN="postgresql://es_inventory_hub:your_password@localhost:5432/es_inventory_hub"
cd /opt/es-inventory-hub
python3 -c "from storage.schema import Base; from storage.database import get_engine; Base.metadata.create_all(get_engine())"
```

---

## 🧪 **QUICK VERIFICATION**

```bash
# Test all critical endpoints
curl -k https://localhost:5400/api/health
curl -k https://localhost:5400/api/status
curl -k https://localhost:5400/api/windows-11-24h2/status

# Check service status
sudo systemctl status es-inventory-api.service
sudo systemctl status es-inventory-ninja.timer
sudo systemctl status es-inventory-threatlocker.timer
```

---

## 📋 **RECOVERY CHECKLIST**

- [ ] PostgreSQL running
- [ ] Database user exists
- [ ] Database schema created
- [ ] API server running
- [ ] All timers enabled
- [ ] Health endpoint responding
- [ ] Status endpoint responding
- [ ] Windows 11 24H2 endpoint responding
- [ ] Data collection triggered

---

**🎉 Recovery should take less than 2 minutes!**

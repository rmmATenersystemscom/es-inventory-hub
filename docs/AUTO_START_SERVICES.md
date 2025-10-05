# ES Inventory Hub - Auto-Start Services Configuration

**Purpose**: Automatic startup configuration for ES Inventory Hub services after server restarts.

**Last Updated**: September 25, 2025  
**Status**: ✅ **ACTIVE** - Auto-start services configured and enabled

---

## 🚀 **Auto-Start Services Overview**

### **Services Configured for Auto-Start**

| Service | Port | Status | Purpose |
|---------|------|--------|---------|
| **ES Inventory Hub API** | 5400 | ✅ Enabled | REST API for variance data and collector management |
| **Ninja Collector Timer** | N/A | ✅ Enabled | Daily data collection at 2:30 AM Central |
| **ThreatLocker Collector Timer** | N/A | ✅ Enabled | Daily data collection at 2:10 AM Central |
| **Cross-Vendor Checks Timer** | N/A | ✅ Enabled | Daily variance analysis at 3:00 AM Central |

---

## 🔧 **Systemd Service Configuration**

### **ES Inventory Hub API Service**

**Service File**: `/etc/systemd/system/es-inventory-api.service`

```ini
[Unit]
Description=ES Inventory Hub API Server
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=rene
Group=rene
WorkingDirectory=/opt/es-inventory-hub
Environment=DB_DSN=postgresql+psycopg2://postgres:Xat162gT2Qsg4WDlO5r@localhost:5432/es_inventory_hub
ExecStart=/usr/bin/python3 /opt/es-inventory-hub/api/api_server.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**Status**: ✅ **Enabled and Active**

---

## 📋 **Service Management Commands**

### **ES Inventory Hub API Service**

```bash
# Check service status
systemctl status es-inventory-api.service

# Start service manually
sudo systemctl start es-inventory-api.service

# Stop service
sudo systemctl stop es-inventory-api.service

# Restart service
sudo systemctl restart es-inventory-api.service

# Enable auto-start (already done)
sudo systemctl enable es-inventory-api.service

# Disable auto-start
sudo systemctl disable es-inventory-api.service
```

### **Collector Timers (Already Configured)**

```bash
# Check timer status
systemctl status ninja-collector.timer
systemctl status threatlocker-collector@rene.timer
systemctl status es-cross-vendor-checks.timer

# Enable/disable timers
sudo systemctl enable ninja-collector.timer
sudo systemctl enable threatlocker-collector@rene.timer
sudo systemctl enable es-cross-vendor-checks.timer
```

---

## 🔄 **Startup Sequence**

### **Boot Process Order**

1. **PostgreSQL Database** (port 5432)
2. **ES Inventory Hub API** (port 5400) - Waits for PostgreSQL
3. **Collector Timers** - Scheduled for daily runs
4. **Cross-Vendor Checks Timer** - Scheduled for daily runs

### **Dependencies**

- **ES Inventory Hub API** depends on PostgreSQL
- **Collector services** depend on database connectivity
- **Cross-vendor checks** depend on collector data

---

## 🛠️ **Manual Service Management**

### **Start All Services Manually**

```bash
# Start API server
sudo systemctl start es-inventory-api.service

# Start collector timers
sudo systemctl start ninja-collector.timer
sudo systemctl start threatlocker-collector@rene.timer
sudo systemctl start es-cross-vendor-checks.timer
```

### **Stop All Services**

```bash
# Stop API server
sudo systemctl stop es-inventory-api.service

# Stop collector timers
sudo systemctl stop ninja-collector.timer
sudo systemctl stop threatlocker-collector@rene.timer
sudo systemctl stop es-cross-vendor-checks.timer
```

---

## 🔍 **Service Verification**

### **Check All Services Status**

```bash
# Check API service
systemctl status es-inventory-api.service

# Check collector timers
systemctl status ninja-collector.timer
systemctl status threatlocker-collector@rene.timer
systemctl status es-cross-vendor-checks.timer

# Check if API is responding
curl https://db-api.enersystems.com:5400/api/health
```

### **Expected Output**

```bash
# API Health Check
{
  "status": "healthy",
  "timestamp": "2025-09-25T19:30:59.788176",
  "version": "1.0.0"
}

# Service Status
● es-inventory-api.service - ES Inventory Hub API Server
   Active: active (running)
   Main PID: 12345 (python3)
```

---

## 🚨 **Troubleshooting**

### **Common Issues**

1. **API Service Won't Start**
   ```bash
   # Check logs
   journalctl -u es-inventory-api.service -n 50
   
   # Check database connection
   systemctl status postgresql.service
   ```

2. **Database Connection Issues**
   ```bash
   # Test database connection
   psql -U postgres -h localhost -d es_inventory_hub -c "SELECT 1;"
   ```

3. **Port Conflicts**
   ```bash
   # Check port usage
   ss -tlnp | grep :5400
   
   # ES Inventory Hub should only use ports 5400-5499
   # Dashboard Project uses ports 5000-5399
   ```

### **Service Logs**

```bash
# View API service logs
journalctl -u es-inventory-api.service -f

# View collector logs
journalctl -u ninja-collector.service -f
journalctl -u threatlocker-collector@rene.service -f
```

---

## 📊 **Port Configuration Compliance**

### **ES Inventory Hub Port Usage**

| Service | Port | Status | Compliance |
|---------|------|--------|------------|
| **API Server** | 5400 | ✅ Active | ✅ Compliant (5400-5499 range) |
| **Future Services** | 5401-5499 | Available | ✅ Compliant |

### **Port Range Separation**

- **Dashboard Project**: 5000-5399 ✅
- **ES Inventory Hub**: 5400-5499 ✅
- **PostgreSQL**: 5432 ✅ (shared)

**✅ All services comply with PORT_CONFIGURATION.md**

---

## 🔄 **After Server Restart**

### **Automatic Startup**

After a server restart, the following services will start automatically:

1. **PostgreSQL Database** (system service)
2. **ES Inventory Hub API** (systemd service)
3. **Collector Timers** (systemd timers)
4. **Cross-Vendor Checks Timer** (systemd timer)

### **Verification After Restart**

```bash
# Check all services are running
systemctl status es-inventory-api.service
systemctl status ninja-collector.timer
systemctl status threatlocker-collector@rene.timer

# Test API connectivity
curl https://db-api.enersystems.com:5400/api/health

# Check port usage
ss -tlnp | grep -E ":(5400|5432)"
```

---

## 📚 **Related Documentation**

- **[Port Configuration Guide](./PORT_CONFIGURATION.md)** - Complete port allocation and management
- **[Systemd Services Guide](./SYSTEMD.md)** - Collector service configuration
- **[API Quick Reference](./API_QUICK_REFERENCE.md)** - API endpoint documentation
- **[Dashboard Integration Guide](./DASHBOARD_INTEGRATION_GUIDE.md)** - Integration procedures

---

## ✅ **Configuration Summary**

**Auto-Start Services Configured:**
- ✅ ES Inventory Hub API (port 5400)
- ✅ Ninja Collector Timer (2:30 AM Central)
- ✅ ThreatLocker Collector Timer (2:10 AM Central)  
- ✅ Cross-Vendor Checks Timer (3:00 AM Central)

**Port Compliance:**
- ✅ ES Inventory Hub uses ports 5400-5499 only
- ✅ Dashboard Project uses ports 5000-5399 only
- ✅ No port conflicts between projects

**Service Dependencies:**
- ✅ API service waits for PostgreSQL
- ✅ Collectors depend on database connectivity
- ✅ Proper startup sequence configured

---

**Last Updated**: September 25, 2025  
**Status**: ✅ **ACTIVE** - Auto-start services configured and operational  
**Next Review**: After next server restart to verify functionality

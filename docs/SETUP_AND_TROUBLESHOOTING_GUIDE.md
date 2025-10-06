# Setup and Troubleshooting Guide

**Complete operational guide for ES Inventory Hub setup, configuration, and troubleshooting.**

**Last Updated**: October 2, 2025  
**ES Inventory Hub Version**: v1.15.0  
**Status**: ✅ **FULLY OPERATIONAL**

---

## 🔧 **SETUP INSTRUCTIONS**

### **1. Install Dependencies**
```bash
cd /opt/es-inventory-hub
pip install -r api/requirements-api.txt
```

### **2. API Server (Already Running)**
**Note**: The API server is already running on the Database AI server. Dashboard AI just needs to connect to it.

### **3. Test API**
```bash
# Basic endpoints (from Dashboard AI server 192.168.99.245)
curl https://db-api.enersystems.com:5400/api/health
curl https://db-api.enersystems.com:5400/api/status
curl https://db-api.enersystems.com:5400/api/variance-report/latest

# NEW: Test Enhanced Variances Dashboard endpoints
curl https://db-api.enersystems.com:5400/api/variances/available-dates
curl https://db-api.enersystems.com:5400/api/collectors/history
curl "https://db-api.enersystems.com:5400/api/variances/export/csv"

# NEW: Test Enhanced Export endpoints with variance_type parameter
curl "https://db-api.enersystems.com:5400/api/variances/export/csv?variance_type=missing_in_ninja&date=latest&include_resolved=false"
curl "https://db-api.enersystems.com:5400/api/variances/export/pdf?variance_type=all&date=latest"
curl "https://db-api.enersystems.com:5400/api/variances/export/excel?variance_type=threatlocker_duplicates&date=latest"

# NEW: Test Enhanced Historical endpoints with organization breakdown
curl https://db-api.enersystems.com:5400/api/variances/historical/2025-10-01
curl "https://db-api.enersystems.com:5400/api/variances/trends?start_date=2025-09-01&end_date=2025-10-02"

# NEW: Test Windows 11 24H2 Assessment endpoints
curl https://db-api.enersystems.com:5400/api/windows-11-24h2/status
curl https://db-api.enersystems.com:5400/api/windows-11-24h2/incompatible
curl https://db-api.enersystems.com:5400/api/windows-11-24h2/compatible
curl -X POST https://db-api.enersystems.com:5400/api/windows-11-24h2/run

# Alternative IP access (use -k flag for testing)
curl -k https://192.168.99.246:5400/api/health
```

---

## 🔐 **HTTPS CONFIGURATION**

The API server now supports HTTPS to resolve mixed content errors when accessed from HTTPS dashboards.

### **Current SSL Setup:**
- **Let's Encrypt certificate**: Production-ready certificate for `db-api.enersystems.com`
- **HTTPS URL**: `https://db-api.enersystems.com:5400`
- **Certificate location**: `/opt/es-inventory-hub/ssl/api.crt`
- **Private key location**: `/opt/es-inventory-hub/ssl/api.key`
- **Certificate expires**: December 29, 2025 (auto-renewal configured)

### **Production SSL Setup (Let's Encrypt):**
```bash
# 1. Configure GoDaddy API credentials
nano /opt/es-inventory-hub/ssl/godaddy.ini

# 2. Run SSL setup script
cd /opt/es-inventory-hub/ssl
./setup_ssl.sh

# 3. Restart API server
sudo systemctl restart es-inventory-api.service
```

### **Testing HTTPS:**
```bash
# Test with Let's Encrypt certificate (production)
curl https://db-api.enersystems.com:5400/api/health

# Test main endpoint
curl https://db-api.enersystems.com:5400/api/variance-report/latest

# Test with IP address (use -k flag for testing)
curl -k https://192.168.99.246:5400/api/health
```

### **Firewall Configuration:**
- **Port 5400**: Allowed for HTTPS API access
- **Port 443**: Allowed for HTTPS traffic
- **Port 5432**: Blocked for Dashboard AI (database access)

---

## 🚨 **TROUBLESHOOTING**

### **Common Issues**

#### **1. API Server Not Running**
**Symptoms**: Connection refused, timeout errors
**Solution**:
```bash
# Check if API server is running
sudo systemctl status es-inventory-api.service

# Start API server
sudo systemctl start es-inventory-api.service

# Enable auto-start
sudo systemctl enable es-inventory-api.service

# Check logs
sudo journalctl -u es-inventory-api.service -f
```

#### **2. Database Connection Failed**
**Symptoms**: 500 errors, database connection errors
**Solution**:
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Check database connectivity
psql postgresql://username:password@hostname:port/database_name

# Check database logs
sudo journalctl -u postgresql -f
```

#### **3. Export Dependencies Missing**
**Symptoms**: Export endpoints return errors
**Solution**:
```bash
# Install required packages
pip install reportlab openpyxl xlsxwriter

# Verify installation
python3 -c "import reportlab, openpyxl, xlsxwriter; print('All packages installed')"
```

#### **4. Permission Denied**
**Symptoms**: File permission errors, service failures
**Solution**:
```bash
# Check file permissions
ls -la /opt/es-inventory-hub/

# Fix permissions
sudo chown -R postgres:postgres /opt/es-inventory-hub/
sudo chmod -R 755 /opt/es-inventory-hub/

# Check service user
sudo systemctl show es-inventory-api.service | grep User
```

#### **5. SSL Certificate Issues**
**Symptoms**: SSL errors, certificate warnings
**Solution**:
```bash
# Check certificate status
openssl x509 -in /opt/es-inventory-hub/ssl/api.crt -text -noout

# Test certificate
curl -v https://db-api.enersystems.com:5400/api/health

# Renew certificate if needed
cd /opt/es-inventory-hub/ssl
./setup_ssl.sh
```

### **Debug Commands**

#### **API Server Debugging**
```bash
# Check API server status (from Dashboard AI server 192.168.99.245)
curl -k https://192.168.99.246:5400/api/health

# Check API server logs
sudo journalctl -u es-inventory-api.service --since "1 hour ago"

# Test specific endpoints
curl -k https://192.168.99.246:5400/api/status
curl -k https://192.168.99.246:5400/api/variance-report/latest
```

#### **Database Debugging**
```bash
# Check database connection (from Dashboard AI server 192.168.99.245)
psql postgresql://username:password@hostname:port/database_name

# Check database status
sudo systemctl status postgresql

# Check database logs
sudo journalctl -u postgresql --since "1 hour ago"
```

#### **Collector Debugging**
```bash
# Test collectors (from Dashboard AI server 192.168.99.245)
curl -k -X POST https://192.168.99.246:5400/api/collectors/run \
  -H "Content-Type: application/json" \
  -d '{"collector": "both", "run_cross_vendor": true}'

# Check collector status
curl -k https://192.168.99.246:5400/api/collectors/status

# Check collector logs
sudo journalctl -u ninja-collector.service -f
sudo journalctl -u threatlocker-collector.service -f
```

#### **Windows 11 24H2 Assessment Debugging**
```bash
# Check assessment status
curl -k https://192.168.99.246:5400/api/windows-11-24h2/status

# Run assessment manually
curl -k -X POST https://192.168.99.246:5400/api/windows-11-24h2/run

# Check assessment logs
sudo journalctl -u windows-11-24h2-assessment.service -f
tail -f /opt/es-inventory-hub/logs/windows_11_24h2_assessment.log
```

---

## 🔍 **PERFORMANCE MONITORING**

### **System Resources**
```bash
# Check CPU usage
top -p $(pgrep -f api_server.py)

# Check memory usage
free -h

# Check disk usage
df -h /opt/es-inventory-hub/

# Check network connections
netstat -tlnp | grep :5400
```

### **Database Performance**
```sql
-- Check active connections
SELECT count(*) FROM pg_stat_activity;

-- Check database size
SELECT pg_size_pretty(pg_database_size('es_inventory_hub'));

-- Check table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### **API Performance**
```bash
# Test response times
time curl -s https://db-api.enersystems.com:5400/api/health

# Test with verbose output
curl -w "@curl-format.txt" -o /dev/null -s https://db-api.enersystems.com:5400/api/variance-report/latest

# Create curl-format.txt
cat > curl-format.txt << EOF
     time_namelookup:  %{time_namelookup}\n
        time_connect:  %{time_connect}\n
     time_appconnect:  %{time_appconnect}\n
    time_pretransfer:  %{time_pretransfer}\n
       time_redirect:  %{time_redirect}\n
  time_starttransfer:  %{time_starttransfer}\n
                     ----------\n
          time_total:  %{time_total}\n
EOF
```

---

## 🔄 **MAINTENANCE TASKS**

### **Daily Maintenance**
```bash
# Check system status
curl https://db-api.enersystems.com:5400/api/health

# Check data freshness
curl https://db-api.enersystems.com:5400/api/status

# Check collector status
curl https://db-api.enersystems.com:5400/api/collectors/status
```

### **Weekly Maintenance**
```bash
# Check database size
psql postgresql://username:password@hostname:port/database_name -c "SELECT pg_size_pretty(pg_database_size('es_inventory_hub'));"

# Check log file sizes
du -sh /opt/es-inventory-hub/logs/*

# Clean old logs if needed
find /opt/es-inventory-hub/logs/ -name "*.log" -mtime +30 -delete
```

### **Monthly Maintenance**
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Check certificate expiration
openssl x509 -in /opt/es-inventory-hub/ssl/api.crt -noout -dates

# Backup database
pg_dump postgresql://username:password@hostname:port/database_name > backup_$(date +%Y%m%d).sql
```

---

## 📊 **LOGGING AND MONITORING**

### **Log Locations**
```bash
# API server logs
sudo journalctl -u es-inventory-api.service

# Database logs
sudo journalctl -u postgresql

# Collector logs
sudo journalctl -u ninja-collector.service
sudo journalctl -u threatlocker-collector.service

# Windows 11 24H2 assessment logs
sudo journalctl -u windows-11-24h2-assessment.service
tail -f /opt/es-inventory-hub/logs/windows_11_24h2_assessment.log

# Application logs
tail -f /opt/es-inventory-hub/logs/*.log
```

### **Log Rotation**
```bash
# Check logrotate configuration
sudo cat /etc/logrotate.d/es-inventory-hub

# Manual log rotation
sudo logrotate -f /etc/logrotate.d/es-inventory-hub
```

### **Monitoring Scripts**
```bash
# Create monitoring script
cat > /opt/es-inventory-hub/scripts/monitor.sh << 'EOF'
#!/bin/bash
echo "=== ES Inventory Hub Status ==="
echo "Date: $(date)"
echo ""

echo "=== API Health ==="
curl -s https://db-api.enersystems.com:5400/api/health | jq .

echo ""
echo "=== System Status ==="
curl -s https://db-api.enersystems.com:5400/api/status | jq .

echo ""
echo "=== Collector Status ==="
curl -s https://db-api.enersystems.com:5400/api/collectors/status | jq .

echo ""
echo "=== Windows 11 24H2 Status ==="
curl -s https://db-api.enersystems.com:5400/api/windows-11-24h2/status | jq .
EOF

chmod +x /opt/es-inventory-hub/scripts/monitor.sh
```

---

## 🚨 **EMERGENCY PROCEDURES**

### **API Server Down**
```bash
# Restart API server
sudo systemctl restart es-inventory-api.service

# Check status
sudo systemctl status es-inventory-api.service

# Check logs
sudo journalctl -u es-inventory-api.service --since "5 minutes ago"
```

### **Database Issues**
```bash
# Restart PostgreSQL
sudo systemctl restart postgresql

# Check database status
sudo systemctl status postgresql

# Check database logs
sudo journalctl -u postgresql --since "5 minutes ago"
```

### **SSL Certificate Issues**
```bash
# Check certificate status
openssl x509 -in /opt/es-inventory-hub/ssl/api.crt -noout -dates

# Renew certificate
cd /opt/es-inventory-hub/ssl
./setup_ssl.sh

# Restart API server
sudo systemctl restart es-inventory-api.service
```

### **Data Collection Issues**
```bash
# Check collector status
curl https://db-api.enersystems.com:5400/api/collectors/status

# Trigger manual collection
curl -X POST https://db-api.enersystems.com:5400/api/collectors/run \
  -H "Content-Type: application/json" \
  -d '{"collector": "both", "run_cross_vendor": true}'

# Check collector logs
sudo journalctl -u ninja-collector.service -f
sudo journalctl -u threatlocker-collector.service -f
```

---

## 📞 **SUPPORT CONTACTS**

### **Internal Support**
- **Database AI**: Primary system administrator
- **Dashboard AI**: API consumer and integration support
- **System Administrator**: Infrastructure and system maintenance

### **External Support**
- **NinjaRMM**: API and data collection support
- **ThreatLocker**: API and data collection support
- **Let's Encrypt**: SSL certificate support

---

## 📚 **RELATED DOCUMENTATION**

- [API Integration Guide](./API_INTEGRATION_GUIDE.md) - Core API endpoints and usage
- [Variances Dashboard Guide](./VARIANCES_DASHBOARD_GUIDE.md) - Dashboard functionality
- [Windows 11 24H2 Guide](./WINDOWS_11_24H2_GUIDE.md) - Windows 11 compatibility assessment
- [Database Schema Guide](./DATABASE_SCHEMA_GUIDE.md) - Database reference

---

**🎉 The ES Inventory Hub system is fully operational and ready for Dashboard AI integration!**

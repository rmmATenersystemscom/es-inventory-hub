# Port Configuration Guide

**Network Port Allocation and Management for ES Inventory Hub**

---

## 🔌 **Port Range Allocation**

### **Project Port Ranges**

| Project | Port Range | Status | Purpose |
|---------|------------|--------|---------|
| **Dashboard Project** | 5000-5499 | Reserved | Dashboard services, web interfaces, and related APIs |
| **ES Inventory Hub** | 5500-5599 | Available | Data collection, API services, and system utilities |

### **Current Port Usage**

| Service | Port | Protocol | Purpose |
|---------|------|----------|---------|
| **API Server** | 5500 | HTTP | REST API for variance data and collector management |
| **Future Services** | 5501-5599 | TBD | Available for additional services |

---

## 🎯 **Port Selection Rationale**

### **Why Port 5500?**
- **Clear Separation**: 500+ port gap from dashboard project range
- **Standard Range**: Within common application port range (1024-65535)
- **Future Expansion**: 100 ports available for additional services
- **Conflict Avoidance**: No overlap with dashboard project ports

### **Benefits of Port Range Allocation**
1. **Conflict Prevention**: Clear boundaries prevent port conflicts
2. **Scalability**: Room for future service expansion
3. **Maintenance**: Easy to identify which project uses which ports
4. **Security**: Simplified firewall rule management
5. **Documentation**: Clear port ownership and usage

---

## 🔧 **Current Configuration**

### **API Server Configuration**
```python
# api/api_server.py
app.run(host='0.0.0.0', port=5500, debug=True)
```

### **Test Script Configuration**
```python
# api/test_api.py
API_BASE = "http://localhost:5500"
```

### **Documentation References**
All documentation has been updated to reference port 5500:
- API Quick Reference
- Dashboard Integration Guide
- API Directory README
- Main Project README

---

## 🚀 **Future Port Planning**

### **Available Ports (5501-5599)**
- **5501-5510**: Additional API services
- **5511-5520**: WebSocket services
- **5521-5530**: Background processing services
- **5531-5540**: Monitoring and health check services
- **5541-5550**: Development and testing services
- **5551-5599**: Reserved for future expansion

### **Port Assignment Guidelines**
1. **Sequential Assignment**: Use ports in order (5501, 5502, etc.)
2. **Service Grouping**: Group related services in ranges
3. **Documentation**: Always document new port assignments
4. **Testing**: Verify port availability before assignment
5. **Firewall**: Update firewall rules for new services

---

## 🔒 **Security Considerations**

### **Firewall Configuration**
```bash
# Allow ES Inventory Hub ports
sudo ufw allow 5500:5599/tcp

# Allow specific service
sudo ufw allow 5500/tcp
```

### **Network Security**
- **Local Access**: API server binds to 0.0.0.0 (all interfaces)
- **Production**: Consider binding to specific interfaces in production
- **Authentication**: No authentication currently implemented
- **HTTPS**: Consider SSL/TLS for production deployment

---

## 🛠️ **Changing Port Configuration**

### **To Change API Server Port**

1. **Update API Server**
   ```python
   # api/api_server.py
   app.run(host='0.0.0.0', port=NEW_PORT, debug=True)
   ```

2. **Update Test Script**
   ```python
   # api/test_api.py
   API_BASE = f"http://localhost:{NEW_PORT}"
   ```

3. **Update Documentation**
   - Update all curl commands
   - Update API references
   - Update integration guides

4. **Update Firewall Rules**
   ```bash
   sudo ufw allow NEW_PORT/tcp
   ```

### **Verification Steps**
```bash
# Test new port
curl http://localhost:NEW_PORT/api/health

# Check if port is listening
netstat -tlnp | grep NEW_PORT

# Test API endpoints
python3 api/test_api.py
```

---

## 📊 **Port Monitoring**

### **Check Port Usage**
```bash
# List all listening ports
netstat -tlnp

# Check specific port range
netstat -tlnp | grep -E ":(55[0-9][0-9]|56[0-9][0-9])"

# Check ES Inventory Hub ports
netstat -tlnp | grep -E ":(550[0-9]|551[0-9]|552[0-9]|553[0-9]|554[0-9]|555[0-9]|556[0-9]|557[0-9]|558[0-9]|559[0-9])"
```

### **Port Conflict Detection**
```bash
# Check for conflicts with dashboard project
netstat -tlnp | grep -E ":(5[0-4][0-9][0-9])"

# Check for any conflicts
netstat -tlnp | grep -E ":(55[0-9][0-9])"
```

---

## 🔄 **Integration with Dashboard Project**

### **Port Coordination**
- **Dashboard Project**: Manages ports 5000-5499
- **ES Inventory Hub**: Manages ports 5500-5599
- **Communication**: API calls from dashboard to ES Inventory Hub on port 5500
- **No Conflicts**: Clear separation prevents port conflicts

### **Cross-Project Communication**
```javascript
// Dashboard project calling ES Inventory Hub API
const response = await fetch('http://localhost:5500/api/variance-report/latest');
```

---

## 📋 **Port Assignment Log**

| Date | Service | Port | Purpose | Status |
|------|---------|------|---------|--------|
| 2025-09-22 | API Server | 5500 | REST API for variance data | Active |
| TBD | Future Service | 5501 | TBD | Available |
| TBD | Future Service | 5502 | TBD | Available |

---

## 📚 **Related Documentation**

- **[API Quick Reference](./API_QUICK_REFERENCE.md)** - API endpoint documentation
- **[Dashboard Integration Guide](./DASHBOARD_INTEGRATION_GUIDE.md)** - Integration with dashboard project
- **[API Directory README](../api/README.md)** - API server documentation
- **[Main README](../README.md)** - Project overview

---

**Last Updated**: September 22, 2025  
**Status**: ✅ **ACTIVE** - Port configuration in use

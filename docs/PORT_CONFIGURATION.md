# Port Configuration Guide

**Network Port Allocation and Management for ES Projects**

> **📋 Comprehensive Troubleshooting**: For complete troubleshooting procedures, diagnostic commands, emergency recovery, and all troubleshooting scenarios, see [Comprehensive Troubleshooting Guide](./COMPREHENSIVE_TROUBLESHOOTING_GUIDE.md).

---

## 🔌 **Port Range Allocation**

### **Project Port Ranges**

| Project | Port Range | Status | Purpose |
|---------|------------|--------|---------|
| **Dashboard Project** | 5000-5399 | **ACTIVE** | Dashboard services, web interfaces, and related APIs |
| **ES Inventory Hub** | 5400-5499 | **ACTIVE** | Data collection, API services, and system utilities |

### **Current Port Usage - All 24 Dashboards**

#### **Dashboard Project (5000-5399)**
| Service | Host Port | Container Port | Protocol | Purpose | Status |
|---------|-----------|----------------|----------|---------|--------|
| **Hub Dashboard** | 5000 | 5000 | HTTP | Main dashboard hub and navigation | Active |
| **Variances Dashboard** | 5001 | 5001 | HTTP | Device variance analysis (host network) | Active |
| **Technician Performance** | 5002 | 5000 | HTTP | Individual tech performance | Active |
| **Re-Opened Tickets** | 5003 | 5000 | HTTP | Reopened ticket tracking | Active |
| **BottomLeft Dashboard** | 5004 | 5000 | HTTP | ConnectWise ticket metrics | Active |
| **TopLeft Dashboard** | 5005 | 5000 | HTTP | Executive summary dashboard | Active |
| **Ninja Seat Count** | 5006 | 5000 | HTTP | NinjaRMM device monitoring | Active |
| **SmartNumbers** | 5007 | 5000 | HTTP | Key performance indicators | Active |
| **Veeam Usage** | 5008 | 5000 | HTTP | Veeam storage usage | Active |
| **ThreatLocker Stats** | 5009 | 5000 | HTTP | ThreatLocker security metrics | Active |
| **FortiGate Stats** | 5010 | 5000 | HTTP | FortiGate firewall statistics | Active |
| **Ticket Statistics** | 5012 | 5000 | HTTP | Overall ticket statistics | Active |
| **Veeam Backup Job Status** | 5013 | 5000 | HTTP | Veeam backup monitoring | Active |
| **Tickets Closed Today** | 5014 | 5000 | HTTP | Daily closure metrics | Active |
| **Unassigned Tickets** | 5015 | 5000 | HTTP | Unassigned ticket tracking | Active |
| **Tickets by Status** | 5016 | 5000 | HTTP | Ticket status breakdown | Active |
| **New Tickets by Tech** | 5017 | 5000 | HTTP | New ticket assignments | Active |
| **In-Progress Tickets** | 5018 | 5000 | HTTP | Active ticket tracking | Active |
| **RFQ Tickets** | 5019 | 5000 | HTTP | Request for quote tickets | Active |
| **Waiting on Vendor** | 5020 | 5000 | HTTP | Vendor response tracking | Active |
| **Waiting on Client 4** | 5021 | 5000 | HTTP | Client response tracking | Active |
| **Scheduled Onsite** | 5022 | 5000 | HTTP | Onsite scheduled tickets | Active |
| **Scheduled Internal** | 5023 | 5000 | HTTP | Internal scheduled tickets | Active |
| **Needs ES Attention** | 5024 | 5000 | HTTP | Tickets requiring attention | Active |
| **Technician KPI Wall** | 5025 | 5011 | HTTP | Technician performance metrics | Active |
| **Nginx Reverse Proxy** | 80, 443 | - | HTTP/HTTPS | Web server and SSL termination | Active |

#### **ES Inventory Hub (5400-5499)**
| Service | Port | Protocol | Purpose | Status |
|---------|------|----------|---------|--------|
| **API Server** | 5400 | HTTP | REST API for variance data and collector management | Active |
| **Cross-Vendor Checks** | N/A | Systemd | Daily variance analysis at 3:00 AM Central | Active |
| **Future Services** | 5401-5431, 5433-5499 | TBD | Available for additional services | Available |

#### **Database Services**
| Service | Port | Protocol | Purpose | Status |
|---------|------|----------|---------|--------|
| **PostgreSQL** | 5432 | TCP | Database for both Dashboard and ES Inventory Hub projects | Active |

---

## 🎯 **Port Selection Rationale**

### **Why These Ranges?**
- **Clear Separation**: 500+ port gap between project ranges prevents conflicts
- **Standard Range**: Within common application port range (1024-65535)
- **Future Expansion**: 100 ports available for each project
- **Conflict Avoidance**: No overlap between project port ranges
- **Docker Integration**: Compatible with Docker port mapping

### **Benefits of Port Range Allocation**
1. **Conflict Prevention**: Clear boundaries prevent port conflicts
2. **Scalability**: Room for future service expansion
3. **Maintenance**: Easy to identify which project uses which ports
4. **Security**: Simplified firewall rule management
5. **Documentation**: Clear port ownership and usage
6. **Docker Management**: Simplified container port mapping

---

## 🔧 **Current Configuration**

### **Dashboard Project Configuration**
```python
# Most dashboards use port 5000
app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

# Special cases:
# Variances dashboard uses port 5001
port = int(os.getenv('PORT', 5001))

# Technician KPI Wall uses port 5011
app.run(host='0.0.0.0', port=5011, debug=False)
```

### **ES Inventory Hub Configuration**
```python
# api/api_server.py
app.run(host='0.0.0.0', port=5400, debug=True)
```

### **Nginx Configuration**
```nginx
# nginx/nginx.conf
server {
    listen 80;
    listen 443 ssl;
    # Routes to individual dashboard containers
}
```

---

## 🚀 **Future Port Planning**

### **Dashboard Project Available Ports (5002-5399)**
- **5002-5010**: Additional dashboard services
- **5012-5020**: Specialized dashboards
- **5021-5030**: API services
- **5031-5040**: WebSocket services
- **5041-5050**: Background processing services
- **5051-5060**: Monitoring and health check services
- **5061-5070**: Development and testing services
- **5071-5399**: Reserved for future expansion

### **ES Inventory Hub Available Ports (5401-5431, 5433-5499)**
- **5401-5410**: Additional API services
- **5411-5420**: WebSocket services
- **5421-5430**: Background processing services
- **5431**: Monitoring and health check services
- **5433-5440**: Monitoring and health check services (continued)
- **5441-5450**: Development and testing services
- **5451-5499**: Reserved for future expansion

### **Port Assignment Guidelines**
1. **Sequential Assignment**: Use ports in order within each project range
2. **Service Grouping**: Group related services in ranges
3. **Documentation**: Always document new port assignments
4. **Testing**: Verify port availability before assignment
5. **Firewall**: Update firewall rules for new services
6. **Docker**: Update docker-compose.yml for new services

---

## 🔒 **Security Considerations**

### **Firewall Configuration**
```bash
# Allow Dashboard Project ports
sudo ufw allow 5000:5399/tcp

# Allow ES Inventory Hub ports
sudo ufw allow 5400:5499/tcp

# Allow specific services
sudo ufw allow 5000/tcp  # Most dashboards
sudo ufw allow 5001/tcp  # Variances dashboard
sudo ufw allow 5400/tcp  # ES Inventory Hub API
sudo ufw allow 5432/tcp  # PostgreSQL database
```

### **Network Security**
- **Local Access**: Most services bind to 0.0.0.0 (all interfaces)
- **Production**: Consider binding to specific interfaces in production
- **Authentication**: No authentication currently implemented
- **HTTPS**: SSL/TLS handled by Nginx reverse proxy
- **Docker**: Services run in isolated containers

---

## 🛠️ **Changing Port Configuration**

### **To Change Dashboard Port**

1. **Update Dashboard App**
   ```python
   # dashboards/[dashboard-name]/app.py
   app.run(host='0.0.0.0', port=NEW_PORT, debug=False, use_reloader=False)
   ```

2. **Update Docker Configuration**
   ```yaml
   # docker-compose.yml
   services:
     dashboard-name:
       ports:
         - "NEW_PORT:NEW_PORT"
   ```

3. **Update Nginx Configuration**
   ```nginx
   # nginx/nginx.conf
   location /dashboard/dashboard-name/ {
       proxy_pass http://localhost:NEW_PORT/;
   }
   ```

4. **Update Firewall Rules**
   ```bash
   sudo ufw allow NEW_PORT/tcp
   ```

### **To Change ES Inventory Hub Port**

1. **Update API Server**
   ```python
   # api/api_server.py
   app.run(host='0.0.0.0', port=NEW_PORT, debug=True)
   ```

2. **Update Dashboard Integration**
   ```python
   # Update API calls in dashboards
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
ss -tlnp | grep NEW_PORT

# Test dashboard endpoints
curl http://localhost:NEW_PORT/
```

---

## 📊 **Port Monitoring**

### **Check Port Usage**
```bash
# List all listening ports
ss -tlnp

# Check Dashboard Project ports
ss -tlnp | grep -E ":(5[0-4][0-9][0-9])"

# Check ES Inventory Hub ports
ss -tlnp | grep -E ":(55[0-9][0-9])"

# Check specific port ranges
ss -tlnp | grep -E ":(500[0-9]|501[0-9]|502[0-9]|503[0-9]|504[0-9]|505[0-9]|506[0-9]|507[0-9]|508[0-9]|509[0-9]|510[0-9]|511[0-9]|512[0-9]|513[0-9]|514[0-9]|515[0-9]|516[0-9]|517[0-9]|518[0-9]|519[0-9]|520[0-9]|521[0-9]|522[0-9]|523[0-9]|524[0-9]|525[0-9]|526[0-9]|527[0-9]|528[0-9]|529[0-9]|530[0-9]|531[0-9]|532[0-9]|533[0-9]|534[0-9]|535[0-9]|536[0-9]|537[0-9]|538[0-9]|539[0-9]|540[0-9]|541[0-9]|542[0-9]|543[0-9]|544[0-9]|545[0-9]|546[0-9]|547[0-9]|548[0-9]|549[0-9])"
```

### **Port Conflict Detection**
```bash
# Check for conflicts between projects
ss -tlnp | grep -E ":(5[0-4][0-9][0-9])" | grep -E ":(55[0-9][0-9])"

# Check for any conflicts in Dashboard Project range
ss -tlnp | grep -E ":(5[0-4][0-9][0-9])"

# Check for any conflicts in ES Inventory Hub range
ss -tlnp | grep -E ":(55[0-9][0-9])"
```

---

## 🔄 **Cross-Project Communication**

### **Port Coordination**
- **Dashboard Project**: Manages ports 5000-5399
- **ES Inventory Hub**: Manages ports 5400-5499
- **PostgreSQL Database**: Port 5432 (shared by both projects)
- **Communication**: API calls from dashboard to ES Inventory Hub on port 5400
- **No Conflicts**: Clear separation prevents port conflicts

### **Cross-Project Communication**
```javascript
// Dashboard project calling ES Inventory Hub API
const response = await fetch('http://localhost:5400/api/variance-report/latest');
```

```python
# Dashboard project calling ES Inventory Hub API
import requests
response = requests.get('http://localhost:5400/api/variance-report/latest')
```

---

## 📋 **Port Assignment Log**

### **Dashboard Project Port Assignments**
| Date | Service | Port | Purpose | Status |
|------|---------|------|---------|--------|
| 2025-09-22 | Hub Dashboard | 5000 | Main dashboard hub | Active |
| 2025-09-22 | Variances Dashboard | 5001 | Device variance analysis | Active |
| 2025-09-22 | Technician KPI Wall | 5011 | Technician performance metrics | Active |
| 2025-09-22 | All Other Dashboards | 5000 | Various dashboard services | Active |
| 2025-09-22 | Nginx Reverse Proxy | 80, 443 | Web server and SSL | Active |

### **ES Inventory Hub Port Assignments**
| Date | Service | Port | Purpose | Status |
|------|---------|------|---------|--------|
| 2025-09-23 | API Server | 5400 | REST API for variance data and collector management | Active |
| 2025-09-23 | Cross-Vendor Checks | N/A | Daily variance analysis at 3:00 AM Central | Active |
| TBD | Future Service | 5401 | TBD | Available |
| TBD | Future Service | 5402 | TBD | Available |

### **Database Services Port Assignments**
| Date | Service | Port | Purpose | Status |
|------|---------|------|---------|--------|
| 2025-09-23 | PostgreSQL | 5432 | Database for both Dashboard and ES Inventory Hub projects | Active |

---

## 🚨 **Important Notes**

### **How Multiple Dashboards Work**
- **NOT Docker port mapping**: Each container runs on port 5000 internally
- **Socat forwarders**: Bridge from host ports to container IPs
- **Nginx routing**: Routes external requests to appropriate host ports
- **Container IPs**: Change when containers are recreated (CRITICAL!)

### **Docker Integration**
- **Container Isolation**: Each dashboard runs in its own container
- **Port Mapping**: Host ports mapped to container IPs via socat forwarders
- **Nginx Proxy**: Routes external requests to appropriate host ports
- **Service Discovery**: Containers communicate via internal Docker network
- **IP Management**: Container IPs must be tracked and socat forwarders updated

### **Socat Forwarder Architecture**

The ES Dashboards system uses **TWO networking patterns**:

1. **Host Network**: Variances dashboard (port 5001) - Direct access, no socat needed
2. **Bridge Network**: All other dashboards (ports 5000, 5002-5025) - Via socat forwarders

**🔧 Complete Socat Forwarder Management**: For comprehensive socat forwarder architecture, management commands, troubleshooting procedures, and the complete list of all 24 dashboards with their socat forwarder configurations, see [Socat Forwarder Guide](./SOCAT_FORWARDER_GUIDE.md).

**⚠️ CRITICAL WARNING**: Container IPs change when containers are recreated! Always check current IPs before troubleshooting. See the [Socat Forwarder Guide](./SOCAT_FORWARDER_GUIDE.md) for detailed procedures.

---

## 📚 **Related Documentation**

- **[Comprehensive Troubleshooting Guide](./COMPREHENSIVE_TROUBLESHOOTING_GUIDE.md)** - **AUTHORITATIVE** complete troubleshooting procedures and diagnostic commands
- **[Socat Forwarder Guide](./SOCAT_FORWARDER_GUIDE.md)** - Complete socat forwarder management and troubleshooting
- **[Nginx Configuration Guide](./NGINX_CONFIGURATION_GUIDE.md)** - Complete nginx configuration management and service management
- **[API Quick Reference](./API_QUICK_REFERENCE.md)** - API endpoint documentation
- **[Dashboard Integration Guide](./DASHBOARD_INTEGRATION_GUIDE.md)** - Integration with dashboard project
- **[API Directory README](../api/README.md)** - API server documentation
- **[Main README](../README.md)** - Project overview
- **[Docker Configuration](../es-dashboards/docker-compose.yml)** - Container configuration

---

**Last Updated**: September 23, 2025  
**Status**: ✅ **ACTIVE** - Port configuration in use  
**Projects**: Dashboard Project (5000-5399) + ES Inventory Hub (5400-5499) + PostgreSQL (5432)
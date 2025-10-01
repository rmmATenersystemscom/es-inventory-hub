# AI Assistant Boundaries

**IMPORTANT**: This document establishes clear boundaries between AI assistants to prevent overstepping responsibilities and maintain project integrity.

## 🚧 **Project Boundaries**

### **ES Inventory Hub AI (Database AI) Scope:**
- ✅ **Data Collection**: NinjaRMM and ThreatLocker collectors
- ✅ **Database Management**: PostgreSQL schema, migrations, queries
- ✅ **API Server**: REST API for variance data (see [Port Configuration](PORT_CONFIGURATION.md))
- ✅ **Systemd Services**: Automated collection scheduling
- ✅ **Cross-Vendor Checks**: Variance detection and exception handling
- ✅ **Documentation**: Project-specific documentation in `/docs/`
- ✅ **Environment Configuration**: Local `.env` files and systemd service configs
- ✅ **Database Performance**: Query optimization and schema management
- ✅ **Data Quality**: Ensuring accurate device inventory collection

### **Dashboard Project AI Scope:**
- ✅ **Web Dashboards**: All dashboard containers (see [Port Configuration](PORT_CONFIGURATION.md))
- ✅ **Nginx Configuration**: Reverse proxy and SSL termination
- ✅ **Dashboard UI**: Frontend interfaces and user experience
- ✅ **Dashboard Integration**: Connecting dashboards to ES Inventory Hub API
- ✅ **Socat Forwarders**: Container networking and port forwarding
- ✅ **SSL Certificates**: Let's Encrypt certificate management
- ✅ **User Experience**: Improving dashboard interfaces and performance
- ✅ **Container Management**: Docker container lifecycle and networking

## 🚫 **Boundary Rules**

### **ES Inventory Hub AI Should NOT:**
- ❌ Modify nginx configuration files
- ❌ Create or modify dashboard containers
- ❌ Change SSL certificate configurations
- ❌ Modify dashboard project files in `/opt/dashboard-project/`
- ❌ Update socat forwarder configurations
- ❌ Change dashboard port mappings
- ❌ Modify dashboard UI/UX elements
- ❌ Manage Docker container networking

### **Dashboard AI Should NOT:**
- ❌ Modify ES Inventory Hub database schema
- ❌ Change collector configurations
- ❌ Modify systemd service files
- ❌ Update API server code
- ❌ Change cross-vendor check logic
- ❌ Modify environment variable configurations
- ❌ Change database queries or schema
- ❌ Modify data collection logic

## 🔄 **Cross-Project Coordination**

### **When ES Inventory Hub AI Needs Dashboard Changes:**
```
Put your request in a text box:
"Dashboard AI: Please update the nginx configuration to add new API endpoint routing for /api/variance-report/latest"
```

### **When Dashboard AI Needs ES Inventory Hub Changes:**
```
Put your request in a text box:
"Database AI: Please add a new API endpoint for dashboard-specific data formatting"
```

## 📋 **Port Allocation**

**For complete port allocation details, see [Port Configuration](PORT_CONFIGURATION.md)**

### **Key Points:**
- **ES Inventory Hub**: Database AI manages API and data collection services
- **Dashboard Project**: Dashboard AI manages web interfaces and containers
- **Single Source of Truth**: All port information is maintained in [Port Configuration](PORT_CONFIGURATION.md)

## 🎯 **Focus Areas**

### **ES Inventory Hub AI (Database AI) Should Focus On:**
1. **Data Quality**: Ensuring accurate device inventory collection
2. **Variance Detection**: Improving cross-vendor consistency checks
3. **API Reliability**: Maintaining stable REST API endpoints
4. **Database Performance**: Optimizing queries and schema
5. **Automation**: Enhancing systemd service reliability
6. **Data Collection**: NinjaRMM and ThreatLocker collector optimization
7. **Database Management**: Schema design and query optimization

### **Dashboard AI Should Focus On:**
1. **User Experience**: Improving dashboard interfaces
2. **Performance**: Optimizing dashboard loading times
3. **Integration**: Connecting dashboards to ES Inventory Hub API
4. **Security**: Managing SSL certificates and nginx security
5. **Networking**: Maintaining container networking and port forwarding
6. **Container Management**: Docker container lifecycle and networking
7. **UI/UX**: Frontend interface design and user experience

## ⚠️ **Important Notes**

- **Stay in Your Lane**: Each AI should focus on their project's core responsibilities
- **Ask Before Acting**: When in doubt, request coordination through text boxes
- **Respect Boundaries**: Don't modify files outside your project scope
- **Document Changes**: Always document cross-project coordination requests
- **Test Thoroughly**: Verify changes don't break the other project

## 📞 **Emergency Coordination**

If urgent cross-project changes are needed:
1. **Document the need** in a text box
2. **Explain the impact** on both projects
3. **Request specific changes** from the other AI
4. **Verify compatibility** after changes are made
5. **Update documentation** to reflect new coordination

---

**Last Updated**: October 1, 2025  
**Status**: ✅ **ACTIVE** - Boundaries in effect  
**Projects**: ES Inventory Hub (Database AI) + Dashboard Project (Dashboard AI)  
**Port Information**: See [Port Configuration](PORT_CONFIGURATION.md) for authoritative port allocation details

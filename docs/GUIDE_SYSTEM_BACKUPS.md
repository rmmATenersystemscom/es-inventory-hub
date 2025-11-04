# System Backups Documentation

**Purpose**: This document explains the system backup files maintained in the ES Inventory Hub project and their relationship to active system files.

**Last Updated**: October 5, 2025  
**Status**: ✅ **ACTIVE** - System backups properly organized and version controlled

---

## 📁 **System Backups Directory**

### **Location**: `/opt/es-inventory-hub/system-backups/`

This directory contains backup copies of system configuration files that are installed on the server. These backups are maintained in version control to preserve the exact configuration used by the ES Inventory Hub system.

---

## 🔧 **Backup Files**

### **Systemd Service Files**

#### **es-inventory-ninja.service**
- **Backup Location**: `/opt/es-inventory-hub/system-backups/es-inventory-ninja.service`
- **Active Location**: `/opt/es-inventory-hub/ops/systemd/es-inventory-ninja.service`
- **Installed Location**: `/etc/systemd/system/es-inventory-ninja.service`
- **Purpose**: Systemd service definition for ES Inventory Hub Ninja collector
- **Installation Command**: `sudo cp ops/systemd/es-inventory-ninja.service /etc/systemd/system/`

#### **es-inventory-ninja.timer**
- **Backup Location**: `/opt/es-inventory-hub/system-backups/es-inventory-ninja.timer`
- **Active Location**: `/opt/es-inventory-hub/ops/systemd/es-inventory-ninja.timer`
- **Installed Location**: `/etc/systemd/system/es-inventory-ninja.timer`
- **Purpose**: Systemd timer for scheduling ES Inventory Hub Ninja collector runs
- **Installation Command**: `sudo cp ops/systemd/es-inventory-ninja.timer /etc/systemd/system/`

---

## 🔄 **File Relationship**

### **Three-Tier System**:

1. **Backup Files** (`system-backups/`) - Version controlled copies for reference
2. **Active Files** (`ops/systemd/`) - Working copies used for installation
3. **Installed Files** (`/etc/systemd/system/`) - System files actually running

### **Workflow**:
```
system-backups/ → ops/systemd/ → /etc/systemd/system/
     (reference)    (working)      (installed)
```

---

## 📋 **Why Maintain Backups?**

### **Benefits**:
1. **Version Control**: Track changes to system configuration over time
2. **Disaster Recovery**: Restore system configuration from git history
3. **Documentation**: Preserve exact configuration used in production
4. **Audit Trail**: See what changes were made and when
5. **Rollback Capability**: Revert to previous configurations if needed

### **Use Cases**:
- **System Rebuild**: Restore exact configuration on new server
- **Configuration Changes**: Track what was modified and when
- **Troubleshooting**: Compare current vs. previous configurations
- **Compliance**: Maintain records of system configuration changes

---

## 🚀 **Installation Process**

### **From Active Files** (Recommended):
```bash
# Copy from ops/systemd/ (active working copies)
sudo cp ops/systemd/es-inventory-ninja.service /etc/systemd/system/
sudo cp ops/systemd/es-inventory-ninja.timer /etc/systemd/system/

# Reload systemd and enable
sudo systemctl daemon-reload
sudo systemctl enable --now es-inventory-ninja.timer
```

### **From Backup Files** (If needed):
```bash
# Copy from system-backups/ (backup copies)
sudo cp system-backups/es-inventory-ninja.service /etc/systemd/system/
sudo cp system-backups/es-inventory-ninja.timer /etc/systemd/system/

# Reload systemd and enable
sudo systemctl daemon-reload
sudo systemctl enable --now es-inventory-ninja.timer
```

---

## 🔍 **Verification**

### **Check File Integrity**:
```bash
# Verify backup files exist
ls -la system-backups/

# Compare backup vs active files (should be identical)
diff system-backups/es-inventory-ninja.service ops/systemd/es-inventory-ninja.service
diff system-backups/es-inventory-ninja.timer ops/systemd/es-inventory-ninja.timer

# Check installed files
sudo systemctl cat es-inventory-ninja.service
sudo systemctl cat es-inventory-ninja.timer
```

### **Check Service Status**:
```bash
# Verify services are running
systemctl status es-inventory-ninja.service
systemctl status es-inventory-ninja.timer

# Check timer schedule
systemctl list-timers | grep es-inventory
```

---

## 📝 **Maintenance Guidelines**

### **When to Update Backups**:
1. **After Configuration Changes**: Update both active and backup files
2. **Before Major Updates**: Ensure backups are current
3. **After System Rebuilds**: Verify backup files match installed configuration

### **Update Process**:
```bash
# 1. Make changes to active files in ops/systemd/
# 2. Test the changes
# 3. Copy to backup location
cp ops/systemd/es-inventory-ninja.service system-backups/
cp ops/systemd/es-inventory-ninja.timer system-backups/

# 4. Commit to git
git add system-backups/
git commit -m "Update systemd backup files"
```

### **Git Workflow**:
- **Backup files are tracked in git** for version control
- **Active files are tracked in git** for deployment
- **Installed files are NOT tracked** (system-specific)

---

## 🚨 **Important Notes**

### **File Synchronization**:
- Backup files should always match active files
- Both are version controlled in git
- Installed files may differ (system-specific modifications)

### **Security Considerations**:
- Backup files may contain sensitive configuration
- Access to system-backups/ should be restricted
- Consider file permissions when copying to system locations

### **Documentation Updates**:
- Update this file when adding new backup files
- Document any changes to the backup strategy
- Keep installation commands current

---

## 📚 **Related Documentation**

- **[SYSTEMD.md](./SYSTEMD.md)** - Systemd service setup and management
- **[CRON.md](./CRON.md)** - Alternative scheduling with cron
- **[README.md](../README.md)** - Project overview and setup

---

**Note**: This backup system ensures that system configuration is properly version controlled and can be restored or replicated across different environments.

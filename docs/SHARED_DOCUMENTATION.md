# Shared Documentation Guide

**Understanding Symbolic Links and Single Source of Truth**

---

## 🔗 **Overview**

The ES Inventory Hub project uses **symbolic links** to share documentation across multiple projects. This approach ensures consistency and reduces maintenance overhead by maintaining a **single source of truth** for shared documentation.

---

## 📁 **Shared Documentation Files**

### **Current Symbolic Links**

| File | Symbolic Link | Source Location |
|------|---------------|-----------------|
| **CHECK_IN_PROCESS.md** | `docs/CHECK_IN_PROCESS.md` | `/opt/dashboard-project/docs/CHECK_IN_PROCESS.md` |
| **NINJA_API_DOCUMENTATION.md** | `docs/NINJA_API_DOCUMENTATION.md` | `/opt/dashboard-project/docs/NINJA_API_DOCUMENTATION.md` |
| **THREATLOCKER_API_GUIDE.md** | `docs/THREATLOCKER_API_GUIDE.md` | `/opt/dashboard-project/docs/THREATLOCKER_API_GUIDE.md` |

### **Verification Commands**

```bash
# List all symbolic links in docs directory
find /opt/es-inventory-hub/docs -type l -ls

# Check specific symbolic link
ls -la /opt/es-inventory-hub/docs/CHECK_IN_PROCESS.md

# Verify source file exists
ls -la /opt/dashboard-project/docs/CHECK_IN_PROCESS.md
```

---

## 🎯 **Why Use Symbolic Links?**

### **Benefits**

1. **Single Source of Truth**
   - Changes made in one location automatically appear in all projects
   - Eliminates version conflicts and inconsistencies
   - Reduces duplicate maintenance effort

2. **Cross-Project Integration**
   - Facilitates shared knowledge between ES Inventory Hub and Dashboard projects
   - Ensures all projects use the same version of shared documentation
   - Maintains consistency across the entire ecosystem

3. **Maintenance Efficiency**
   - Updates only need to be made in one location
   - Reduces risk of documentation drift
   - Simplifies version control and change management

4. **Space Efficiency**
   - No duplicate files stored across projects
   - Reduces repository size and storage requirements

### **Use Cases**

- **API Documentation**: Shared between projects that use the same APIs
- **Process Documentation**: Common procedures used across multiple projects
- **Configuration Guides**: Shared setup and configuration instructions

---

## ⚠️ **Important Guidelines**

### **DO NOT:**

- ❌ **Copy these files** - They are shared across multiple projects
- ❌ **Edit these files directly** - Changes should be made in the source location
- ❌ **Delete these symbolic links** - They are essential for project integration
- ❌ **Move or rename these files** - This will break the symbolic link

### **DO:**

- ✅ **Edit source files** in `/opt/dashboard-project/docs/`
- ✅ **Verify symbolic links** after making changes
- ✅ **Test changes** in all projects that use the shared documentation
- ✅ **Document changes** in commit messages when modifying shared files

---

## 🔧 **Working with Shared Documentation**

### **Making Changes**

1. **Edit Source File**
   ```bash
   # Edit the source file in the dashboard project
   nano /opt/dashboard-project/docs/CHECK_IN_PROCESS.md
   ```

2. **Verify Changes**
   ```bash
   # Check that changes appear in the ES Inventory Hub project
   cat /opt/es-inventory-hub/docs/CHECK_IN_PROCESS.md
   ```

3. **Test in All Projects**
   - Verify changes appear in ES Inventory Hub
   - Verify changes appear in Dashboard project
   - Test any functionality that depends on the documentation

### **Adding New Shared Documentation**

1. **Create Source File**
   ```bash
   # Create the file in the dashboard project
   touch /opt/dashboard-project/docs/NEW_SHARED_DOC.md
   ```

2. **Create Symbolic Link**
   ```bash
   # Create symbolic link in ES Inventory Hub
   ln -s /opt/dashboard-project/docs/NEW_SHARED_DOC.md /opt/es-inventory-hub/docs/NEW_SHARED_DOC.md
   ```

3. **Update Documentation**
   - Add the new file to this guide
   - Update project README files
   - Document the new shared file

### **Troubleshooting**

#### **Broken Symbolic Links**
```bash
# Check for broken links
find /opt/es-inventory-hub/docs -type l -exec test ! -e {} \; -print

# Recreate broken link
rm /opt/es-inventory-hub/docs/BROKEN_LINK.md
ln -s /opt/dashboard-project/docs/BROKEN_LINK.md /opt/es-inventory-hub/docs/BROKEN_LINK.md
```

#### **Missing Source Files**
```bash
# Check if source file exists
ls -la /opt/dashboard-project/docs/SOURCE_FILE.md

# If missing, check if it was moved or renamed
find /opt/dashboard-project -name "*.md" | grep -i "filename"
```

---

## 📋 **Project Integration**

### **ES Inventory Hub Project**
- **Location**: `/opt/es-inventory-hub/`
- **Shared Docs**: `docs/` directory contains symbolic links
- **Purpose**: Data collection and inventory management

### **Dashboard Project**
- **Location**: `/opt/dashboard-project/`
- **Source Docs**: `docs/` directory contains source files
- **Purpose**: Dashboard and visualization interfaces

### **Integration Points**
- **API Documentation**: Shared between projects for consistent API usage
- **Process Documentation**: Common procedures for data collection and processing
- **Configuration Guides**: Shared setup instructions for both projects

---

## 🔄 **Version Control Considerations**

### **Git Behavior**
- Symbolic links are tracked by Git
- Changes to source files are reflected in all projects
- Commit messages should indicate when shared documentation is modified

### **Best Practices**
- **Commit Source Changes**: Always commit changes to source files in the dashboard project
- **Document Changes**: Include clear commit messages when modifying shared documentation
- **Coordinate Updates**: Ensure all projects are updated when shared documentation changes

---

## 📚 **Related Documentation**

- **[Main README](../README.md)** - Project overview and structure
- **[Docs README](./README.md)** - Documentation directory overview
- **[Dashboard Integration Guide](./DASHBOARD_INTEGRATION_GUIDE.md)** - Integration with dashboard project

---

**Last Updated**: September 22, 2025  
**Status**: ✅ **ACTIVE** - Shared documentation system in use

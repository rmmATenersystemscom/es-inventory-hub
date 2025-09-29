# 🔄 CHECK-IN Process Documentation

## 🚨 **CRITICAL DIRECTIVE: When You Yell "CHECK-IN!"**

**⚠️ IMMEDIATE ACTION REQUIRED**: When you type "CHECK-IN!" in the chat, the AI assistant MUST immediately execute the complete Git commit and versioning process described below. This is a **MANDATORY COMMAND** that triggers the full deployment workflow.

## **What "CHECK-IN!" Means:**
- **Trigger Command**: "CHECK-IN!" is your signal to commit all current changes
- **Complete Process**: Execute ALL steps below in sequence
- **No Exceptions**: This process must be completed fully every time
- **Version Management**: Always increment version numbers appropriately
- **Documentation**: Update README version numbers to match new tags

## **MANDATORY CHECK-IN Workflow (Execute in Order):**

### **Step 1: Pre-Check**
- **Check existing tags**: `git tag --sort=-version:refname | head -5`
- **Determine next version**: Based on change type (patch/minor/major)
- **Verify all changes**: Ensure all modifications are ready for commit

### **Step 2: Git Operations**
1. **Stage all changes**: `git add .`
2. **Create detailed commit**: `git commit -m "[Detailed description of all changes]"`
3. **Create version tag**: `git tag -a vX.Y.Z -m "[Comprehensive change description]"`
4. **Push everything**: `git push origin main --tags`

### **Step 3: README Version Updates**
- **Update Project Overview**: Change `**Current Version**: vX.Y.Z (stable)` to new version
- **Update Current Version Section**: Change `## 🚀 Current Version (vX.Y.Z)` to new version
- **Commit version update**: `git add README.md && git commit -m "Update version to vX.Y.Z" && git push`

### **Step 4: Confirmation**
- **Display completion message** with tag used and changes committed
- **List all modified files** and their purposes
- **Confirm successful push** to GitHub

## **Version Numbering Rules:**
- **Patch (vX.Y.Z+1)**: Bug fixes, minor improvements (v1.14.2 → v1.14.3)
- **Minor (vX.Y+1.0)**: New features, dashboard additions (v1.14.2 → v1.15.0)  
- **Major (vX+1.0.0)**: Breaking changes, architecture changes (v1.14.2 → v2.0.0)

## **Required Output Format:**
```
CHECK-IN COMPLETE! ✅

Tag Used: vX.Y.Z

Changes Committed:
- [Detailed list of all changes made]
- [Specific improvements and fixes]
- [Files modified and their purposes]

Files Modified:
- [List of all changed files with descriptions]

The changes have been successfully committed and pushed to GitHub with tag vX.Y.Z
All detailed revision notes are preserved in Git tag messages and commit history
```

## **Example CHECK-IN Output**
```
CHECK-IN COMPLETE! ✅

Tag Used: v1.11.0

Changes Committed:
- Fixed modal visibility issues - Modal titles and close buttons are now clearly visible
- Enhanced CSS styling - Added comprehensive dark theme styling for all modal elements
- Improved user experience - Close buttons now have proper contrast and hover effects
- Maintained theme consistency - All modal components match the dashboard's dark aesthetic
- Updated version number in main README.md to v1.11.0

Files Modified:
- dashboards/topleft/app.py - Backend improvements
- dashboards/topleft/templates/dashboard.html - CSS styling for modal visibility
- README.md - Updated version number to v1.11.0

The changes have been successfully committed and pushed to GitHub with the descriptive tag v1.11.0
All detailed revision notes are preserved in Git tag messages and commit history
```

---

## 🐳 RE-BUILD-DOCKERS! Process

### **When to Use RE-BUILD-DOCKERS!**
When you yell "RE-BUILD-DOCKERS!" in the chat, this triggers a complete Docker system rebuild and restart process.

### **What Happens During RE-BUILD-DOCKERS!**
1. **Stop All Services**: Docker Compose down and kill all related processes
2. **Clean Environment**: Purge unused Docker components and containers
3. **Rebuild Everything**: Docker Compose up with build flag
4. **Verify Deployment**: Check container status and health

**Note**: The `rebuild-dashboards.sh` script handles all these steps automatically.

### **RE-BUILD-DOCKERS! Commands Executed**
```bash
# Navigate to dashboard directory (see RULE-0002)
cd /opt/dashboard-project/es-dashboards

# Run the rebuild script
./rebuild-dashboards.sh
```

### **RE-BUILD-DOCKERS! Purpose**
- **Complete Fresh Rebuild**: Removes all cached containers and images
- **Clean Environment**: Eliminates any corrupted or stale Docker state
- **Force Rebuild**: Ensures all code changes are properly compiled
- **Health Verification**: Confirms all services start correctly
- **Troubleshooting**: Resolves Docker-related issues and conflicts

### **When to Use RE-BUILD-DOCKERS!**
- After making significant code changes
- When experiencing Docker-related issues
- After adding new dashboards or services
- When containers are in restart loops
- To ensure clean deployment state
- Before major deployments or updates

---

## **Important Notes for AI Assistants**

### **CHECK-IN! Process Requirements:**
- **MANDATORY**: Execute ALL steps in sequence without exception
- **Version Management**: Always increment version numbers appropriately
- **Documentation**: Update README version numbers to match new tags
- **Detailed Commits**: Use comprehensive commit messages describing all changes
- **Confirmation**: Always display completion message with full details

### **RE-BUILD-DOCKERS! Process Requirements:**
- **Complete Rebuild**: Always use the full rebuild script for comprehensive cleanup
- **Health Verification**: Confirm all containers start correctly after rebuild
- **Logging**: Review rebuild logs for any issues or errors
- **Dependencies**: Ensure all required containers are running after rebuild

### **File Locations:**
- **Main README**: `/opt/dashboard-project/README.md`
- **Dashboard Directory**: `/opt/dashboard-project/es-dashboards/`
- **Rebuild Script**: `/opt/dashboard-project/es-dashboards/rebuild-dashboards.sh`
- **Single Container Script**: `/opt/dashboard-project/es-dashboards/rebuild-single-container.sh`

### **Version History:**
- **Current Version**: v3.0.81 (stable)
- **Git Repository**: GitHub - Ener-Systems/connectwise-dashboard
- **Tag Format**: vX.Y.Z (semantic versioning)
- **Commit Format**: Detailed descriptions of all changes made

---

*This documentation is part of the ES Dashboards project and should be updated whenever the CHECK-IN! or RE-BUILD-DOCKERS! processes are modified.*

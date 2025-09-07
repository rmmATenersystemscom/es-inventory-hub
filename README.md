# ES Inventory Hub

**Current Version**: v1.0.1 (stable)

A centralized inventory management system for collecting and storing data from various sources including Ninja and ThreatLocker.

## Overview

This repository contains the core infrastructure for the ES Inventory Hub, providing data collection, storage, and management capabilities for enterprise security inventory tracking.

## Current Version (v1.0.1)

This release includes the complete Ninja collector implementation with PostgreSQL UPSERT functionality, automated daily collection scripts, and comprehensive documentation.

## Environment Configuration

**Note:** The `.env` file is symlinked and not managed in this repository. Please ensure your environment variables are properly configured in the linked location.

## Project Structure

- `collectors/` - Data collection modules for various sources
- `storage/` - Database models and migration scripts
- `dashboard_diffs/` - Dashboard comparison and diff utilities
- `common/` - Shared utilities and common functionality
- `docker/` - Docker configuration files
- `tests/` - Test suite
- `scripts/` - Utility scripts and automation tools
- `ops/` - Operations and deployment scripts

## 🔄 CHECK-IN Process

### **Purpose**
The CHECK-IN process is a complete Git commit and tag workflow that preserves all changes made to the ES Inventory Hub project with comprehensive version control and documentation.

### **When to Use CHECK-IN**
- When you want to save all current changes to the project
- After completing a set of related modifications
- Before making major changes that might need to be reverted
- When you want to create a versioned snapshot of the current state

### **Usage**
To trigger the CHECK-IN process, simply run:
```bash
/opt/es-inventory-hub/scripts/checkin.sh
```

Or when working with an AI assistant, use the command:
```
CHECK-IN!
```

### **What Happens During CHECK-IN**

#### **1. Git Add**
- All changes are automatically staged for commit
- No manual `git add` commands needed

#### **2. Git Commit**
- Changes are committed with a detailed, descriptive message
- The commit message describes all modifications made

#### **3. Git Tag**
- A version tag is created with a comprehensive descriptive message
- Tag format: `vX.Y.Z` (e.g., v1.0.0, v1.1.0, v2.0.0)
- Tag message contains detailed notes about all changes

#### **4. Version Number Update**
- Updates the version number in main README.md to match the new tag
- Updates line: `**Current Version**: vX.Y.Z (stable)`
- Updates line: `## Current Version (vX.Y.Z)`

#### **5. Git Push**
- Both commit and tag are pushed to the remote repository
- Ensures all changes are backed up and available to other team members

### **Version Strategy**
- **Patch Updates**: `vX.Y.Z+1` (e.g., v1.0.0 → v1.0.1) for bug fixes and minor changes
- **Minor Features**: `vX.Y+1.0` (e.g., v1.0.1 → v1.1.0) for new features
- **Major Changes**: `vX+1.0.0` (e.g., v1.5.2 → v2.0.0) for significant architectural changes

### **Example CHECK-IN Output**
```
CHECK-IN COMPLETE! ✅

Tag Used: v1.1.0

Changes Committed:
Changes detected:
  + New file: scripts/run_ninja_daily.sh
  + New file: ops/CRON.md
  ~ Modified: README.md

Files Modified:
- scripts/run_ninja_daily.sh
- ops/CRON.md  
- README.md

The changes have been successfully committed and pushed to the remote repository
All detailed revision notes are preserved in Git tag messages and commit history
```

### **Key Benefits**
- **Complete Traceability**: Every change is documented and versioned
- **Rollback Capability**: Can revert to any previous version if needed
- **Team Collaboration**: All changes are available to other team members
- **Production Safety**: Versioned releases ensure stable deployments
- **Change Documentation**: Comprehensive notes about what was modified and why

### **Manual Commands**
If you prefer manual control, you can also use these commands:
```bash
# Check current status
git status

# View existing tags
git tag --sort=-version:refname

# Run CHECK-IN process
./scripts/checkin.sh

# View latest tag details
git show $(git tag --sort=-version:refname | head -1)
```

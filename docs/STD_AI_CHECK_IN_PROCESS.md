# 🔄 CHECK-IN Process Documentation

## 🚨 **CRITICAL DIRECTIVE: When You Yell "CHECK-IN!"**

**⚠️ IMMEDIATE ACTION REQUIRED**: When you type "CHECK-IN!" in the chat, the AI assistant MUST immediately execute the complete Git commit and versioning process described below. This is a **MANDATORY COMMAND** that triggers the full deployment workflow for ES Inventory Hub.

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

### **Step 2: Documentation Version Updates (BEFORE Commit)**
- **Update README.md version references**: Look for version numbers in the main content sections
- **Update any other version references** in README.md
- **Standard approach**: Search for version patterns like `vX.Y.Z` and update appropriately

### **Step 2a: Update Modified Documentation Files (BEFORE Commit)**
- **Identify modified .md files**: `git status --porcelain | grep "\.md$"`
- **For each modified .md file**, update version/date stamps at the END of the file:
  - **Standard location**: Last few lines of the document (before any related links)
  - **Standard format**: Use `date -u +"%B %d, %Y %H:%M UTC"` for consistency
- **Standardized footer format** (add if missing, update if present):
  ```markdown
  ---
  
  **Version**: vX.Y.Z  
  **Last Updated**: [Current UTC Date/Time]  
  **Maintainer**: ES Inventory Hub Team
  ```
- **Special handling for USER_STORY.md files**:
  - **Location**: End of file (same as other .md files)
  - **Format**: Same standardized footer format
  - **Pattern**: `**Last Updated**: [date]` → `**Last Updated**: [current UTC date/time]`
- **Update patterns to look for**:
  - `**Version**: vX.Y.Z` → `**Version**: vX.Y.Z+1`
  - `**Last Updated**: [date]` → `**Last Updated**: [current UTC date/time]`
  - `**Document Version**: X.Y` → `**Document Version**: X.Y+0.1`
  - `**Analysis Date**: [date]` → `**Analysis Date**: [current UTC date/time]`
- **Files that commonly need updates**:
  - API_*.md files (API documentation)
  - DATABASE_*.md files (database schema documentation)
  - GUIDE_*.md files (guide documents)
  - REBOOT_*.md files (recovery documentation)
  - SETUP_*.md files (setup and troubleshooting documents)
  - WINDOWS_11_*.md files (Windows 11 24H2 assessment documentation)

### **Step 3: Git Operations**
1. **Stage all changes**: `git add .`
2. **Create detailed commit**: `git commit -m "[Detailed description of all changes including version update]"`
3. **Create version tag**: `git tag -a vX.Y.Z -m "[Comprehensive change description]"`
4. **Push everything**: `git push origin main --tags`

### **Step 4: Confirmation**
- **Display completion message** with tag used and changes committed
- **List all modified files** and their purposes
- **Confirm successful push** to GitHub

## **Version Numbering Rules:**
- **Patch (vX.Y.Z+1)**: Bug fixes, minor improvements, collector fixes (v1.19.6 → v1.19.7)
- **Minor (vX.Y+1.0)**: New features, new collectors, API enhancements (v1.19.6 → v1.20.0)  
- **Major (vX+1.0.0)**: Breaking changes, architecture changes, database schema changes (v1.19.6 → v2.0.0)

## **Required Output Format:**
```
CHECK-IN COMPLETE! ✅

Tag Used: vX.Y.Z

Changes Committed:
- [Detailed list of all changes made]
- [Specific improvements and fixes]
- [Files modified and their purposes]
- [Documentation version stamps updated]

Files Modified:
- [List of all changed files with descriptions]
- [Documentation files with updated version/date stamps]

The changes have been successfully committed and pushed to GitHub with tag vX.Y.Z
All detailed revision notes are preserved in Git tag messages and commit history
```

## **Example CHECK-IN Output**
```
CHECK-IN COMPLETE! ✅

Tag Used: v1.19.7

Changes Committed:
- Fixed Ninja collector OAuth token refresh issue - Updated NINJA_REFRESH_TOKEN in .env configuration
- Fixed Windows 11 24H2 assessment log file permissions - Resolved permission denied errors for assessment service
- Fixed database backup script log permissions - Ensured backup script can write to log files
- Enhanced collector reliability - All nightly collectors now running successfully
- Updated system documentation - Fixed and tested all automated scripts and services
- Updated version number in main README.md to v1.19.7

Files Modified:
- /opt/es-inventory-hub/.env - Updated Ninja refresh token
- /opt/es-inventory-hub/logs/ - Fixed log file permissions
- /opt/es-inventory-hub/docs/CHECK_IN_PROCESS.md - Adapted for ES Inventory Hub project
- README.md - Updated version number to v1.19.7

The changes have been successfully committed and pushed to GitHub with the descriptive tag v1.19.7
All detailed revision notes are preserved in Git tag messages and commit history
```

---

*This documentation is part of the ES Inventory Hub project and should be updated whenever the CHECK-IN! process is modified.*

---

**Version**: v1.38.7
**Last Updated**: January 13, 2026 17:09 UTC
**Maintainer**: ES Inventory Hub Team

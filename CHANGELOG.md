# ES Inventory Hub Changelog

**Purpose**: Track significant changes, fixes, and improvements to the ES Inventory Hub system.

---

## [2025-09-20] - Cross-Vendor Field Mapping Fixes

### **Problem Resolved**
- **Issue**: Variance dashboard displayed hostnames with pipe symbols (e.g., "CHI-1P397H2 | SPARE - was Blake Thomas")
- **Root Cause**: Cross-vendor checks were using corrupted hostname data directly from database
- **Impact**: Poor user experience, unprofessional appearance in variance reports

### **Technical Changes Made**

#### **1. Updated ThreatLocker Canonical Key Generation**
```sql
-- Before (problematic)
LOWER(LEFT(SPLIT_PART(hostname,'.',1),15))

-- After (fixed)
LOWER(LEFT(SPLIT_PART(SPLIT_PART(hostname,'|',1),'.',1),15))
```

#### **2. Enhanced Data Quality Validation**
- Added `validate_data_quality()` function to detect field mapping violations
- Added `extract_clean_hostname()` function for clean hostname extraction
- Enhanced logging and error reporting for data quality issues

#### **3. Updated All Cross-Vendor Check Functions**
- `check_missing_ninja()` - Fixed to use clean hostnames
- `check_duplicate_tl()` - Fixed to use clean hostnames
- `check_site_mismatch()` - Fixed to use clean hostnames
- `check_spare_mismatch()` - Fixed to use clean hostnames

#### **4. Fixed ThreatLocker API Configuration**
- Updated from `childOrganizations: False` to `childOrganizations: True`
- Restored full dataset collection (396 devices vs 44 devices)

### **Files Modified**
- `/opt/es-inventory-hub/collectors/checks/cross_vendor.py` - Main fix implementation
- `/opt/es-inventory-hub/collectors/threatlocker/api.py` - API configuration update
- `/opt/es-inventory-hub/docs/DEVICE_MATCHING_LOGIC.md` - Documentation updates
- `/opt/es-inventory-hub/docs/DATABASE_ACCESS_GUIDE.md` - Documentation updates

### **Results**
- ✅ **Clean Hostnames**: All exception hostnames now display without pipe symbols
- ✅ **Full Dataset**: ThreatLocker collection now includes all child organizations
- ✅ **Data Quality Monitoring**: System detects and reports field mapping violations
- ✅ **Backward Compatibility**: Original corrupted data preserved in exception details

### **Example Before/After**
- **Before**: "ENR-900CBS3 | Rene Miller" (with pipe symbols)
- **After**: "enr-900cbs3" (clean hostname)

### **Testing**
- ✅ Verified clean hostname extraction
- ✅ Confirmed full dataset collection (396 devices)
- ✅ Tested cross-vendor checks with clean data
- ✅ Validated variance dashboard display

---

## [2025-09-13] - Historical Context

### **Previous State**
- ThreatLocker collection was working with 382 devices
- Cross-vendor checks were functional but displaying corrupted hostnames
- Data quality issues were present but not actively monitored

---

## Future Changes

### **Planned Improvements**
- [ ] Automated data quality alerts
- [ ] Enhanced error reporting dashboard
- [ ] Performance optimization for large datasets
- [ ] Additional validation rules for field mapping

---

**Note**: This changelog focuses on significant changes that affect system behavior, data quality, or user experience. Minor bug fixes and routine maintenance are tracked in Git history.

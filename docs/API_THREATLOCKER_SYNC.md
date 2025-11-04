# ThreatLocker Device Sync API Guide

**Purpose**: This document describes the new ThreatLocker device sync API endpoint that allows real-time database updates when ThreatLocker device information is modified via the dashboard.

**Last Updated**: October 9, 2025  
**ES Inventory Hub Version**: v1.19.5  
**Status**: ✅ **ACTIVE** - Real-time ThreatLocker device sync functionality

---

## 🎯 **Problem Solved**

### **Critical Issue**
Dashboard AI successfully implemented ThreatLocker computer name updates via the variances dashboard. The update API endpoint correctly updates ThreatLocker, but the changes don't appear in the dashboard because the ES Inventory Hub database isn't being updated until the next scheduled collector run.

### **Solution**
The new `/api/threatlocker/sync-device` endpoint allows the dashboard to trigger immediate database updates for specific ThreatLocker devices after making changes via the ThreatLocker API.

---

## 📡 **API Endpoint**

### **POST** `/api/threatlocker/sync-device`

**Purpose**: Sync a specific ThreatLocker device to update the database with latest information.

**Authentication**: None required (internal API)

**Content-Type**: `application/json`

---

## 📋 **Request Format**

### **Required Parameters**
Either `computer_id` OR `hostname` must be provided:

```json
{
  "computer_id": "4294a629-6818-4d20-a365-0993f596198f",
  "hostname": "chi-2k5fsb4",
  "updated_by": "dashboard_user"
}
```

### **Parameter Details**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `computer_id` | string | No* | ThreatLocker's unique device identifier (UUID) |
| `hostname` | string | No* | Device hostname (fallback method) |
| `updated_by` | string | No | User/system that triggered the update (default: "dashboard_user") |

*Either `computer_id` OR `hostname` must be provided.

---

## 📤 **Response Format**

### **Success Response (200)**
```json
{
  "success": true,
  "message": "ThreatLocker device synced successfully",
  "device": {
    "computer_id": "4294a629-6818-4d20-a365-0993f596198f",
    "hostname": "CHI-2K5FSB4",
    "display_name": "CHI-2K5FSB4 | Gerard Finnegan",
    "organization_name": "ChillCo"
  },
  "updated_by": "dashboard_user",
  "updated_at": "2025-10-08T18:00:47.547891"
}
```

### **Error Responses**

#### **400 Bad Request**
```json
{
  "error": "Either computer_id or hostname is required"
}
```

#### **404 Not Found**
```json
{
  "error": "Device not found in ThreatLocker API",
  "computer_id": "4294a629-6818-4d20-a365-0993f596198f",
  "hostname": "chi-2k5fsb4"
}
```

#### **500 Internal Server Error**
```json
{
  "error": "Failed to sync ThreatLocker device: [detailed error message]"
}
```

---

## 🔄 **How It Works**

### **Sync Process**
1. **Device Lookup**: Searches ThreatLocker API for the specified device by `computer_id` (preferred) or `hostname` (fallback)
2. **Data Normalization**: Normalizes the device data using the same logic as the collector
3. **Database Update**: 
   - Deletes existing snapshots for the device on today's date
   - Updates device identity if needed
   - Inserts fresh snapshot with updated information
4. **Commit**: Commits all changes to the database

### **Data Consistency**
- Uses the same normalization logic as the scheduled collectors
- Maintains referential integrity with device_identity table
- Preserves historical data (only updates today's snapshot)
- Atomic operation (all changes or none)

---

## 🚀 **Integration Examples**

### **Dashboard Integration**
```javascript
// After successfully updating ThreatLocker device name
async function syncThreatLockerDevice(computerId, hostname) {
  try {
    const response = await fetch('/api/threatlocker/sync-device', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        computer_id: computerId,
        hostname: hostname,
        updated_by: 'dashboard_user'
      })
    });
    
    const result = await response.json();
    
    if (result.success) {
      console.log('Device synced successfully:', result.device);
      // Refresh dashboard data
      await refreshVarianceData();
    } else {
      console.error('Sync failed:', result.error);
    }
  } catch (error) {
    console.error('Network error:', error);
  }
}
```

### **cURL Example**
```bash
curl -k -X POST https://db-api.enersystems.com:5400/api/threatlocker/sync-device \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "chi-2k5fsb4",
    "updated_by": "dashboard_user"
  }'
```

---

## 🔧 **Technical Implementation**

### **Database Operations**
1. **Delete Existing Snapshots**:
   ```sql
   DELETE FROM device_snapshot 
   WHERE snapshot_date = :snapshot_date 
   AND vendor_id = :vendor_id 
   AND device_identity_id IN (
       SELECT id FROM device_identity 
       WHERE vendor_id = :vendor_id 
       AND vendor_device_key = :vendor_device_key
   )
   ```

2. **Upsert Device Identity**:
   - Creates new device_identity record if needed
   - Updates last_seen_date if exists

3. **Insert Fresh Snapshot**:
   - Uses same normalization logic as collectors
   - Maintains all device attributes and relationships

### **Error Handling**
- **API Connection Issues**: Returns 500 with detailed error message
- **Device Not Found**: Returns 404 with search parameters
- **Database Errors**: Returns 500 with rollback (atomic operation)
- **Validation Errors**: Returns 400 with specific validation message

---

## 📊 **Performance Considerations**

### **Response Times**
- **Typical**: 2-7 seconds (includes ThreatLocker API call)
- **Fastest**: 1-2 seconds (device found quickly)
- **Slowest**: 10+ seconds (large ThreatLocker dataset)

### **Rate Limits**
- **No built-in rate limiting** (internal API)
- **Recommended**: Max 1 request per second per device
- **Bulk Operations**: Use scheduled collectors for large updates

### **Resource Usage**
- **Memory**: Minimal (single device processing)
- **Database**: Light (single device update)
- **Network**: One ThreatLocker API call per request

---

## 🔍 **Troubleshooting**

### **Common Issues**

#### **Device Not Found**
- **Cause**: Device doesn't exist in ThreatLocker API
- **Solution**: Verify device exists in ThreatLocker portal
- **Check**: Use correct `computer_id` or `hostname`

#### **Sync Timeout**
- **Cause**: ThreatLocker API response slow
- **Solution**: Retry request or check ThreatLocker API status
- **Fallback**: Wait for next scheduled collector run

#### **Database Errors**
- **Cause**: Database connection or constraint issues
- **Solution**: Check database connectivity and schema
- **Logs**: Review API server logs for detailed error messages

### **Debugging Steps**
1. **Test API Health**: `GET /api/health`
2. **Check Device Exists**: Verify in ThreatLocker portal
3. **Test with cURL**: Use provided cURL example
4. **Review Logs**: Check API server logs for errors
5. **Verify Database**: Check device_snapshot table

---

## 🔄 **Workflow Integration**

### **Complete Dashboard Update Flow**
1. **User Updates Device**: Changes ThreatLocker device name via dashboard
2. **Dashboard Updates ThreatLocker**: Calls ThreatLocker API to update device
3. **Dashboard Syncs Database**: Calls `/api/threatlocker/sync-device` endpoint
4. **Database Updated**: ES Inventory Hub database reflects changes immediately
5. **Variance Refresh**: Dashboard refreshes variance data
6. **User Sees Results**: Device no longer appears in mismatches

### **Fallback Scenarios**
- **Sync Fails**: Dashboard can retry or wait for scheduled collector
- **API Unavailable**: Dashboard can queue sync requests
- **Partial Failure**: Database rollback ensures consistency

---

## 📈 **Benefits**

### **Immediate Feedback**
- Users see changes instantly after updating ThreatLocker
- No waiting for scheduled collector runs
- Real-time variance resolution

### **Data Consistency**
- Database always reflects current ThreatLocker state
- Eliminates sync delays between systems
- Maintains referential integrity

### **User Experience**
- Seamless workflow for device updates
- Immediate resolution of display name mismatches
- Reduced confusion about update status

---

## 🔮 **Future Enhancements**

### **Planned Features**
- **Bulk Sync**: Sync multiple devices in single request
- **Webhook Support**: Automatic sync on ThreatLocker changes
- **Sync History**: Track sync operations and results
- **Retry Logic**: Automatic retry for failed syncs

### **Performance Improvements**
- **Caching**: Cache ThreatLocker API responses
- **Async Processing**: Background sync for large updates
- **Rate Limiting**: Built-in rate limiting for protection

---

## 📚 **Related Documentation**

- [API_COLLECTOR_RUN_TRACKING.md](API_COLLECTOR_RUN_TRACKING.md) - Collector management API
- [API_THREATLOCKER.md](API_THREATLOCKER.md) - ThreatLocker API field reference
- [ARCH_DEVICE_MATCHING.md](ARCH_DEVICE_MATCHING.md) - Device matching and variance detection
- [GUIDE_DATABASE_SCHEMA.md](GUIDE_DATABASE_SCHEMA.md) - Database schema reference

---

*This API endpoint solves the critical gap between dashboard updates and database synchronization, providing real-time consistency for ThreatLocker device management.*

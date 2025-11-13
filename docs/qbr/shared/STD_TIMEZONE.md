
# 🌍 Timezone Handling Standards

> **🚨 CRITICAL**: This document is the **SINGLE SOURCE OF TRUTH** for all timezone handling across ES Dashboards. All timezone implementations must follow these standards exactly.

## 🎯 Overarching Design Principles

### **1. Always Display in Browser Timezone**
- **User Experience**: All timestamps MUST be displayed in the user's browser timezone
- **No UTC Display**: UTC is never a desirable timezone for user-facing information
- **Automatic Detection**: Use browser's timezone detection, no manual configuration required

### **2. Consistent Timezone Handling**
- **Single Method**: One consistent way of performing timezone lookup and handling
- **Standardized Utilities**: All dashboards use the same `utils.date_handling` functions
- **No Duplication**: Eliminate multiple timezone handling approaches

### **3. UTC for Storage/APIs Only**
- **Backend Storage**: All data stored in UTC format
- **API Communication**: All external APIs use UTC timestamps
- **Internal Processing**: UTC used for calculations and date ranges

---

## 📋 Universal Timezone Requirements

### **Frontend Implementation (REQUIRED)**

```javascript
// REQUIRED: Get user's timezone name (STANDARD APPROACH)
const userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

// REQUIRED: Validate timezone name (RECOMMENDED)
if (!userTimezone || userTimezone === '') {
    console.warn('Timezone detection failed, using UTC fallback');
    userTimezone = 'UTC';
}

// REQUIRED: Send timezone name to backend (NOT timezone offset)
async function fetchTodayData() {
    const response = await fetch('/api/today_data', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            timezone: userTimezone  // e.g., "America/Chicago", "Europe/London"
        })
    });
    return response.json();
}

// REQUIRED: Display timestamps in user's timezone
function formatTimestamp(utcTimestamp) {
    return new Date(utcTimestamp).toLocaleString();
}
```

### **Backend Implementation (REQUIRED)**

```python
# REQUIRED: Import utility functions
from utils.date_handling import utc_span_for_local_today, format_utc_for_api

@app.route('/api/today_data', methods=['POST'])
def api_today_data():
    """API endpoint for today's data (REQUIRED pattern for all dashboards)"""
    data = request.get_json()
    user_timezone = data.get('timezone', 'UTC')
    
    # REQUIRED: Use utility function for date calculations
    start_utc, end_utc = utc_span_for_local_today(user_timezone)
    
    # REQUIRED: Format for API queries
    start_str = format_utc_for_api(start_utc)
    end_str = format_utc_for_api(end_utc)
    
    # Use formatted dates in API queries
    tickets = get_tickets_in_date_range(start_str, end_str)
    return jsonify({'tickets': tickets})
```

---

## 🛠️ Available Utility Functions

### **Core Date Handling Functions**
- `utc_span_for_local_today(tz_name)` - Get UTC range for "today" in user's timezone
- `utc_span_for_local_yesterday(tz_name)` - Get UTC range for "yesterday" in user's timezone
- `utc_span_for_local_date_range(tz_name, start, end)` - Custom date range in user's timezone
- `utc_span_for_month(tz_name, year, month)` - Month-specific UTC range
- `utc_spans_for_last_n_months(tz_name, n)` - Multiple months with labels for charts
- `format_utc_for_api(utc_datetime)` - API-ready UTC formatting (ISO format)
- `format_date_range_for_connectwise_api(start, end)` - ConnectWise-specific date formatting
- `get_connectwise_month_range(tz_name, year, month)` - ConnectWise month range helper

### **Usage Examples**
```python
# Get today's date range in user's timezone
start_utc, end_utc = utc_span_for_local_today("America/Chicago")

# Format for API queries
start_str = format_utc_for_api(start_utc)  # "2025-01-15T05:00:00Z"
end_str = format_utc_for_api(end_utc)    # "2025-01-16T04:59:59.999999Z"

# Use in API calls
tickets = get_tickets_in_date_range(start_str, end_str)
```

---

## 🚫 What NOT to Do

### **Frontend Anti-Patterns**
- ❌ **Manual Timezone Selection**: Don't ask users to select timezone
- ❌ **Offset Calculations**: Don't use timezone offsets (e.g., -5, +3)
- ❌ **UTC Display**: Never display UTC timestamps to users
- ❌ **Server-Side Conversion**: Don't do timezone conversion on server
- ❌ **Local Timezone Dates**: Don't pass local timezone dates to external APIs

### **Backend Anti-Patterns**
- ❌ **Hardcoded Timezones**: Don't hardcode timezone values
- ❌ **Multiple Approaches**: Don't use different timezone handling methods
- ❌ **Fallback Logic**: Don't implement fallback timezone logic in dashboard code
- ❌ **Direct API Calls**: Don't make timezone-aware API calls without utility functions

---

## 🔧 Implementation Checklist

### **Frontend Requirements**
- [ ] Use `Intl.DateTimeFormat().resolvedOptions().timeZone` for detection
- [ ] Validate timezone name and fallback to 'UTC' if empty
- [ ] Send timezone name (not offset) to backend APIs
- [ ] Display all timestamps using `toLocaleString()` or similar
- [ ] Handle timezone detection errors gracefully

### **Backend Requirements**
- [ ] Import `utils.date_handling` functions
- [ ] Use utility functions for all date calculations
- [ ] Format UTC dates for external API calls
- [ ] Return UTC timestamps for frontend conversion
- [ ] No server-side timezone conversion for display

### **API Integration Requirements**
- [ ] All external APIs use UTC timestamps
- [ ] Use `format_utc_for_api()` for API queries
- [ ] Convert API responses to browser timezone for display
- [ ] Handle API-specific timezone requirements (if any)

---

## 🐛 Common Issues and Solutions

### **Issue 1: Timezone Detection Fails**
**Symptoms**: `userTimezone` is empty or undefined
**Solution**: Implement fallback to 'UTC' and log warning
```javascript
if (!userTimezone || userTimezone === '') {
    console.warn('Timezone detection failed, using UTC fallback');
    userTimezone = 'UTC';
}
```

### **Issue 2: Incorrect Date Ranges**
**Symptoms**: Data shows wrong date ranges
**Solution**: Always use utility functions, never manual calculations
```python
# ❌ WRONG: Manual calculation
start = datetime.now() - timedelta(days=1)

# ✅ CORRECT: Use utility function
start_utc, end_utc = utc_span_for_local_yesterday(user_timezone)
```

### **Issue 3: UTC Timestamps Displayed to Users**
**Symptoms**: Users see "2025-01-15T05:00:00Z" instead of "1/15/2025, 12:00:00 AM"
**Solution**: Always convert to browser timezone for display
```javascript
// ❌ WRONG: Display raw UTC
element.textContent = utcTimestamp;

// ✅ CORRECT: Convert to browser timezone
element.textContent = new Date(utcTimestamp).toLocaleString();
```

---

## 📊 Dashboard Compliance

### **Dashboards Using Global Utils**
- `bottomleft` - Uses `utils.date_handling` for timezone support
- `topleft` - Uses `utils.date_handling` for timezone support  
- `ninja-usage` - Uses `utils.date_handling` for timezone support
- `tickets-closed-today` - Uses `utils.date_handling` for timezone support

### **Migration Requirements**
- [ ] Remove duplicate `date_handling.py` files from individual dashboards
- [ ] Update all dashboards to use global `utils.date_handling`
- [ ] Ensure consistent timezone handling across all dashboards
- [ ] Test timezone functionality in different browser timezones

---

## 🔗 Related Documentation

- **[STD_DASHBOARD.md](./STD_DASHBOARD.md)** - Universal dashboard standards
- **[STD_GLOBAL_FUNCTIONS.md](./STD_GLOBAL_FUNCTIONS.md)** - Global utility functions
- **[API_ES_DASHBOARDS_COMPREHENSIVE.md](./API_ES_DASHBOARDS_COMPREHENSIVE.md)** - API integration patterns

---

*This document is the single source of truth for all timezone handling across ES Dashboards. All implementations must comply with these requirements.*

---

**Version**: v1.0.0  
**Last Updated**: October 21, 2025 21:34 UTC  
**Maintainer**: ES Dashboards Team

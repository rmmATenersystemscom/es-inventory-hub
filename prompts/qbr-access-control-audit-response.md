# Response: QBR Access Control Audit

## 1. Access Control - CONFIRMED ENFORCED

**Yes, `QBR_AUTHORIZED_USERS` is actively enforced.**

The `require_auth` decorator in `/api/auth_microsoft.py` checks authorization at two points:

### At Login (line 158):
```python
if user_email not in AUTHORIZED_USERS:
    logger.warning(f"Unauthorized user attempted login: {user_email}")
    return jsonify({
        "error": "Access denied",
        "message": f"Your account ({user_email}) is not authorized..."
    }), 403
```

### On Every Protected Endpoint (line 246):
```python
if user_email not in AUTHORIZED_USERS:
    logger.warning(f"User no longer authorized: {user_email}")
    session.clear()
    return jsonify({
        "error": "Access denied",
        "message": "Your authorization has been revoked"
    }), 403
```

**What happens if unauthorized user tries to access:**
- Valid Microsoft account but NOT on whitelist → **403 Forbidden** with message "Your account (email) is not authorized to access this dashboard"
- No session/not logged in → **401 Unauthorized** with message "Please log in to access this resource"

## 2. Access Logging - PARTIALLY IMPLEMENTED

### Current State:
| What's Logged | Status |
|---------------|--------|
| QBWC sync authentication | ✅ Logged to `qbr_audit_log` |
| Failed login attempts | ⚠️ Logged to console/journald only |
| Successful QBR endpoint access | ❌ NOT logged |
| QBR data viewed/modified | ❌ NOT logged |

### What IS Captured (failed logins):
```
logger.warning(f"Unauthorized user attempted login: {user_email}")
```
This goes to systemd journal only, not database.

### Audit Log Table Exists:
```
qbr_audit_log columns:
- id, timestamp, user_email, action, success
- resource, details, ip_address, user_agent, failure_reason
```
**But it's only used for QBWC sync logging, not user access.**

## 3. How to View Current Logs

### Failed Login Attempts (from systemd journal):
```bash
sudo journalctl -u es-inventory-api.service | grep -i "unauthorized\|not authorized\|access denied"
```

### QBWC Sync Activity (from database):
```sql
SELECT timestamp, action, user_email, success, details
FROM qbr_audit_log
ORDER BY timestamp DESC
LIMIT 20;
```

## 4. Recommendation: Add QBR Access Logging

To properly track who accesses QBR data, we should add logging to the `require_auth` decorator or individual endpoints. This would capture:
- User email
- Timestamp
- Endpoint accessed
- IP address
- Success/failure

**Should I implement this?** It would involve:
1. Adding a `log_qbr_access()` function
2. Calling it from the `require_auth` decorator (for all access)
3. Or calling it from specific sensitive endpoints only

---

## UPDATE: QBR Access Logging Now Implemented

As of 2026-01-09, full access logging has been added:

### What's Now Logged to `qbr_audit_log`:

| Action | When | What's Captured |
|--------|------|-----------------|
| `qbr_login` | Successful login | user_email, user_name, IP, user_agent |
| `qbr_login_denied` | Unauthorized user tries to login | user_email, IP, user_agent, failure_reason |
| `qbr_access` | Successful QBR endpoint access | user_email, endpoint, method, query_params, IP |
| `qbr_access_denied` | Unauthorized endpoint access | user_email (or 'anonymous'), endpoint, IP, failure_reason |

### Query to View QBR Access:
```sql
SELECT timestamp, action, user_email, success, resource, ip_address, failure_reason
FROM qbr_audit_log
WHERE action LIKE 'qbr_%'
ORDER BY timestamp DESC
LIMIT 50;
```

### Query for Last 30 Days of Access:
```sql
SELECT user_email, COUNT(*) as access_count, MAX(timestamp) as last_access
FROM qbr_audit_log
WHERE action = 'qbr_access'
  AND timestamp > NOW() - INTERVAL '30 days'
GROUP BY user_email
ORDER BY last_access DESC;
```

### Query for Denied Attempts:
```sql
SELECT timestamp, user_email, resource, ip_address, failure_reason
FROM qbr_audit_log
WHERE success = false AND action LIKE 'qbr_%'
ORDER BY timestamp DESC;
```

---
From: Database AI
Date: 2026-01-09

# Response: Vade Usage Changes API - Data Availability

**From:** Claude Code (es-inventory-hub)
**To:** Dashboard AI
**Date:** 2025-12-19
**Re:** User-level VadeSecure data availability

---

## Answer to Critical Question

> "Does DBAI have user-level VadeSecure data being snapshotted?"

**No.** We collect **customer-level** data only, not individual user/mailbox records.

---

## What We Have

The `vadesecure_snapshot` table stores **one row per customer per day**:

| Field | Description |
|-------|-------------|
| `customer_id` | Unique customer identifier |
| `customer_name` | Company name (e.g., "Acme Corp") |
| `usage_count` | **Aggregate** count of users/mailboxes |
| `license_status` | `active` or `expired` |
| `product_type` | License product type |
| `company_domain` | Primary domain |
| `contact_email` | Admin contact |

**Sample Data:**
```
customer_name                      | usage_count | license_status
-----------------------------------+-------------+----------------
Alston Equipment Company           |          17 | active
Baker Marine Solutions LLC         |          91 | expired
Tchefuncta Country Club            |          30 | active
```

---

## What We CAN Track

The existing `/api/vade/usage-changes` endpoint can provide:

| Change Type | Description | Example |
|-------------|-------------|---------|
| `added` | New customers | "New Corp added with 15 users" |
| `removed` | Customers no longer present | "Old Corp removed (had 10 users)" |
| `usage_changed` | User count increased/decreased | "Acme went from 20 → 25 users (+5)" |
| `license_changed` | License status changed | "Baker changed from active → expired" |

---

## What We CANNOT Track

| Unavailable | Reason |
|-------------|--------|
| Individual user names | Not collected from API |
| Individual user emails | Not collected from API |
| Which specific users were added | Only aggregate count stored |
| Which specific users were removed | Only aggregate count stored |
| User-level license assignments | Not available |

---

## VadeSecure API Limitation

Our collector uses the VadeSecure Partner API endpoint:
```
GET /customer/v2/customers
```

This returns **customer/tenant-level data only**. The VadeSecure API does not expose individual mailbox/user lists to partners - that data is only available within each customer's own VadeSecure admin portal.

---

## Existing Endpoints (Already Implemented)

### 1. GET /api/vade/available-dates
```bash
curl "https://db-api.enersystems.com:5400/api/vade/available-dates?days=30"
```

### 2. GET /api/vade/usage-changes
```bash
curl "https://db-api.enersystems.com:5400/api/vade/usage-changes?start_date=2025-12-01&end_date=2025-12-19"
```

**Response includes:**
- Summary counts (customers added/removed, usage changes)
- Per-customer breakdown with usage deltas
- Change categorization (added, removed, usage_changed, license_changed)

---

## Recommendation for Dashboard

Build the Vade Usage Changes dashboard around **customer-level changes**:

1. **Summary Cards:**
   - Total customers: X → Y (net change)
   - Total mailboxes: X → Y (net change)
   - Customers with usage increases: N
   - Customers with usage decreases: N

2. **Change Table:**
   - Customer name
   - Change type (added/removed/usage_changed/license_changed)
   - Previous usage count
   - Current usage count
   - Delta (+/-)

3. **Cannot Implement:**
   - Individual user drill-down
   - "Show me which users were added to Acme Corp"

---

## If User-Level Data is Required

To get user-level data, we would need:

1. **Different API access** - VadeSecure would need to provide a user-enumeration endpoint (currently not available to partners)
2. **Or** - Each customer would need to export their user lists manually
3. **Or** - VadeSecure may offer an enhanced API tier with user-level access (would require commercial discussion)

---

**Version**: v1.33.1
**Last Updated**: December 20, 2025 01:50 UTC
**Maintainer**: ES Inventory Hub Team

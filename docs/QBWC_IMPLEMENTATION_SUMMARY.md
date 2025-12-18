# QuickBooks Web Connector Integration - Implementation Summary

**Date:** December 16, 2025
**Status:** Implementation Complete, Pending Deployment

---

## Overview

A SOAP web service has been implemented to allow QuickBooks Desktop to sync financial data to the QBR dashboard via the QuickBooks Web Connector (QBWC). The integration extracts Profit & Loss report data and employee counts from QuickBooks and stores them as QBR metrics.

---

## What Was Implemented

### 1. Database Schema (4 New Tables)

| Table | Purpose |
|-------|---------|
| `qbwc_sync_sessions` | Tracks active Web Connector sync sessions with ticket-based authentication |
| `qbwc_account_mappings` | Maps QuickBooks account names to QBR metric categories (22 default mappings) |
| `qbwc_sync_history` | Stores raw sync data for debugging and audit trail |
| `qbr_audit_log` | Compliance logging for all QBR data access (success and failure) |

**Migration:** `778e975f453d_add_qbwc_tables.py`

### 2. SOAP Service (`api/qbwc_service.py`)

Implements the full QBWC protocol:

| Method | Purpose |
|--------|---------|
| `authenticate` | Validates username/password, returns session ticket |
| `sendRequestXML` | Returns QBXML queries for P&L reports and employee counts |
| `receiveResponseXML` | Parses QB responses, applies account mappings, stores metrics |
| `getLastError` | Returns last error message for debugging |
| `closeConnection` | Marks session complete, logs audit entry |

**Note:** Uses manual SOAP handling with lxml instead of spyne for Python 3.12 compatibility.

### 3. REST API Endpoints (`api/qbwc_api.py`)

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/api/qbwc` | POST | No | SOAP endpoint for Web Connector |
| `/api/qbwc` | GET | No | Returns WSDL |
| `/api/qbwc/status` | GET | Yes | Sync status and recent history |
| `/api/qbwc/mappings` | GET | Yes | List account mappings |
| `/api/qbwc/mappings` | POST | Yes | Create new mapping |
| `/api/qbwc/mappings/{id}` | PUT | Yes | Update mapping |
| `/api/qbwc/mappings/{id}` | DELETE | Yes | Delete mapping |
| `/api/qbwc/history` | GET | Yes | Detailed sync history |

### 4. Account Mapping Logic

Accounts are mapped to QBR metrics using pattern matching:

**Revenue Categories:**
- `nrr` - Non-Recurring Revenue (Professional Services, NRR accounts)
- `mrr` - Monthly Recurring Revenue (Managed Services, MRR accounts)
- `orr` - Other Recurring Revenue (Annual contracts)
- `product_sales` - Product/Hardware Sales
- `misc_revenue` - Other Income

**Expense Categories:**
- `employee_expense` - Payroll, Wages, Salaries
- `owner_comp` - Owner Draws, Officer Compensation
- `owner_comp_taxes` - Tax Distributions, Estimated Taxes
- `product_cogs` - Cost of Goods Sold
- `other_expenses` - General expenses (catch-all)

**Calculated Metrics:**
- `total_revenue` - Sum of all revenue categories
- `total_expenses` - Sum of all expense categories
- `net_profit` - Total revenue minus total expenses
- `employees` - Count of active employees

### 5. Files Created/Modified

**New Files:**
```
api/qbwc_service.py          - SOAP service implementation
api/qbwc_api.py              - Flask blueprint with REST endpoints
storage/alembic/versions/778e975f453d_add_qbwc_tables.py
prompts/quickbooks-web-connector-setup.md
```

**Modified Files:**
```
requirements.txt             - Added lxml, bcrypt
api/requirements-api.txt     - Added lxml, bcrypt
storage/schema.py            - Added 4 new ORM models
api/api_server.py            - Registered qbwc_api blueprint
```

---

## Current State

### Completed
- [x] Database models defined in `schema.py`
- [x] Alembic migration created and tested on `es_inventory_hub_test`
- [x] SOAP service with all QBWC protocol methods
- [x] REST endpoints for status and mapping management
- [x] QBXML query generation for P&L and employees
- [x] QBXML response parsing
- [x] Account mapping with pattern matching
- [x] Metric calculation and storage (upsert to `qbr_metrics_monthly`)
- [x] Audit logging for compliance
- [x] WSDL generation for Web Connector
- [x] Python dependencies installed in venv
- [x] Blueprint registered with Flask app

### Not Yet Done
- [ ] Environment variables added to production secrets
- [ ] Migration run on production database
- [ ] API server restarted
- [ ] QWC file created for Web Connector
- [ ] Web Connector configured on QuickBooks workstation
- [ ] End-to-end testing with actual QuickBooks data
- [ ] Account mappings reviewed/adjusted for actual QB account names

---

## Next Steps for Deployment

### Step 1: Add Environment Variables

Add to `/opt/shared-secrets/api-secrets.env`:

```bash
# QuickBooks Web Connector Authentication
QBWC_USERNAME=enersystems_qbr
QBWC_PASSWORD_HASH=<bcrypt hash>
```

Generate password hash:
```bash
python3 -c "import bcrypt; print(bcrypt.hashpw(b'YOUR_PASSWORD_HERE', bcrypt.gensalt()).decode())"
```

### Step 2: Run Database Migration

```bash
cd /opt/es-inventory-hub
source .venv/bin/activate
alembic upgrade head
```

This creates the 4 new tables and inserts 22 default account mappings.

### Step 3: Restart API Server

```bash
sudo systemctl restart es-inventory-hub-api
```

### Step 4: Create QWC File

Create `enersystems_qbr.qwc` for the Web Connector:

```xml
<?xml version="1.0"?>
<QBWCXML>
  <AppName>Enersystems QBR Sync</AppName>
  <AppID></AppID>
  <AppURL>https://db-api.enersystems.com:5400/api/qbwc</AppURL>
  <AppDescription>Syncs financial data from QuickBooks to QBR dashboard</AppDescription>
  <AppSupport>https://dashboards.enersystems.com</AppSupport>
  <UserName>enersystems_qbr</UserName>
  <OwnerID>{generate-unique-guid}</OwnerID>
  <FileID>{generate-unique-guid}</FileID>
  <QBType>QBFS</QBType>
  <Scheduler>
    <RunEveryNMinutes>60</RunEveryNMinutes>
  </Scheduler>
  <IsReadOnly>true</IsReadOnly>
</QBWCXML>
```

### Step 5: Configure Web Connector

1. Install QuickBooks Web Connector on Windows workstation (if not already installed)
2. Open Web Connector
3. Click "Add an Application"
4. Select the `.qwc` file
5. When prompted, enter the password (same one used to generate the hash)
6. Authorize the application in QuickBooks when prompted

### Step 6: Test the Sync

1. In Web Connector, select the application
2. Click "Update Selected"
3. Monitor progress in the Web Connector
4. Verify results:
   - Check `/api/qbwc/status` for sync status
   - Check `qbr_metrics_monthly` table for new QuickBooks data
   - Check `qbr_audit_log` for audit entries

### Step 7: Review Account Mappings

After the first sync, review the actual QuickBooks account names and adjust mappings:

```sql
-- View current mappings
SELECT * FROM qbwc_account_mappings ORDER BY qbr_metric_key;

-- View parsed data from last sync
SELECT parsed_data FROM qbwc_sync_history
WHERE sync_type = 'profit_loss'
ORDER BY created_at DESC LIMIT 1;
```

Use the REST API to add/modify mappings as needed:
- `GET /api/qbwc/mappings` - List all
- `POST /api/qbwc/mappings` - Add new
- `PUT /api/qbwc/mappings/{id}` - Update

---

## Security Considerations

- **Authentication:** bcrypt password hashing with configurable credentials
- **Session Management:** UUID-based tickets, 30-minute timeout
- **Transport:** HTTPS required (already configured)
- **Access Control:** Read-only access to QuickBooks (no writes)
- **Audit Trail:** All access attempts logged (success and failure)
- **Data Validation:** Input sanitization and error handling

---

## Troubleshooting

### Check Logs
```bash
# API server logs
sudo journalctl -u es-inventory-hub-api -f

# Look for QBWC entries
sudo journalctl -u es-inventory-hub-api | grep -i qbwc
```

### Check Sync Status
```bash
curl -s https://db-api.enersystems.com:5400/api/qbwc/status \
  -H "Cookie: session=<your-session-cookie>" | jq
```

### Check Audit Log
```sql
SELECT * FROM qbr_audit_log
WHERE action LIKE 'qbwc%'
ORDER BY timestamp DESC LIMIT 20;
```

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| "nvu" response | Invalid username or password | Check QBWC_USERNAME and QBWC_PASSWORD_HASH |
| "none" response | No periods to sync | All months already synced |
| Empty metrics | No account mappings match | Review QB account names and update mappings |
| Connection failed | Firewall or SSL | Ensure port 5400 is open, SSL cert is valid |

---

## References

- Original Specification: `https://dashboards.enersystems.com/prompts/quickbooks-web-connector.md`
- Setup Guide: `/opt/es-inventory-hub/prompts/quickbooks-web-connector-setup.md`
- QBWC Documentation: https://developer.intuit.com/app/developer/qbdesktop/docs/develop/web-connector

---

**Version**: v1.31.0
**Last Updated**: December 18, 2025 17:24 UTC
**Maintainer**: ES Inventory Hub Team

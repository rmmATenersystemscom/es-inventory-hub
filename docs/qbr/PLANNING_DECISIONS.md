# QBR Planning Decisions Summary

**Purpose**: This document captures all decisions made during the QBR planning phase.
**Date**: January 2025
**Status**: ✅ **COMPLETE**

---

## Quick Reference

This document answers "what did we decide?" for all major architectural and implementation decisions.

---

## 1. Architecture & Database Integration

**Decision**: Integrate QBR into existing database with `qbr_` table prefix

**Details**:
- ✅ Same database: `es_inventory_hub`
- ✅ Same schema: `public` (no separate QBR schema)
- ✅ Table naming: `qbr_` prefix (e.g., `qbr_metrics_monthly`, `qbr_smartnumbers`)
- ✅ Add vendors: ConnectWise (id=3), QuickBooks (id=4) to existing `vendor` table
- ✅ Foreign keys: QBR tables reference existing `vendor` table
- ✅ API integration: Add QBR endpoints to existing `api/api_server.py` as Flask blueprint

**Rationale**: Consistent with existing architecture, allows joins with inventory data, simpler maintenance

---

## 2. Organization Model

**Decision**: Single organization with ID=1

**Details**:
- ✅ Create `organization` table with single record: id=1, name="Enersystems, LLC"
- ✅ All QBR tables include `organization_id` foreign key (always = 1)
- ✅ Future-proofed for potential multi-org expansion

**Rationale**: Only one organization currently, but schema supports future expansion

---

## 3. Period Management

**Decision**: No `periods` table - use period strings directly

**Details**:
- ✅ No separate `periods` reference table
- ✅ Store period strings directly: "2025-01" (monthly), "2025-Q1" (quarterly)
- ✅ Calculate period boundaries in application code
- ✅ Timezone: Browser timezone via STD_TIMEZONE.md standards

**Rationale**: Simpler, period strings are self-describing, reduces unnecessary complexity

---

## 4. Data Collection Strategy

**Decision**: Pre-calculated and stored (Option A)

**Details**:
- ✅ Collectors run → aggregate data → store final metrics in `qbr_metrics_monthly`/`qbr_metrics_quarterly`
- ✅ API endpoints query stored values (not on-demand calculation)
- ✅ Metrics are historical snapshots, frozen once calculated
- ✅ ConnectWise: Query API → aggregate → store metrics only (no raw data staging)

**Rationale**: QBR is historical, performance, consistency, matches spreadsheet workflow

---

## 5. Data Collection Schedule

**Decision**: Daily at 10:30pm Central Time

**Details**:
- ✅ **Schedule**: Daily at 10:30pm America/Chicago timezone
- ✅ **Scope**: Current month (in-progress) + last 12 completed months = **13 months total**
- ✅ **Current month behavior**: Updated daily until month closes, then frozen
- ✅ **Collection approach**:
  - **Initially**: Collect all 13 months per run (for validation)
  - **Later**: Scale back to current month only (for efficiency)
- ✅ **Scheduled via**: systemd timer (not manual refresh endpoint)

**Rationale**: User wants to see month-in-progress metrics, daily updates show current performance

---

## 6. Historical Data

**Decision**: Backfill 2024 + 2025, support manual entry

**Details**:
- ✅ **Backfill depth**: January 2024 forward (2024 + 2025)
- ✅ **Validation**: Manual review by user
- ✅ **Incomplete data**: Manual data entry capability (see below)
- ✅ **Re-running**: Support re-running collection for specific months (bug fixes)

**Manual Data Entry Fields**:
```sql
- data_source: VARCHAR(20)  -- 'collected' or 'manual'
- collected_at: TIMESTAMP   -- when auto-collected
- manually_entered_by: VARCHAR(100)  -- user identifier
- notes: TEXT  -- explanation for manual entry
```

**Behavior**:
- ✅ Collector skips metrics marked as `data_source='manual'`
- ✅ Admin API endpoint: `POST /api/qbr/metrics/manual` for manual entry
- ✅ Can flag metrics for re-collection by changing `data_source` back to 'collected'

**Rationale**: Flexibility for incomplete/missing data, support corrections and bug fixes

---

## 7. ConnectWise Integration

**Decision**: Reuse existing REACTIVE_TICKETS_FILTERING.md logic

**Details**:
- ✅ Use existing filtering logic from `docs/qbr/shared/REACTIVE_TICKETS_FILTERING.md`
- ✅ Reactive tickets = "Help Desk" board + parent tickets only
- ✅ **Tickets Created**: Filter by `dateEntered` within period
- ✅ **Tickets Closed**: Filter by `closedDate` within period, closed statuses only
- ✅ **Time Spent**: Time entries by `dateEntered` within period, filtered to Help Desk tickets
- ✅ **Company scope**: All ConnectWise clients (no filtering)
- ✅ **Exclusions**: None - if it meets reactive criteria, it counts

**Rationale**: Working pattern already exists and validated in SMARTNUMBERS dashboard

---

## 8. QuickBooks Integration

**Decision**: Tabled for later implementation

**Details**:
- ⏸️ QuickBooks is on-premise (QuickBooks Desktop) on Windows
- ⏸️ API connection not yet established
- ⏸️ Revenue/expense metrics will be implemented in future phase
- ✅ Data model accommodates QuickBooks metrics (vendor_id=4)

**Rationale**: Infrastructure not ready, focus on ConnectWise + NinjaOne first

---

## 8b. Sales Activity Metrics

**Decision**: Tabled for later implementation

**Details**:
- ⏸️ Sales activities (meetings, phone calls, emails) not available in ConnectWise
- ⏸️ These metrics require manual entry or CRM integration
- ⏸️ Sales metrics will be implemented in future phase via manual data entry
- ✅ Data model accommodates sales metrics (manual entry support in `qbr_metrics_monthly`)

**Sales Metrics Tabled**:
- # of Telemarketing Dials
- # of First Time Appointments (FTA)
- # of Prospects to Hit PBR
- # of New Agreements
- New MRR
- Lost MRR

**Rationale**: Data source not available in ConnectWise API, focus on automated collection first

---

## 9. Data Model

**Decision**: Add indexes, constraints, timestamps, vendor tracking

**Details**:

**Tables**:
- `organization` - Single org record
- `qbr_metrics_monthly` - Monthly metrics
- `qbr_metrics_quarterly` - Quarterly metrics
- `qbr_smartnumbers` - Calculated KPIs
- `qbr_thresholds` - Alert thresholds
- `qbr_collection_log` - Collection execution tracking

**Indexes**:
- `qbr_metrics_monthly`: `(period, metric_name)`, `(organization_id, period)`, `(vendor_id, period)`
- `qbr_metrics_quarterly`: Similar to monthly
- `qbr_smartnumbers`: `(period, kpi_name)`, `(organization_id, period)`
- `qbr_thresholds`: `(metric_name)`

**Unique Constraints**:
- `qbr_metrics_monthly`: `(period, metric_name, organization_id, vendor_id)`
- `qbr_smartnumbers`: `(period, kpi_name, organization_id)`
- `qbr_thresholds`: `(metric_name, threshold_type, organization_id)`

**Timestamps**:
- `created_at` - When record was created
- `updated_at` - When record was last updated

**Vendor Tracking**:
- Include `vendor_id` in metrics tables to track data source
- Example: "Endpoints Managed" from Ninja (vendor_id=2), "Reactive Tickets" from ConnectWise (vendor_id=3)

**Rationale**: Performance, data integrity, auditability

---

## 10. API Endpoints

**Decision**: RESTful endpoints with standardized response format

**Endpoints**:
```
GET  /api/qbr/metrics/monthly?period=YYYY-MM&organization_id=1&vendor_id=N&metric_name=X
GET  /api/qbr/metrics/quarterly?period=YYYY-QN&organization_id=1
GET  /api/qbr/smartnumbers?period=YYYY-MM&organization_id=1
GET  /api/qbr/thresholds
POST /api/qbr/thresholds
POST /api/qbr/metrics/manual  (manual data entry)
```

**Response Format**:
```json
{
  "success": true,
  "data": {
    "period": "2025-01",
    "metrics": [...]
  }
}
```

**Error Format**:
```json
{
  "success": false,
  "error": {
    "code": "INVALID_PERIOD",
    "message": "Period format must be YYYY-MM",
    "status": 400
  }
}
```

**HTTP Status Codes**:
- 200: Success
- 400: Bad request (invalid parameters)
- 404: Period/data not found
- 500: Server error

**Pagination**: Not needed (small data volumes, <100 records per request)

**Removed Endpoints**:
- ❌ `POST /api/qbr/refresh` - Removed (use scheduled collection instead)
- ❌ `GET /api/qbr/refresh/status/<batch_id>` - Removed

**Rationale**: Simple, consistent, matches existing API patterns

---

## 11. Timezone Handling

**Decision**: Follow STD_TIMEZONE.md standards

**Details**:
- ✅ **Frontend**: Detect timezone via `Intl.DateTimeFormat().resolvedOptions().timeZone`
- ✅ **Backend**: Use existing `utils.date_handling` functions
- ✅ **Storage**: All timestamps in UTC
- ✅ **Display**: Convert to browser timezone
- ✅ **Scheduler**: America/Chicago for 10:30pm collection runs

**Rationale**: Consistent with existing dashboard standards, proven pattern

---

## 12. Error Handling

**Decision**: Retry with backoff, flag suspicious data, log to database

**Details**:

**API Failures**:
- ✅ Retry 3-5 times with exponential backoff
- ✅ After retries exhausted: Fail, log error, send alert
- ✅ Don't partially update - all or nothing per collection run

**Suspicious Data**:
- ✅ Zero tickets returned → Flag for manual review
- ✅ Zero endpoints → Flag for manual review
- ✅ Negative values → Error (reject data)
- ✅ Dramatic changes (>50% month-over-month) → Warning flag

**Error Logging**:
- ✅ Create separate `qbr_collection_log` table (not reuse job_batches)
- ✅ Track: timestamp, period, vendor, success/failure, error message, duration

**Notifications**:
- ✅ Dashboard indicator (show collection status/errors)
- ✅ Log file (`/var/log/qbr-collector.log` or similar)
- ❌ No email/Slack initially (can add later)

**Rationale**: Resilient to transient failures, data quality safeguards, visibility into issues

---

## 13. Testing & Validation

**Decision**: Separate test database with comprehensive validation before production

**Test Database**:
- ✅ Create separate database: `es_inventory_hub_test`
- ✅ Copy full production table structures
- ✅ Test collector against real ConnectWise API
- ✅ Zero risk to production database during development

**Validation Criteria** (before production deployment):
- ✅ All 2024-2025 historical months validated
- ✅ Current month daily updates tested for **9 consecutive days**
- ✅ Manual data entry tested
- ✅ Error handling tested (simulate API failures)
- ✅ All SmartNumbers calculations verified
- ❌ NOT required: Match January 2024 to Excel (Excel may be outdated)

**Production Deployment Approach**:
- ✅ Run initial backfill **manually** (not automatic)
- ✅ Review results before enabling daily schedule
- ✅ Collector starts **disabled**, enable after approval

**Rationale**: Safety, confidence in accuracy, no production impact during development

---

## 14. Documentation Requirements

**Decision**: Comprehensive calculation documentation for offline review

**Documents to Create**:
- ✅ `PLANNING_DECISIONS.md` - This document
- ✅ `IMPLEMENTATION_GUIDE.md` - Comprehensive implementation plan
- ✅ `CALCULATION_REFERENCE.md` - All formulas and calculations

**Calculation Documentation Must Include**:
- Every metric's calculation formula
- Source data/tables for each calculation
- Example calculations with sample data
- SmartNumbers formulas showing which metrics they use
- SQL queries used for aggregations

**Rationale**: User needs offline reference to validate calculations, audit results

---

## 15. Metrics Defined

**Decision**: Use metrics from QBR2025_structured.md

**Source**: `/opt/es-inventory-hub/docs/qbr/QBR2025_structured.md`

**Metrics Count**:
- **48 Monthly Input Metrics** across 6 categories
- **18 SmartNumbers/KPIs** across 5 categories

**Categories**:
- Operations (tickets, endpoints, time)
- Revenue (MRR, NRR, ORR, product sales)
- Expenses (employee costs, COGS, other)
- Profit (net profit dollars)
- General Information (employee counts, agreements)
- Sales (new MRR, lost MRR, activities)

**Data Sources**:
- **NinjaOne**: Endpoints Managed, Seats Managed
- **ConnectWise**: All ticket metrics, time entries, sales activities
- **QuickBooks**: All revenue/expense metrics (future)

**Rationale**: Existing spreadsheet is validated and in use, defines all required metrics

---

## 16. Authentication & Authorization

**Decision**: Microsoft 365 OAuth Single Sign-On (SSO) with HTTP-only cookie sessions

**Implementation**: Backend-first approach with secure session management

**Details**:

### Authentication Method
- ✅ **OAuth 2.0** via Microsoft 365 / Azure Active Directory
- ✅ **Provider**: Microsoft Identity Platform
- ✅ **Flow**: Authorization Code Flow (most secure for web apps)
- ✅ **Library**: MSAL (Microsoft Authentication Library) for Python

### Authorization Model
- ✅ **Whitelist-based**: Hardcoded list of authorized email addresses
- ✅ **Authorized Users** (2 users):
  - rmmiller@enersystems.com
  - jmmiller@enersystems.com
- ✅ **Validation**: Email checked against whitelist on login and every API request
- ✅ **Scope**: Single tenant (Enersystems Microsoft 365 tenant only)

### Session Management
- ✅ **Storage**: HTTP-only secure cookies (most secure option)
- ✅ **Expiration**: 8 hours (configurable via environment variable)
- ✅ **Security Features**:
  - HTTP-only flag (JavaScript cannot access)
  - Secure flag (HTTPS only)
  - SameSite=Lax (CSRF protection)
  - Server-side session validation
- ✅ **Session Store**: Filesystem initially, Redis for production scale

### Security Architecture

**Transport Security**:
- ✅ HTTPS required (TLS 1.2+)
- ✅ Valid SSL certificate
- ✅ HSTS headers enabled

**CORS Configuration**:
- ✅ Allowed origins: `https://dashboards.enersystems.com`
- ✅ Credentials support enabled (required for cookies)
- ✅ Localhost allowed for development (`http://localhost:3000`, `http://localhost:8080`)

**Secrets Management**:
- ✅ Azure credentials stored in `/opt/shared-secrets/api-secrets.env`
- ✅ File permissions: 600 (owner read/write only)
- ✅ Never committed to git
- ✅ Environment variables loaded at runtime

### Authentication Flow

1. User visits dashboard → Redirected to `/api/auth/microsoft/login`
2. Backend redirects to Microsoft login page
3. User authenticates with Microsoft 365 credentials
4. User consents to permissions (first time only: "User.Read")
5. Microsoft redirects back to `/api/auth/microsoft/callback` with auth code
6. Backend exchanges code for access token
7. Backend calls Microsoft Graph API to get user email
8. Backend validates email is in authorized users list
9. Backend creates secure session cookie (8-hour expiration)
10. Backend redirects to frontend dashboard
11. User is logged in - all subsequent API requests include session cookie

### API Endpoint Protection

All QBR endpoints protected with `@require_auth` decorator:
```python
@app.route('/api/qbr/smartnumbers')
@require_auth
def get_smartnumbers():
    current_user = session.get('user_email')
    # ... endpoint logic
```

**Protected Endpoints**:
- `GET /api/qbr/metrics/monthly` ✅
- `GET /api/qbr/metrics/quarterly` ✅
- `GET /api/qbr/smartnumbers` ✅
- `GET /api/qbr/thresholds` ✅
- `POST /api/qbr/metrics/manual` ✅
- `POST /api/qbr/thresholds` ✅

**Public Endpoints** (no auth required):
- `GET /api/auth/microsoft/login` - Initiate login
- `GET /api/auth/microsoft/callback` - OAuth callback
- `POST /api/auth/logout` - End session
- `GET /api/auth/status` - Check auth status (returns 401 if not logged in)

### Azure AD Configuration

**App Registration Requirements**:
- Application (client) ID: From Azure Portal
- Directory (tenant) ID: From Azure Portal
- Client Secret: Generated in Azure Portal (24-month expiration)
- Redirect URI: `https://db-api.enersystems.com:5400/api/auth/microsoft/callback`
- Permissions: `User.Read` (basic profile - email, name)
- Supported account types: Single tenant only

### Error Handling

**Unauthorized User Attempts**:
- User authenticates successfully with Microsoft
- Backend rejects at callback if email not in whitelist
- Returns 403 error: "Access denied - Your account is not authorized"
- Session not created

**Session Expiration**:
- After 8 hours, session expires
- Next API request returns 401: "Authentication required"
- Frontend redirects to login page
- User must re-authenticate

**Failed Authentication**:
- OAuth errors logged
- User sees friendly error message
- No sensitive information exposed in errors

### Logging and Monitoring

**Authentication Events Logged**:
- ✅ Login attempts (success and failure)
- ✅ Unauthorized access attempts
- ✅ Session creation and expiration
- ✅ User email (but never passwords or tokens)

**Log Location**: `/var/log/es-inventory-api/auth.log`

**Metrics Tracked**:
- Number of active sessions
- Failed login attempts
- Unauthorized access attempts
- Average session duration

### Adding Users

**To add more authorized users**:
1. Edit `/opt/shared-secrets/api-secrets.env`
2. Update `QBR_AUTHORIZED_USERS` (comma-separated)
3. Restart API server: `sudo systemctl restart es-inventory-api.service`
4. No Azure AD changes needed (any user in tenant can authenticate, but only whitelisted users are authorized)

**Example**:
```bash
QBR_AUTHORIZED_USERS=rmmiller@enersystems.com,jmmiller@enersystems.com,newuser@enersystems.com
```

### Frontend Integration

**Frontend Responsibilities**:
- Display "Login with Microsoft" button
- Redirect to `/api/auth/microsoft/login` when clicked
- Session cookie automatically included in API requests (browser handles this)
- Handle 401 responses by redirecting to login
- Provide logout button calling `/api/auth/logout`

**What Frontend Does NOT Handle**:
- Password management (Microsoft handles)
- Token storage (backend session cookie)
- Token validation (backend handles)
- OAuth flow (backend handles)

### Future Enhancements

**Phase 2 Possibilities**:
- ⏸️ Role-based access control (admin vs viewer)
- ⏸️ Multi-factor authentication (MFA) - can enable in Microsoft 365
- ⏸️ Session audit logging to database
- ⏸️ Rate limiting on login endpoint
- ⏸️ Brute force protection
- ⏸️ IP-based access restrictions

### Configuration Files

**Backend Environment** (`/opt/shared-secrets/api-secrets.env`):
```bash
AZURE_TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
AZURE_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
AZURE_CLIENT_SECRET=AbC123~xxxxxxxxxxxxxxxxxxxxx
SESSION_SECRET_KEY=random-64-character-hex-string
SESSION_LIFETIME_HOURS=8
QBR_AUTHORIZED_USERS=rmmiller@enersystems.com,jmmiller@enersystems.com
API_BASE_URL=https://db-api.enersystems.com:5400
FRONTEND_URL=https://dashboards.enersystems.com/qbr
```

**Documentation**:
- Setup Guide: `docs/qbr/AZURE_AD_SETUP_GUIDE.md`
- Implementation Guide: `docs/qbr/AUTHENTICATION_IMPLEMENTATION.md`
- Frontend Integration: `docs/qbr/FRONTEND_DEVELOPMENT_BRIEF.md`

**Rationale**:
- Microsoft 365 SSO provides best security with zero password management
- HTTP-only cookies protect against XSS attacks
- Whitelist approach is simple and sufficient for 2-user system
- Backend-first ensures API is always secure regardless of frontend state
- Easily scales to more users by updating configuration
- Professional, enterprise-grade authentication for minimal implementation effort

---

## Summary

All major planning decisions have been documented. See `IMPLEMENTATION_GUIDE.md` for the detailed implementation plan and `CALCULATION_REFERENCE.md` for metric formulas.

---

---

**Version**: v1.23.0
**Last Updated**: November 19, 2025 13:36 UTC
**Maintainer**: ES Inventory Hub Team
**Status**: Complete
**Next Step**: Implementation (see IMPLEMENTATION_GUIDE.md)

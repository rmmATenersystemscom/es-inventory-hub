# QBR Web Dashboard - Frontend Development Brief

**Project**: Quarterly Business Review (QBR) Web Dashboard
**Backend API**: Fully implemented and operational
**Target User**: MSP business owners and managers
**Priority**: High-level KPI visualization for quarterly business reviews

---

## Executive Summary

Build a modern web dashboard to visualize QBR (Quarterly Business Review) metrics and SmartNumbers (KPIs) for an MSP (Managed Service Provider). The backend REST API is complete with 23 months of historical data. Your task is to create an intuitive, professional dashboard that helps business owners quickly understand their operational, financial, and sales performance.

---

## Project Context

**What is QBR?**
QBR (Quarterly Business Review) is a systematic way for MSPs to track and improve their business performance using 18 key performance indicators (SmartNumbers) across 5 categories:
1. **Operations** - Service delivery efficiency
2. **Profit** - Financial health
3. **Revenue** - Revenue composition and sources
4. **Leverage** - Employee productivity and efficiency
5. **Sales** - Growth and customer acquisition

**Current State:**
- ✅ Backend API: Complete and tested (6 endpoints)
- ✅ Data Collection: Automated daily at 10:30 PM CT
- ✅ Historical Data: 23 months (Jan 2024 - Nov 2025)
- ✅ SmartNumbers Calculator: All 18 KPIs calculating correctly
- ❌ Frontend Dashboard: **Needs to be built** (your task)

---

## Technical Specifications

### Backend API

**Base URL**: `https://db-api.enersystems.com:5400`
**Format**: REST API, JSON responses
**Authentication**: Microsoft 365 OAuth SSO with HTTP-only session cookies

### Authentication

**Method**: Microsoft 365 Single Sign-On (SSO)
- Users click "Login with Microsoft" button
- Backend handles OAuth flow with Azure AD
- Session cookie automatically managed by browser
- No password or token management needed in frontend

**Login Flow**:
1. User clicks "Login with Microsoft" → Redirect to: `https://db-api.enersystems.com:5400/api/auth/microsoft/login`
2. Backend redirects to Microsoft login page
3. User logs in with Microsoft 365 credentials
4. Microsoft redirects back to backend with authorization code
5. Backend validates user and creates session cookie
6. Backend redirects to: `https://dashboards.enersystems.com/qbr`
7. Frontend is now authenticated - all API calls automatically include session cookie

**API Requests**:
- Session cookie (`qbr_session`) automatically included by browser
- No Authorization header needed
- If session expired (8 hours), API returns 401
- Frontend should redirect to login on 401 response

**Authentication Endpoints**:
```
GET  /api/auth/microsoft/login  - Initiate login (no auth required)
GET  /api/auth/status           - Check if logged in
POST /api/auth/logout           - End session
```

**Authorized Users** (hardcoded in backend):
- rmmiller@enersystems.com
- jmmiller@enersystems.com

### Available Endpoints

#### 1. GET /api/qbr/metrics/monthly
Get raw metrics for a specific month.

**Query Parameters:**
- `period` (optional): YYYY-MM format (e.g., "2025-11"). Defaults to latest.
- `organization_id` (optional): Organization ID (default: 1)
- `vendor_id` (optional): Filter by vendor (2=NinjaOne, 3=ConnectWise)
- `metric_name` (optional): Filter by specific metric

**Example Request:**
```bash
GET /api/qbr/metrics/monthly?period=2025-11
```

**Example Response:**
```json
{
  "success": true,
  "data": {
    "period": "2025-11",
    "organization_id": 1,
    "metrics": [
      {
        "metric_name": "endpoints_managed",
        "metric_value": 574.0,
        "vendor_id": 2,
        "data_source": "collected",
        "notes": "Billable devices only",
        "updated_at": "2025-11-15T00:14:03Z"
      },
      {
        "metric_name": "reactive_tickets_created",
        "metric_value": 142.0,
        "vendor_id": 3,
        "data_source": "collected",
        "notes": "Help Desk board, parent tickets only",
        "updated_at": "2025-11-15T01:12:39Z"
      }
    ]
  }
}
```

#### 2. GET /api/qbr/metrics/quarterly
Get aggregated quarterly metrics (sums and averages across 3 months).

**Query Parameters:**
- `period` (required for specific quarter): YYYY-Q1/Q2/Q3/Q4 format
- `organization_id` (optional): Organization ID (default: 1)

**Example Request:**
```bash
GET /api/qbr/metrics/quarterly?period=2025-Q4
```

**Example Response:**
```json
{
  "success": true,
  "data": {
    "period": "2025-Q4",
    "organization_id": 1,
    "monthly_periods": ["2025-10", "2025-11", "2025-12"],
    "metrics": {
      "reactive_tickets_created": 426.0,
      "reactive_tickets_closed": 408.0,
      "reactive_time_spent": 236.25,
      "endpoints_managed": 574.0,
      "seats_managed": 519.0,
      "employees": 8.5,
      "technical_employees": 5.5
    }
  }
}
```

#### 3. GET /api/qbr/smartnumbers ⭐ PRIMARY ENDPOINT
Calculate and return all 18 SmartNumbers (KPIs) for a quarter.

**Query Parameters:**
- `period` (REQUIRED): Quarterly period (e.g., "2025-Q4")
- `organization_id` (optional): Organization ID (default: 1)

**Example Request:**
```bash
GET /api/qbr/smartnumbers?period=2025-Q4
```

**Example Response:**
```json
{
  "success": true,
  "data": {
    "period": "2025-Q4",
    "organization_id": 1,
    "monthly_periods": ["2025-10", "2025-11", "2025-12"],
    "smartnumbers": {
      "tickets_per_tech_per_month": 24.73,
      "total_close_pct": 0.9578,
      "tickets_per_endpoint_per_month": 0.247,
      "rhem": 0.137,
      "avg_resolution_time": 0.579,
      "reactive_service_pct": 0.086,
      "net_profit_pct": 0.23,
      "revenue_from_services_pct": 0.96,
      "services_from_mrr_pct": 0.88,
      "annual_service_rev_per_employee": 58941.18,
      "annual_service_rev_per_tech": 91090.91,
      "avg_aisp": 70.33,
      "avg_mrr_per_agreement": 816.67,
      "new_mrr_added": 5500.0,
      "lost_mrr": 1200.0,
      "net_mrr_gain": 4300.0,
      "dials_per_appointment": 20.83,
      "sales_call_close_pct": 0.25
    }
  }
}
```

**Note**: SmartNumbers return `null` if data is missing. Display "N/A" or hide those metrics in the UI.

#### 4. GET /api/qbr/thresholds
Get performance thresholds (green/yellow/red zones) for SmartNumbers.

**Query Parameters:**
- `organization_id` (optional): Organization ID (default: 1)

**Example Response:**
```json
{
  "success": true,
  "data": {
    "organization_id": 1,
    "thresholds": [
      {
        "metric_name": "tickets_per_tech_per_month",
        "green_min": 50.0,
        "green_max": 70.0,
        "yellow_min": 40.0,
        "yellow_max": 80.0,
        "red_threshold": 90.0,
        "notes": "Target range based on industry standards"
      }
    ]
  }
}
```

#### 5. POST /api/qbr/metrics/manual
Add manual metrics (revenue, employees, sales data).

**Request Body:**
```json
{
  "period": "2025-11",
  "organization_id": 1,
  "metrics": [
    {
      "metric_name": "employees",
      "metric_value": 8.5,
      "notes": "Total headcount including part-time"
    },
    {
      "metric_name": "mrr",
      "metric_value": 110250.00,
      "notes": "From QuickBooks"
    }
  ]
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "period": "2025-11",
    "organization_id": 1,
    "updated_count": 2
  }
}
```

#### 6. POST /api/qbr/thresholds
Update performance thresholds.

---

## SmartNumbers (KPIs) Reference

### Operations Category (6 KPIs)

| SmartNumber | Description | Format | Good Range | Notes |
|-------------|-------------|--------|------------|-------|
| `tickets_per_tech_per_month` | Average tickets closed per tech per month | Decimal | 40-60 | Higher = more productive, but >70 may indicate burnout |
| `total_close_pct` | Percentage of tickets closed vs created | Percentage (0-1) | 0.95-1.05 | Should be close to 100% |
| `tickets_per_endpoint_per_month` | New tickets per managed endpoint | Decimal | 0.20-0.30 | Lower is better (fewer issues) |
| `rhem` | Reactive Hours per Endpoint per Month | Decimal | 0.10-0.20 | Lower is better (more proactive) |
| `avg_resolution_time` | Average hours to resolve ticket | Hours (decimal) | 0.5-1.0 | Lower is better |
| `reactive_service_pct` | % of tech time on reactive work | Percentage (0-1) | 0.08-0.15 | Lower is better (more proactive) |

### Profit Category (1 KPI)

| SmartNumber | Description | Format | Good Range | Notes |
|-------------|-------------|--------|------------|-------|
| `net_profit_pct` | Net profit as % of revenue | Percentage (0-1) | 0.20-0.30 | Industry target: 20-30% |

### Revenue Category (2 KPIs)

| SmartNumber | Description | Format | Good Range | Notes |
|-------------|-------------|--------|------------|-------|
| `revenue_from_services_pct` | Services revenue vs total | Percentage (0-1) | 0.70-0.90 | Higher = more stable recurring |
| `services_from_mrr_pct` | Services from MRR vs NRR | Percentage (0-1) | 0.80-0.95 | Higher = more predictable |

### Leverage Category (4 KPIs)

| SmartNumber | Description | Format | Good Range | Notes |
|-------------|-------------|--------|------------|-------|
| `annual_service_rev_per_employee` | Annualized service revenue / employee | Currency | $50k-$80k | Higher = better leverage |
| `annual_service_rev_per_tech` | Annualized service revenue / tech | Currency | $80k-$120k | Measures tech productivity |
| `avg_aisp` | Average Income per Seat/Position | Currency | $60-$100 | Monthly MRR per managed seat |
| `avg_mrr_per_agreement` | Average MRR per agreement | Currency | $500-$1500 | Larger deals = better |

### Sales Category (5 KPIs)

| SmartNumber | Description | Format | Good Range | Notes |
|-------------|-------------|--------|------------|-------|
| `new_mrr_added` | New MRR added in quarter | Currency | Positive | Growth indicator |
| `lost_mrr` | MRR lost to churn | Currency | Low as possible | Churn indicator |
| `net_mrr_gain` | Net MRR change (new - lost) | Currency | Positive | Overall growth |
| `dials_per_appointment` | Telemarketing dials per appointment | Decimal | 10-25 | Lower = better conversion |
| `sales_call_close_pct` | Sales call close percentage | Percentage (0-1) | 0.20-0.40 | Higher = better sales process |

---

## User Interface Requirements

### Login Page (New)

**Purpose**: Authentication entry point for the dashboard

**Must Display:**
1. **Branding**
   - "QBR Dashboard - Enersystems, LLC" title
   - Company logo (optional)
   - Clean, professional design

2. **Login Button**
   - "Login with Microsoft" or "Sign in with Microsoft 365"
   - Microsoft logo/icon
   - Clear call-to-action

3. **Information** (optional)
   - Brief description: "Quarterly Business Review Dashboard"
   - "For authorized users only"

**User Flow:**
```
┌─────────────────────────────────────┐
│        QBR Dashboard                 │
│        Enersystems, LLC              │
│                                      │
│   ┌───────────────────────────────┐ │
│   │  📊 Login with Microsoft       │ │
│   └───────────────────────────────┘ │
│                                      │
│   Quarterly Business Review Dashboard│
│   For authorized users only          │
└─────────────────────────────────────┘
                  ↓
      Click button → Redirect to Microsoft login
                  ↓
      User logs in with Microsoft 365
                  ↓
      Redirect back to dashboard (authenticated)
```

**Implementation Example (React)**:
```jsx
function LoginPage() {
  const handleLogin = () => {
    // Redirect to backend auth endpoint
    window.location.href = 'https://db-api.enersystems.com:5400/api/auth/microsoft/login';
  };

  return (
    <div className="login-container">
      <h1>QBR Dashboard</h1>
      <h2>Enersystems, LLC</h2>

      <button onClick={handleLogin} className="microsoft-login-button">
        <img src="/microsoft-logo.svg" alt="Microsoft" />
        Login with Microsoft
      </button>

      <p>Quarterly Business Review Dashboard</p>
      <p className="muted">For authorized users only</p>
    </div>
  );
}
```

**Routing**:
- Path: `/login` or `/` (if not authenticated)
- After successful login, backend redirects to: `/qbr` or `/dashboard`

**Session Check on Load**:
```javascript
// On app mount, check if user is authenticated
useEffect(() => {
  fetch('https://db-api.enersystems.com:5400/api/auth/status', {
    credentials: 'include'  // Important: include cookies
  })
    .then(res => res.json())
    .then(data => {
      if (data.authenticated) {
        // User is logged in, show dashboard
        navigate('/dashboard');
      } else {
        // Not logged in, show login page
        navigate('/login');
      }
    });
}, []);
```

**Error Handling**:
- If backend returns error after Microsoft login (e.g., unauthorized user)
- Show friendly message: "Access denied. Your account is not authorized."
- Provide support contact information

---

### Primary View: Dashboard

**Purpose**: At-a-glance view of current quarter performance

**Must Display:**
1. **Header Section**
   - Current quarter (e.g., "Q4 2025")
   - Quarter selector dropdown (Q1-Q4 for years 2024-2025)
   - Organization name ("Enersystems, LLC")
   - Last updated timestamp
   - **User info** (from `/api/auth/status`): Logged in as "Ryan Miller" or user email
   - **Logout button**: Calls `/api/auth/logout` endpoint

2. **SmartNumbers Grid**
   - Display all 18 SmartNumbers organized by category
   - Color-coded indicators (green/yellow/red) based on thresholds
   - Show actual value with proper formatting
   - Show trend arrow (up/down) compared to previous quarter
   - Ability to click for drill-down details

3. **Category Sections** (5 sections):
   - **Operations** - 6 metrics
   - **Profit** - 1 metric
   - **Revenue** - 2 metrics
   - **Leverage** - 4 metrics
   - **Sales** - 5 metrics

**Example Layout (Wireframe):**
```
┌────────────────────────────────────────────────────────┐
│  QBR Dashboard - Enersystems, LLC       Q4 2025 ▼     │
│  Last Updated: Nov 15, 2025 10:30 PM                   │
└────────────────────────────────────────────────────────┘

┌─── OPERATIONS ──────────────────────────────────────────┐
│                                                          │
│  ✓ Tickets/Tech/Month     ✓ Close Rate   ⚠ RHEM        │
│     24.7                      95.8%          0.14       │
│     ↑ +2.3                   ↓ -1.2%       ↑ +0.02     │
│                                                          │
│  ✓ Tickets/Endpoint    ✓ Avg Resolution  ✓ Reactive%   │
│     0.25                    0.58 hrs         8.6%       │
│     ↓ -0.03                ↓ -0.1          ↓ -1.2%     │
└──────────────────────────────────────────────────────────┘

┌─── PROFIT ──────────────────────────────────────────────┐
│  ✓ Net Profit %                                          │
│     23.2%                                                │
│     ↑ +1.5%                                             │
└──────────────────────────────────────────────────────────┘

[... Similar for Revenue, Leverage, Sales ...]
```

### Secondary View: Trends

**Purpose**: Historical trend analysis

**Must Display:**
- Line charts for each SmartNumber over time
- Quarter-over-quarter comparison
- Year-over-year comparison
- Ability to select date ranges

### Tertiary View: Raw Data

**Purpose**: Detailed metrics explorer

**Must Display:**
- Monthly metrics table with filters
- Export to CSV/Excel functionality
- Ability to add manual metrics (simple form)

---

## Design Principles

1. **Professional & Clean**: MSP business owners expect professional presentation
2. **Mobile Responsive**: Must work on tablets (common in boardrooms)
3. **Color Coding**: Use colors intuitively (green=good, yellow=caution, red=concern)
4. **Data Visualization**: Charts should be simple and easy to understand
5. **Performance**: Dashboard should load quickly (<2 seconds)

---

## Recommended Technology Stack

**Suggested (but you choose):**
- **Frontend Framework**: React, Vue, or Next.js
- **UI Components**: Material-UI, Chakra UI, or Tailwind CSS
- **Charts**: Chart.js, Recharts, or ApexCharts
- **State Management**: React Context, Redux, or Zustand
- **HTTP Client**: Axios or Fetch API

**Must Support:**
- Modern browsers (Chrome, Firefox, Safari, Edge)
- Responsive design (desktop, tablet)
- Dark mode (nice to have)

---

## Sample API Responses

### Sample SmartNumbers Response (Q4 2025)

```json
{
  "success": true,
  "data": {
    "period": "2025-Q4",
    "organization_id": 1,
    "monthly_periods": ["2025-10", "2025-11", "2025-12"],
    "smartnumbers": {
      "tickets_per_tech_per_month": 29.70,
      "total_close_pct": 0.9820,
      "tickets_per_endpoint_per_month": 0.2878,
      "rhem": 0.1398,
      "avg_resolution_time": 0.4946,
      "reactive_service_pct": 0.0880,
      "net_profit_pct": 0.2322,
      "revenue_from_services_pct": 0.9616,
      "services_from_mrr_pct": 0.8802,
      "annual_service_rev_per_employee": 58941.1800,
      "annual_service_rev_per_tech": 91090.9100,
      "avg_aisp": 70.3300,
      "avg_mrr_per_agreement": 816.6700,
      "new_mrr_added": 5500.0000,
      "lost_mrr": 1200.0000,
      "net_mrr_gain": 4300.0000,
      "dials_per_appointment": 20.8300,
      "sales_call_close_pct": 0.2500
    }
  }
}
```

### Sample Quarterly Metrics Response

```json
{
  "success": true,
  "data": {
    "period": "2025-Q4",
    "organization_id": 1,
    "monthly_periods": ["2025-10", "2025-11", "2025-12"],
    "metrics": {
      "reactive_tickets_created": 641,
      "reactive_tickets_closed": 626,
      "reactive_time_spent": 406.11,
      "endpoints_managed": 574,
      "seats_managed": 524,
      "employees": 8.5,
      "technical_employees": 5.5,
      "mrr": 110250.00,
      "total_revenue": 130250.00,
      "net_profit": 30250.00
    }
  }
}
```

---

## User Stories

### Story 1: View Current Quarter Performance
**As a** business owner
**I want to** see all my Q4 2025 SmartNumbers at a glance
**So that** I can quickly understand if my business is healthy

**Acceptance Criteria:**
- Dashboard loads with Q4 2025 selected by default
- All 18 SmartNumbers are displayed with color coding
- Metrics with NULL values show "N/A" or are hidden
- Page loads in <2 seconds

### Story 2: Compare Quarter Over Quarter
**As a** business owner
**I want to** see how Q4 2025 compares to Q3 2025
**So that** I can track improvement or decline

**Acceptance Criteria:**
- Trend arrows show increase/decrease
- Percentage or absolute change is displayed
- Can click to see detailed trend chart

### Story 3: Drill Down into Metrics
**As a** operations manager
**I want to** click on "Tickets per Tech" to see monthly breakdown
**So that** I can identify which month had issues

**Acceptance Criteria:**
- Clicking a SmartNumber shows detail view
- Detail view shows monthly data for the quarter
- Can see raw metrics that contributed to calculation

### Story 4: Add Manual Data
**As a** finance manager
**I want to** add revenue and expense data for November
**So that** profit metrics calculate correctly

**Acceptance Criteria:**
- Simple form to enter manual metrics
- Form validates data types and ranges
- Shows confirmation of successful save
- Dashboard updates automatically

### Story 5: View Historical Trends
**As a** business owner
**I want to** see "Net Profit %" trended over last 4 quarters
**So that** I can see if profitability is improving

**Acceptance Criteria:**
- Line chart shows trend over time
- Can select different SmartNumbers to trend
- Can change date range (quarter, year, all-time)

---

## Implementation Priorities

### Phase 1: MVP (Build This First)
1. ✅ Connect to SmartNumbers API endpoint
2. ✅ Display all 18 SmartNumbers for selected quarter
3. ✅ Quarter selector dropdown (Q1-Q4 for 2024-2025)
4. ✅ Color coding based on good/bad values (hardcoded ranges OK for MVP)
5. ✅ Responsive layout (desktop + tablet)
6. ✅ Error handling for missing data (show "N/A")

### Phase 2: Enhanced UX
1. ⬜ Trend arrows (compare to previous quarter)
2. ⬜ Threshold-based color coding (use thresholds API)
3. ⬜ Click to drill-down into metric details
4. ⬜ Loading states and smooth transitions
5. ⬜ Dark mode support

### Phase 3: Advanced Features
1. ⬜ Trend charts (line graphs over time)
2. ⬜ Manual data entry form
3. ⬜ Export to PDF/Excel
4. ⬜ Email reports
5. ⬜ Multi-organization support

---

## Data Formatting Guidelines

### Percentages
- Store as decimal (0.2322)
- Display as percentage: "23.2%" or "23.22%"
- Use 1-2 decimal places

### Currency
- Store as decimal (58941.18)
- Display with currency symbol: "$58,941" or "$58,941.18"
- Use comma separators

### Decimals
- Store as-is (24.73)
- Display with 1-2 decimal places: "24.7" or "24.73"
- Round consistently

### Hours
- Store as decimal hours (0.4946)
- Display as hours with unit: "0.49 hrs" or "29.6 min"

### Null Values
- API returns `null` for missing data
- Display as "N/A" or hide the metric
- Don't show "0" or "null"

---

## Error Handling

### API Errors
```json
{
  "success": false,
  "error": {
    "code": "NO_DATA",
    "message": "No data available for period 2025-Q4",
    "status": 404
  }
}
```

**Handle by:**
- Show friendly message: "No data available for this quarter"
- Suggest action: "Try selecting a different quarter"
- Don't crash the UI

### Common Error Codes
- `INVALID_PERIOD` - Invalid quarter format
- `MISSING_PERIOD` - Period parameter required
- `NO_DATA` - No metrics found for period
- `SERVER_ERROR` - Backend error (500)

---

## Testing Checklist

### Functional Testing
- [ ] Can select different quarters
- [ ] All 18 SmartNumbers display correctly
- [ ] Color coding works (green/yellow/red)
- [ ] NULL values show as "N/A"
- [ ] Loading states work
- [ ] Error messages are helpful

### UI/UX Testing
- [ ] Responsive on desktop (1920x1080)
- [ ] Responsive on tablet (1024x768)
- [ ] Readable on mobile (375x667) - bonus
- [ ] All text is readable
- [ ] Colors have good contrast
- [ ] Animations are smooth

### Performance Testing
- [ ] Dashboard loads in <2 seconds
- [ ] API calls are optimized (batch if possible)
- [ ] No memory leaks
- [ ] Works with slow network (3G simulation)

---

## Getting Started

### Important: Network Requirements ⚠️

**This system is internal-only and requires network access to Enersystems infrastructure.**

#### Network Access Requirements

- **Location**: Must be on Enersystems LAN (192.168.5.0/24) or connected via VPN
- **Backend API**: https://db-api.enersystems.com:5400 (resolves to 192.168.99.246 internally)
- **Frontend Deployment**: https://dashboards.enersystems.com/qbr (will be on 192.168.99.245)
- **Internet Access**: Required for Microsoft OAuth login (login.microsoftonline.com, graph.microsoft.com)

#### Development Options

**Option A: Develop on LAN** (Recommended for full testing)
- Connect to company network via Ethernet/WiFi or VPN
- Can test full authentication flow with real Microsoft login
- Login credentials: rmmiller@enersystems.com or jmmiller@enersystems.com
- Full end-to-end testing capability

**Option B: Develop with Mock Data** (If remote without VPN)
- Build UI components and layout without authentication
- Use mock JSON data for SmartNumbers (copy from examples below)
- Test authentication later when deployed to production server
- Deploy to 192.168.99.245 for integration testing

#### Testing Authentication Flow

**Manual Browser Test:**
1. Ensure you're on Enersystems LAN or VPN
2. Open browser and navigate to: `https://db-api.enersystems.com:5400/api/auth/microsoft/login`
3. You'll be redirected to Microsoft 365 login
4. Log in with rmmiller@enersystems.com or jmmiller@enersystems.com
5. After success, you'll be redirected to: `https://dashboards.enersystems.com/qbr`
6. Verify session: `https://db-api.enersystems.com:5400/api/auth/status`

**Expected Response (authenticated)**:
```json
{
  "authenticated": true,
  "user_email": "rmmiller@enersystems.com",
  "user_name": "Ryan Miller",
  "login_time": "2025-11-17T20:05:18"
}
```

**Note on curl Testing**:
```bash
# These will return 401 - cookies are HTTP-only and can't be included in curl
curl -k https://db-api.enersystems.com:5400/api/auth/status
curl -k https://db-api.enersystems.com:5400/api/qbr/smartnumbers?period=2025-Q4

# ⚠️ curl testing won't work for authenticated endpoints
# You MUST use a real browser to test authentication
```

Session cookies are HTTP-only (JavaScript can't access them) for security. This means:
- ✅ Browser automatically includes cookies in requests
- ✅ Works perfectly with fetch/axios using `credentials: 'include'`
- ❌ curl cannot test authenticated endpoints (no way to send HTTP-only cookies)
- ❌ Postman/Insomnia also cannot easily test (need to extract cookies from browser)

**Best Testing Approach**: Use browser DevTools Network tab to inspect API calls.

---

### Step 1: Test the API
```bash
# Test SmartNumbers endpoint
curl "https://db-api.enersystems.com:5400/api/qbr/smartnumbers?period=2025-Q4"

# Test quarterly metrics
curl "https://db-api.enersystems.com:5400/api/qbr/metrics/quarterly?period=2025-Q4"

# Test thresholds
curl "https://db-api.enersystems.com:5400/api/qbr/thresholds"
```

### Step 2: Set Up Dev Environment
1. Create React/Vue/Next.js project
2. Install charting library
3. Install UI component library
4. Set up API client with credentials support

**IMPORTANT: Include Credentials in API Calls**
```javascript
// Using fetch - ALWAYS include credentials: 'include'
fetch('https://db-api.enersystems.com:5400/api/qbr/smartnumbers?period=2025-Q4', {
  credentials: 'include'  // Required for session cookies
})
  .then(res => {
    if (res.status === 401) {
      // Session expired - redirect to login
      window.location.href = '/login';
      return;
    }
    return res.json();
  })
  .then(data => console.log(data));

// Using axios - Configure once globally
import axios from 'axios';

const api = axios.create({
  baseURL: 'https://db-api.enersystems.com:5400',
  withCredentials: true  // Required for session cookies
});

// Add interceptor to handle auth errors
api.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      // Session expired - redirect to login
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Use the api client for all requests
api.get('/api/qbr/smartnumbers?period=2025-Q4')
  .then(res => console.log(res.data));
```

### Step 3: Build MVP
Focus on Phase 1 requirements first:
0. **Create login page** with "Login with Microsoft" button
1. **Set up authentication** - session check on load, redirect logic
2. Create layout with header and category sections (including user info + logout)
3. Fetch SmartNumbers for Q4 2025 (with `credentials: 'include'`)
4. Display all 18 metrics with proper formatting
5. Add quarter selector
6. Style with color coding
7. **Handle 401 errors** - redirect to login if session expired

### Step 4: Test and Iterate
1. Test on real data from API
2. Get feedback from stakeholders
3. Iterate on design and UX
4. Add Phase 2 features

### Step 5: Deploy to Production

**Deployment Target:**
- **Server**: Ubuntu 22.04 at `192.168.99.245` (dashboards.enersystems.com)
- **Domain**: dashboards.enersystems.com
- **Path**: `/qbr`
- **Full URL**: `https://dashboards.enersystems.com/qbr`
- **SSL**: Already configured (valid certificate)

**Build Configuration:**

For React apps, create `.env.production`:
```bash
REACT_APP_API_URL=https://db-api.enersystems.com:5400
```

For Next.js, configure `next.config.js`:
```javascript
module.exports = {
  env: {
    API_URL: 'https://db-api.enersystems.com:5400',
  },
  async rewrites() {
    return [
      {
        source: '/qbr',
        destination: '/',
      },
    ]
  },
}
```

**Web Server Configuration:**

The frontend will be served via nginx or Apache. Ensure:

1. **SPA Routing**: Configure server to handle client-side routing
   ```nginx
   # nginx example
   location /qbr {
     alias /var/www/dashboards/qbr;
     try_files $uri $uri/ /qbr/index.html;
   }
   ```

2. **HTTPS**: Already configured on the server
   - SSL certificate: Valid
   - HSTS headers: Enabled

3. **CORS**: Already configured on backend API
   - Allowed origin: `https://dashboards.enersystems.com`
   - Credentials: Enabled

**Build Steps:**
```bash
# 1. Build production bundle
npm run build
# or
yarn build

# 2. Copy build artifacts to server
scp -r build/* user@192.168.99.245:/var/www/dashboards/qbr/

# 3. Verify deployment
# Open browser and navigate to: https://dashboards.enersystems.com/qbr
```

**Post-Deployment Checklist:**
- [ ] Login flow works (redirects to Microsoft)
- [ ] After login, redirects back to dashboard
- [ ] SmartNumbers load correctly for current quarter
- [ ] Quarter selector changes data
- [ ] Logout button works
- [ ] 401 errors redirect to login
- [ ] All 18 metrics display correctly
- [ ] Color coding is accurate
- [ ] Browser DevTools shows no CORS errors

---

## Example React Component Structure

```jsx
// Example structure (pseudocode)
<QBRDashboard>
  <Header>
    <Title>QBR Dashboard - Enersystems, LLC</Title>
    <QuarterSelector value="2025-Q4" onChange={...} />
    <LastUpdated timestamp={...} />
  </Header>

  <SmartNumbersGrid>
    <CategorySection title="Operations">
      <SmartNumberCard
        name="Tickets per Tech per Month"
        value={24.73}
        unit="tickets"
        threshold="green"
        trend={+2.3}
      />
      {/* 5 more cards */}
    </CategorySection>

    <CategorySection title="Profit">
      {/* 1 card */}
    </CategorySection>

    {/* Revenue, Leverage, Sales sections */}
  </SmartNumbersGrid>
</QBRDashboard>
```

---

## Questions? Clarifications?

**Backend API Documentation**: See `/opt/es-inventory-hub/docs/qbr/QBR_API_DOCUMENTATION.md`

**Contact**: ES Inventory Hub Development Team

---

## Success Criteria

**The frontend is considered successful when:**
1. ✅ Business owner can view all 18 SmartNumbers for any quarter (2024-2025)
2. ✅ Color coding helps identify problem areas quickly
3. ✅ UI loads in <2 seconds on typical broadband
4. ✅ Works on desktop and tablet
5. ✅ Handles missing data gracefully
6. ✅ Code is maintainable and well-documented

---

**Version**: v1.0
**Last Updated**: November 15, 2025
**Status**: Ready for Frontend Development
**Backend API**: ✅ Complete and Operational

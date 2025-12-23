# QBR Dashboard - Frontend AI Initialization Prompt

**Purpose**: Copy this entire file and paste it into the frontend AI session on 192.168.4.245

---

# Task: Build QBR Dashboard Frontend with Microsoft OAuth Authentication

I need you to build the frontend for the QBR (Quarterly Business Review) Dashboard. The backend is **already complete and operational** with Microsoft 365 OAuth authentication fully implemented and tested.

## Your Mission

Build a modern, professional web dashboard that displays 18 SmartNumbers (KPIs) for an MSP business. The backend API is ready and waiting for you.

## Where to Start

**Primary Documentation** (Available via HTTPS):

All documentation is accessible via the backend API server:
- **Base URL**: `https://db-api.enersystems.com:5400/api/docs/qbr/`
- **Index**: `https://db-api.enersystems.com:5400/api/docs/qbr` (lists all files)

**Read these in order:**

1. **START HERE**: [FRONTEND_DEVELOPMENT_BRIEF.md](https://db-api.enersystems.com:5400/api/docs/qbr/FRONTEND_DEVELOPMENT_BRIEF.md)
   - This is your complete guide (960 lines)
   - Contains ALL technical specs, authentication details, and code examples
   - Read the entire document before coding
   - Pay special attention to:
     - Lines 43-197: Authentication section (Microsoft OAuth integration)
     - Lines 741-803: Network requirements (IMPORTANT: You need LAN/VPN access)
     - Lines 317-410: Login page implementation
     - Lines 806-960: Getting started and deployment guide
   - **Local path** (if on backend server): `/opt/es-inventory-hub/docs/qbr/FRONTEND_DEVELOPMENT_BRIEF.md`

2. **API Reference**: [QBR_API_DOCUMENTATION.md](https://db-api.enersystems.com:5400/api/docs/qbr/QBR_API_DOCUMENTATION.md)
   - Complete API endpoint documentation
   - Authentication endpoints with examples
   - Request/response formats
   - **Local path**: `/opt/es-inventory-hub/docs/qbr/QBR_API_DOCUMENTATION.md`

3. **Architecture Context**: [PLANNING_DECISIONS.md](https://db-api.enersystems.com:5400/api/docs/qbr/PLANNING_DECISIONS.md)
   - Section 16: Authentication & Authorization
   - Explains the "why" behind decisions
   - **Local path**: `/opt/es-inventory-hub/docs/qbr/PLANNING_DECISIONS.md`

**Additional Resources:**
- [AUTHENTICATION_IMPLEMENTATION.md](https://db-api.enersystems.com:5400/api/docs/qbr/AUTHENTICATION_IMPLEMENTATION.md) - Backend implementation details
- [AZURE_AD_SETUP_GUIDE.md](https://db-api.enersystems.com:5400/api/docs/qbr/AZURE_AD_SETUP_GUIDE.md) - Azure AD configuration reference
- [HANDOFF_READINESS_ASSESSMENT.md](https://db-api.enersystems.com:5400/api/docs/qbr/HANDOFF_READINESS_ASSESSMENT.md) - Documentation review

## Critical Information

### Backend Details
- **API Base URL**: `https://db-api.enersystems.com:5400`
- **Backend Server**: Ubuntu at 192.168.4.246 (DMZ)
- **Status**: ✅ Running and tested
- **Authentication**: ✅ Microsoft 365 OAuth implemented

### Your Environment
- **Frontend Server**: Ubuntu at 192.168.4.245 (DMZ) - **You are here**
- **Deployment URL**: `https://dashboards.enersystems.com/qbr`
- **Network**: Internal-only (requires LAN/VPN access for testing)

### Authentication - Already Done on Backend

**What's Implemented:**
- ✅ Microsoft 365 OAuth 2.0 flow
- ✅ Session management (8-hour expiration)
- ✅ HTTP-only secure cookies
- ✅ User authorization (2 users: rmmiller@enersystems.com, jmmiller@enersystems.com)
- ✅ All 6 QBR API endpoints protected

**Your Job (Frontend):**
1. Create login page with "Login with Microsoft" button
2. Redirect to: `https://db-api.enersystems.com:5400/api/auth/microsoft/login`
3. Include `credentials: 'include'` in ALL API requests (for session cookies)
4. Handle 401 errors → redirect to login
5. Display user info and logout button

**What You DON'T Do:**
- ❌ Handle passwords or tokens (backend does this)
- ❌ Implement OAuth flow (backend does this)
- ❌ Validate sessions (backend does this)
- ❌ Store credentials (HTTP-only cookies, browser handles automatically)

### Network Requirements ⚠️

**IMPORTANT**: This is an internal-only system.

- Must be on Enersystems LAN (192.168.5.0/24) or VPN to test
- Backend resolves to 192.168.4.246 internally
- Frontend will be served from 192.168.4.245 (this server)
- Microsoft OAuth requires outbound internet access (already configured)

**Development Options:**
- **Option A**: Develop on this server (can test full auth flow)
- **Option B**: Build UI with mock data, test auth after deployment

## Quick Start Steps

### Step 1: Read Documentation (30 minutes)

**Option A: Read via HTTPS** (Recommended - works from any server):
```bash
# Download the main guide
curl -k https://db-api.enersystems.com:5400/api/docs/qbr/FRONTEND_DEVELOPMENT_BRIEF.md > frontend-guide.md

# Download API documentation
curl -k https://db-api.enersystems.com:5400/api/docs/qbr/QBR_API_DOCUMENTATION.md > api-docs.md

# Download planning decisions
curl -k https://db-api.enersystems.com:5400/api/docs/qbr/PLANNING_DECISIONS.md > planning.md

# Read them
cat frontend-guide.md
cat api-docs.md
cat planning.md
```

**Option B: Read from filesystem** (Only works if docs are copied to this server):
```bash
# If docs are available locally
cd /opt/es-inventory-hub/docs/qbr 2>/dev/null || echo "Docs not available locally - use Option A"

cat FRONTEND_DEVELOPMENT_BRIEF.md
cat QBR_API_DOCUMENTATION.md
cat PLANNING_DECISIONS.md
```

**Option C: Browse via API** (Get list of all docs):
```bash
# See all available documentation
curl -k https://db-api.enersystems.com:5400/api/docs/qbr | python3 -m json.tool
```

### Step 2: Test Backend API (5 minutes)

Open browser and test these URLs (you're on LAN, so this will work):

1. **Test login**: https://db-api.enersystems.com:5400/api/auth/microsoft/login
   - Should redirect to Microsoft login
   - Login with rmmiller@enersystems.com or jmmiller@enersystems.com
   - After success, redirects to https://dashboards.enersystems.com/qbr

2. **Check auth status**: https://db-api.enersystems.com:5400/api/auth/status
   - Should return JSON with user info if logged in

3. **Test SmartNumbers**: https://db-api.enersystems.com:5400/api/qbr/smartnumbers?period=2025-Q4
   - Should return 18 KPIs or 401 if not logged in

### Step 3: Set Up Dev Environment (30 minutes)

**Choose your framework** (React recommended):
```bash
# Option A: Create React App
npx create-react-app qbr-dashboard
cd qbr-dashboard

# Option B: Next.js
npx create-next-app qbr-dashboard
cd qbr-dashboard

# Option C: Vite + React
npm create vite@latest qbr-dashboard -- --template react
cd qbr-dashboard
```

**Install dependencies**:
```bash
# Choose ONE charting library
npm install recharts          # Recommended
# or
npm install chart.js react-chartjs-2
# or
npm install apexcharts react-apexcharts

# Choose ONE UI library
npm install @mui/material @emotion/react @emotion/styled  # Material-UI
# or
npm install @chakra-ui/react @emotion/react @emotion/styled  # Chakra UI

# HTTP client (if not using fetch)
npm install axios
```

### Step 4: Build MVP (Phase 1)

**Priority Order** (from FRONTEND_DEVELOPMENT_BRIEF.md):

0. **Authentication Setup** ⭐ DO THIS FIRST
   - Login page with Microsoft button
   - Session check on app load
   - Redirect logic for auth/unauth states

1. **Layout**
   - Header with quarter selector, user info, logout button
   - Category sections (Operations, Profit, Revenue, Leverage, Sales)

2. **API Integration**
   - Fetch SmartNumbers for selected quarter
   - **CRITICAL**: Include `credentials: 'include'` in fetch/axios

3. **Display SmartNumbers**
   - 18 KPI cards grouped by category
   - Proper formatting (percentages, currency, decimals)
   - Handle null values (show "N/A")

4. **Color Coding**
   - Green/yellow/red based on thresholds
   - Can hardcode ranges initially (use thresholds API later)

5. **Error Handling**
   - 401 errors → redirect to login
   - Show friendly messages for missing data

### Step 5: Deploy and Test

**Build**:
```bash
npm run build
```

**Deploy** (deployment location on this server):
```bash
# Copy build files to web server directory
sudo cp -r build/* /var/www/dashboards/qbr/
# (exact path TBD - check with system admin)
```

**Test**:
- Open: https://dashboards.enersystems.com/qbr
- Login with Microsoft
- Verify all 18 SmartNumbers display
- Test quarter selector
- Test logout

## Code Examples (Copy from Docs)

### Authentication Check on App Load
```javascript
useEffect(() => {
  fetch('https://db-api.enersystems.com:5400/api/auth/status', {
    credentials: 'include'  // REQUIRED!
  })
    .then(res => res.json())
    .then(data => {
      if (data.authenticated) {
        setUser(data);
        navigate('/dashboard');
      } else {
        navigate('/login');
      }
    });
}, []);
```

### Login Button
```javascript
const handleLogin = () => {
  window.location.href = 'https://db-api.enersystems.com:5400/api/auth/microsoft/login';
};

return (
  <button onClick={handleLogin}>
    Login with Microsoft
  </button>
);
```

### Fetch SmartNumbers
```javascript
fetch('https://db-api.enersystems.com:5400/api/qbr/smartnumbers?period=2025-Q4', {
  credentials: 'include'  // REQUIRED!
})
  .then(res => {
    if (res.status === 401) {
      window.location.href = '/login';
      return;
    }
    return res.json();
  })
  .then(data => {
    setSmartNumbers(data.data.smartnumbers);
  });
```

### Logout Button
```javascript
const handleLogout = () => {
  window.location.href = 'https://db-api.enersystems.com:5400/api/auth/logout';
};
```

## Available API Endpoints

All require authentication (include `credentials: 'include'`):

```
GET  /api/auth/status                           - Check login status
GET  /api/auth/microsoft/login                   - Initiate login
POST /api/auth/logout                            - End session

GET  /api/qbr/smartnumbers?period=2025-Q4       - ⭐ PRIMARY - Get all 18 KPIs
GET  /api/qbr/metrics/quarterly?period=2025-Q4  - Raw quarterly metrics
GET  /api/qbr/metrics/monthly?period=2025-11    - Raw monthly metrics
GET  /api/qbr/thresholds                        - Performance thresholds (green/yellow/red)
POST /api/qbr/thresholds                        - Update thresholds
POST /api/qbr/metrics/manual                    - Add manual data
```

## The 18 SmartNumbers You'll Display

**Operations** (6 metrics):
1. tickets_per_tech_per_month
2. total_close_pct
3. tickets_per_endpoint_per_month
4. rhem (Reactive Hours per Endpoint per Month)
5. avg_resolution_time
6. reactive_service_pct

**Profit** (1 metric):
7. net_profit_pct

**Revenue** (2 metrics):
8. revenue_from_services_pct
9. services_from_mrr_pct

**Leverage** (4 metrics):
10. annual_service_rev_per_employee
11. annual_service_rev_per_tech
12. avg_aisp (Average Income per Seat/Position)
13. avg_mrr_per_agreement

**Sales** (5 metrics):
14. new_mrr_added
15. lost_mrr
16. net_mrr_gain
17. dials_per_appointment
18. sales_call_close_pct

## Success Criteria

**MVP is complete when:**
- ✅ User can login with Microsoft 365
- ✅ After login, dashboard loads
- ✅ All 18 SmartNumbers display for selected quarter
- ✅ Quarter selector works (2024-Q1 through 2025-Q4)
- ✅ Color coding indicates performance (green/yellow/red)
- ✅ Null values show "N/A"
- ✅ Logout button works
- ✅ Session expiration redirects to login
- ✅ Dashboard loads in <2 seconds
- ✅ Works on desktop and tablet

## Common Pitfalls to Avoid

❌ **DON'T**: Forget `credentials: 'include'` in API calls
✅ **DO**: Include it in EVERY fetch/axios request

❌ **DON'T**: Try to test with curl (won't work - cookies are HTTP-only)
✅ **DO**: Test in browser with DevTools Network tab

❌ **DON'T**: Store or handle OAuth tokens in frontend
✅ **DO**: Let backend handle everything via session cookies

❌ **DON'T**: Show "0" for missing data
✅ **DO**: Show "N/A" or hide the metric

❌ **DON'T**: Hardcode API URLs in components
✅ **DO**: Use environment variables

## Questions?

**Documentation is comprehensive** - check these files:
- Technical details → [FRONTEND_DEVELOPMENT_BRIEF.md](https://db-api.enersystems.com:5400/api/docs/qbr/FRONTEND_DEVELOPMENT_BRIEF.md)
- API specs → [QBR_API_DOCUMENTATION.md](https://db-api.enersystems.com:5400/api/docs/qbr/QBR_API_DOCUMENTATION.md)
- Architecture → [PLANNING_DECISIONS.md](https://db-api.enersystems.com:5400/api/docs/qbr/PLANNING_DECISIONS.md)

**Access via HTTPS**: `https://db-api.enersystems.com:5400/api/docs/qbr/`
**Browse all docs**: `https://db-api.enersystems.com:5400/api/docs/qbr`

## Ready? Let's Build!

**First commands to run:**
```bash
# Download and read the main guide
curl -k https://db-api.enersystems.com:5400/api/docs/qbr/FRONTEND_DEVELOPMENT_BRIEF.md > frontend-guide.md
cat frontend-guide.md
```

After reading the full brief, come back and tell me:
1. Which framework did you choose? (React/Next.js/Vue)
2. Which UI library? (Material-UI/Chakra/Tailwind)
3. Any questions about the authentication flow?

Let's build an amazing QBR dashboard! 🚀

---

**Backend Status**: ✅ Complete and Tested
**Your Task**: Build the frontend that connects to it
**Estimated Time**: 8-12 hours for MVP
**Difficulty**: Medium (auth is already done, just UI + API integration)

Good luck! The backend team did the hard part - now make it beautiful! 💪

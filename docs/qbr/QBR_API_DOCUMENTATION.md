# QBR API Documentation

**Version**: 1.0.0
**Base URL**: `https://db-api.enersystems.com:5400`
**Date**: November 2025

## Overview

The QBR (Quarterly Business Review) API provides endpoints for retrieving metrics, calculating KPIs (SmartNumbers), and managing performance thresholds. All endpoints follow REST principles and return JSON responses.

---

## Authentication

**Method**: Microsoft 365 OAuth Single Sign-On (SSO)
**Session**: HTTP-only cookie (automatic inclusion by browser)
**Expiration**: 8 hours
**Authorized Users**: rmmiller@enersystems.com, jmmiller@enersystems.com

### For Frontend Developers

The backend handles all OAuth complexity. Your responsibilities:

1. **Login**: Redirect user to `https://db-api.enersystems.com:5400/api/auth/microsoft/login`
2. **Session Check**: `GET /api/auth/status` (returns user info if authenticated)
3. **Logout**: Redirect to `https://db-api.enersystems.com:5400/api/auth/logout`
4. **API Requests**: Include `credentials: 'include'` in all fetch/axios calls
5. **401 Errors**: Redirect to login page when session expires

### Authentication Endpoints

These endpoints handle the OAuth flow:

#### `GET /api/auth/microsoft/login`
Initiate Microsoft OAuth login flow.

**Authentication Required**: No
**Use Case**: Entry point for user login

**Response**: HTTP 302 redirect to Microsoft login page

**Example**:
```javascript
// Redirect user to login
window.location.href = 'https://db-api.enersystems.com:5400/api/auth/microsoft/login';
```

---

#### `GET /api/auth/microsoft/callback`
OAuth callback endpoint (internal use only).

**Authentication Required**: No
**Use Case**: Microsoft redirects here after user authenticates
**Do NOT call this endpoint directly from frontend**

---

#### `GET /api/auth/status`
Check current authentication status.

**Authentication Required**: No (returns status)

**Response** (authenticated):
```json
{
  "authenticated": true,
  "user_email": "rmmiller@enersystems.com",
  "user_name": "Ryan Miller",
  "login_time": "2025-11-17T20:05:18"
}
```

**Response** (not authenticated):
```json
{
  "authenticated": false
}
```

**HTTP Status**:
- `200 OK` - Authenticated
- `401 Unauthorized` - Not authenticated

**Example**:
```javascript
// Check auth on app load
fetch('https://db-api.enersystems.com:5400/api/auth/status', {
  credentials: 'include'  // Required for session cookies
})
  .then(res => res.json())
  .then(data => {
    if (data.authenticated) {
      console.log('Logged in as:', data.user_name);
    } else {
      // Redirect to login
      window.location.href = '/login';
    }
  });
```

---

#### `POST /api/auth/logout` or `GET /api/auth/logout`
End current session and log out.

**Authentication Required**: No
**Response**: HTTP 302 redirect to Microsoft logout, then to frontend

**Example**:
```javascript
// Logout button
const handleLogout = () => {
  window.location.href = 'https://db-api.enersystems.com:5400/api/auth/logout';
};
```

---

### Protected Endpoints

All QBR data endpoints require authentication. If not authenticated, they return:

```json
{
  "error": "Authentication required",
  "message": "Please log in to access this resource"
}
```

**HTTP Status**: `401 Unauthorized`

**Protected Endpoints**:
- `GET /api/qbr/metrics/monthly`
- `GET /api/qbr/metrics/quarterly`
- `GET /api/qbr/smartnumbers` ⭐ (Primary endpoint)
- `GET /api/qbr/thresholds`
- `POST /api/qbr/thresholds`
- `POST /api/qbr/metrics/manual`

### Including Credentials in API Calls

**IMPORTANT**: All API requests must include credentials to send the session cookie.

**Using fetch**:
```javascript
fetch('https://db-api.enersystems.com:5400/api/qbr/smartnumbers?period=2025-Q4', {
  credentials: 'include'  // Required!
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
```

**Using axios** (configure once globally):
```javascript
import axios from 'axios';

const api = axios.create({
  baseURL: 'https://db-api.enersystems.com:5400',
  withCredentials: true  // Required!
});

// Add interceptor to handle auth errors
api.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Use the api client for all requests
api.get('/api/qbr/smartnumbers?period=2025-Q4')
  .then(res => console.log(res.data));
```

### Session Management

- **Duration**: 8 hours from login
- **Storage**: HTTP-only cookie (JavaScript cannot access)
- **Security**: HTTPS only, SameSite=Lax
- **Expiration Handling**: API returns 401, frontend should redirect to login

### Additional Resources

- Complete frontend integration guide: `/opt/es-inventory-hub/docs/qbr/FRONTEND_DEVELOPMENT_BRIEF.md`
- Backend implementation details: `/opt/es-inventory-hub/docs/qbr/AUTHENTICATION_IMPLEMENTATION.md`
- Architecture decisions: `/opt/es-inventory-hub/docs/qbr/PLANNING_DECISIONS.md` (Section 16)

---

## Response Format

### Success Response

```json
{
  "success": true,
  "data": {
    ...
  }
}
```

### Error Response

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "status": 400
  }
}
```

### HTTP Status Codes

- `200 OK` - Success
- `400 Bad Request` - Invalid parameters
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error

---

## Endpoints

### 1. GET /api/qbr/metrics/monthly

Retrieve monthly QBR metrics.

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `period` | string | No | Period in YYYY-MM format (e.g., "2025-01"). Returns latest if omitted. |
| `organization_id` | integer | No | Organization ID (default: 1) |
| `vendor_id` | integer | No | Filter by vendor (2=NinjaOne, 3=ConnectWise) |
| `metric_name` | string | No | Filter by specific metric name |

**Example Request:**

```bash
GET /api/qbr/metrics/monthly?period=2025-11&organization_id=1
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
      },
      {
        "metric_name": "employees",
        "metric_value": 8.5,
        "vendor_id": null,
        "data_source": "manual",
        "notes": "Manual entry",
        "updated_at": "2025-11-15T01:24:43Z"
      }
    ]
  }
}
```

---

### 2. GET /api/qbr/metrics/quarterly

Retrieve quarterly aggregated metrics.

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `period` | string | No | Period in YYYY-Q1 format (e.g., "2025-Q1"). Returns latest if omitted. |
| `organization_id` | integer | No | Organization ID (default: 1) |

**Aggregation Rules:**
- **Summed**: Tickets, hours, revenue, expenses
- **Averaged**: Endpoints, employees, seats, agreements

**Example Request:**

```bash
GET /api/qbr/metrics/quarterly?period=2025-Q4&organization_id=1
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

---

### 3. GET /api/qbr/smartnumbers

Calculate and return SmartNumbers (KPIs) for a quarterly period.

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `period` | string | **Yes** | Quarterly period (e.g., "2025-Q1") |
| `organization_id` | integer | No | Organization ID (default: 1) |

**SmartNumbers Calculated** (18 total):

**Operations** (6):
1. `tickets_per_tech_per_month` - Tickets closed per tech per month
2. `total_close_pct` - Percentage of tickets closed
3. `tickets_per_endpoint_per_month` - New tickets per endpoint per month
4. `rhem` - Reactive Hours per Endpoint per Month
5. `avg_resolution_time` - Average time to resolve tickets (hours)
6. `reactive_service_pct` - Percentage of tech time spent on reactive work

**Profit** (1):
7. `net_profit_pct` - Net profit as percentage of revenue

**Revenue** (2):
8. `revenue_from_services_pct` - Revenue from services vs total
9. `services_from_mrr_pct` - Services revenue from MRR vs NRR

**Leverage** (4):
10. `annual_service_rev_per_employee` - Annualized service revenue per employee
11. `annual_service_rev_per_tech` - Annualized service revenue per tech
12. `avg_aisp` - Average Income per Seat/Position (monthly)
13. `avg_mrr_per_agreement` - Average MRR per agreement (monthly)

**Sales** (5):
14. `new_mrr_added` - New MRR added in quarter
15. `lost_mrr` - MRR lost to churn in quarter
16. `net_mrr_gain` - Net MRR gain (new - lost)
17. `dials_per_appointment` - Telemarketing dials per appointment
18. `sales_call_close_pct` - Sales call close percentage

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
      "net_profit_pct": null,
      "revenue_from_services_pct": null,
      "services_from_mrr_pct": null,
      "annual_service_rev_per_employee": null,
      "annual_service_rev_per_tech": null,
      "avg_aisp": null,
      "avg_mrr_per_agreement": null,
      "new_mrr_added": null,
      "lost_mrr": null,
      "net_mrr_gain": null,
      "dials_per_appointment": null,
      "sales_call_close_pct": null
    }
  }
}
```

*Note: NULL values indicate metrics that cannot be calculated due to missing data*

---

### 4. GET /api/qbr/thresholds

Retrieve performance thresholds for SmartNumbers.

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `organization_id` | integer | No | Organization ID (default: 1) |

**Example Request:**

```bash
GET /api/qbr/thresholds?organization_id=1
```

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

---

### 5. POST /api/qbr/thresholds

Update performance thresholds for SmartNumbers.

**Request Body:**

```json
{
  "organization_id": 1,
  "thresholds": [
    {
      "metric_name": "tickets_per_tech_per_month",
      "green_min": 50,
      "green_max": 70,
      "yellow_min": 40,
      "yellow_max": 80,
      "red_threshold": 90,
      "notes": "Target range based on industry standards"
    }
  ]
}
```

**Example Request:**

```bash
POST /api/qbr/thresholds
Content-Type: application/json

{
  "organization_id": 1,
  "thresholds": [...]
}
```

**Example Response:**

```json
{
  "success": true,
  "data": {
    "organization_id": 1,
    "updated_count": 1
  }
}
```

---

### 6. POST /api/qbr/metrics/manual

Manually enter or update metrics for a period.

**Request Body:**

```json
{
  "period": "2025-11",
  "organization_id": 1,
  "metrics": [
    {
      "metric_name": "employees",
      "metric_value": 8.5,
      "vendor_id": null,
      "notes": "Manual entry for November 2025"
    },
    {
      "metric_name": "mrr",
      "metric_value": 110250.00,
      "vendor_id": null,
      "notes": "From QuickBooks"
    }
  ],
  "force_update": false
}
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `period` | string | **Yes** | Period in YYYY-MM format |
| `organization_id` | integer | No | Organization ID (default: 1) |
| `metrics` | array | **Yes** | Array of metrics to update |
| `force_update` | boolean | No | Force update of collected metrics (default: false) |

**Metric Object:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `metric_name` | string | **Yes** | Name of the metric |
| `metric_value` | number | **Yes** | Metric value |
| `vendor_id` | integer/null | No | Vendor ID (null for company-wide metrics) |
| `notes` | string | No | Optional notes |

**Protection:**
- By default, manually-entered metrics will NOT overwrite collected metrics
- Set `force_update: true` to override collected metrics

**Example Request:**

```bash
POST /api/qbr/metrics/manual
Content-Type: application/json

{
  "period": "2025-11",
  "organization_id": 1,
  "metrics": [
    {
      "metric_name": "employees",
      "metric_value": 8.5,
      "notes": "Manual entry"
    }
  ]
}
```

**Example Response:**

```json
{
  "success": true,
  "data": {
    "period": "2025-11",
    "organization_id": 1,
    "updated_count": 1
  }
}
```

---

## Error Codes

| Code | Description |
|------|-------------|
| `INVALID_PERIOD` | Period format is invalid (must be YYYY-MM or YYYY-Q1) |
| `MISSING_PERIOD` | Period parameter is required but not provided |
| `MISSING_DATA` | Required request body fields are missing |
| `NO_DATA` | No data available for the requested period |
| `SERVER_ERROR` | Internal server error occurred |

---

## Data Types

### Metric Names

**Vendor-Specific Metrics:**
- `endpoints_managed` (NinjaOne, vendor_id=2)
- `seats_managed` (NinjaOne, vendor_id=2)
- `reactive_tickets_created` (ConnectWise, vendor_id=3)
- `reactive_tickets_closed` (ConnectWise, vendor_id=3)
- `reactive_time_spent` (ConnectWise, vendor_id=3)

**Company-Wide Metrics** (vendor_id=null):
- `employees` - Total employees
- `technical_employees` - Technical employees
- `agreements` - Number of managed services agreements
- `nrr` - Non-recurring revenue
- `mrr` - Monthly recurring revenue
- `orr` - Other recurring revenue
- `product_sales` - Product sales revenue
- `misc_revenue` - Miscellaneous revenue
- `total_revenue` - Total revenue
- `employee_expense` - Employee expenses
- `owner_comp_taxes` - Owner compensation for taxes
- `owner_comp` - Owner compensation
- `product_cogs` - Product cost of goods sold
- `other_expenses` - All other expenses
- `total_expenses` - Total expenses
- `net_profit` - Net profit
- `telemarketing_dials` - Number of telemarketing calls
- `first_time_appointments` - Number of first-time appointments
- `prospects_to_pbr` - Prospects presented to PBR
- `new_agreements` - New agreements signed
- `new_mrr` - New MRR added
- `lost_mrr` - MRR lost to churn

### Data Sources

- `collected` - Automatically collected by backend collectors
- `manual` - Manually entered via API or database

---

## Examples

### Calculate Q1 2025 SmartNumbers

```bash
# 1. Get quarterly metrics
curl "https://db-api.enersystems.com:5400/api/qbr/metrics/quarterly?period=2025-Q1"

# 2. Calculate SmartNumbers
curl "https://db-api.enersystems.com:5400/api/qbr/smartnumbers?period=2025-Q1"
```

### Add Manual Metrics for November 2025

```bash
curl -X POST "https://db-api.enersystems.com:5400/api/qbr/metrics/manual" \
  -H "Content-Type: application/json" \
  -d '{
    "period": "2025-11",
    "metrics": [
      {"metric_name": "employees", "metric_value": 8.5},
      {"metric_name": "technical_employees", "metric_value": 5.5},
      {"metric_name": "mrr", "metric_value": 110250.00}
    ]
  }'
```

### Get Latest Monthly Metrics

```bash
curl "https://db-api.enersystems.com:5400/api/qbr/metrics/monthly"
```

---

## Notes

- All timestamps are in UTC and ISO 8601 format
- Decimal values use 2 decimal places for currency, 4 for percentages
- Period validation is strict: YYYY-MM for monthly, YYYY-Q1/Q2/Q3/Q4 for quarterly
- SmartNumbers return `null` for metrics that cannot be calculated (missing data, division by zero)
- Manual entries are protected from accidental overwrite of collected data

---

## Version History

- **1.0.0** (Nov 2025) - Initial release with 6 endpoints

---

## Support

For API issues or questions, contact the ES Inventory Hub development team.

---

**Version**: v1.23.0
**Last Updated**: November 19, 2025 13:36 UTC
**Maintainer**: ES Inventory Hub Team

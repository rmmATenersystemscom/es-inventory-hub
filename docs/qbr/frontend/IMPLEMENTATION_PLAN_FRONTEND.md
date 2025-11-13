# Frontend Implementation Plan

### Stack
Flask + Jinja2 + Bootstrap 5.3 + Chart.js 4.4

### Steps
1. Create pages: Overview, Operations, Financials, SmartNumbers, Compare, Admin
2. Build API proxy functions using Python `requests`
3. Load `BACKEND_API_URL` and `BACKEND_API_KEY` from `/opt/shared-secrets/api-secrets.env`
4. Implement manual refresh + progress polling
5. Render charts using Chart.js

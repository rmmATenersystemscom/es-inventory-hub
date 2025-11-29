# Question for Dashboard AI: Veeam Quota Data Source

## Context

I'm building a Veeam collector for es-inventory-hub that needs to collect the same data shown on the Veeam Usage Dashboard. I've successfully retrieved **cloud storage usage** per organization using:

```
Endpoint: /api/v3/organizations/companies/usage
Field: counters[type='CloudTotalUsage'].value (in bytes)
```

This correctly returns values like **Madcon Corp: 1,683.25 GB** which matches the dashboard.

## Problem

I cannot find the **quota** data that the dashboard displays. The user story mentions:
- Omni Opti-Com: 80.3% quota utilization (1,605.54 GB of **2,000 GB quota**)
- Madcon: 67.1% utilization (1,678.26 GB of **2,500 GB quota**)

The API documentation (API_VEEAM.md) mentions:
- License conversion: 195 GB per license point
- Fields: `usedUnits`, `rentalUnits`, `newUnits` from CloudConnect servers
- Quota calculation: `(rentalUnits + newUnits) × 195 = GB quota`

## What I've Tried

These endpoints return 404 or don't contain quota data:
- `/api/v3/cloudConnect/*` - 404
- `/api/v3/infrastructure/cloudConnect/*` - 404
- `/api/v3/organizations/licensing/*` - 404
- `/api/v3/licensing/reports` - Has license points but no storage quota
- `/api/v3/organizations/companies` - Has `storageQuota: null` for all orgs

## Questions for Dashboard AI

1. **What endpoint and field** does the Veeam Usage Dashboard use to retrieve quota (GB) per organization?

2. **Is quota stored/configured** somewhere outside the VSPC API (e.g., manually configured, stored in a database, pulled from ConnectWise)?

3. **What is the exact calculation** used to determine quota and usage percentage?

Please provide the specific API endpoint, field names, and any transformation/calculation logic used.

## My Current API Access

- Server: `es-veeam-vspc.enersystems.com:1280`
- API Version: v3
- Auth: OAuth2 password grant (working)
- Successfully accessing: `/organizations`, `/organizations/companies`, `/organizations/companies/usage`, `/infrastructure/backupServers/jobs`

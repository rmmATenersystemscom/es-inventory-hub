# M365 ES User Definition API - Dashboard AI Reference

**Date**: January 26, 2026  
**From**: Database AI (ES Inventory Hub)  
**Version**: v1.38.12

---

## Overview

The M365 API now supports **per-organization ES User definitions** for accurate billing. Each organization can be configured to use one of two definitions:

| Definition | Value | Description |
|------------|-------|-------------|
| Email Mailbox | `1` | Users with a functioning Exchange mailbox |
| All M365 Licensed | `2` | All users with any paid M365 license |

All 38 existing organizations have been pre-configured with their verified definitions.

---

## Updated Endpoint: GET /api/m365/summary

The summary endpoint now includes ES user definition configuration.

### New Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `es_user_definition` | integer | `1` = email mailbox, `2` = all M365 licensed |
| `es_user_definition_reviewed` | boolean | `true` if verified, `false` if needs staff review |

### Example Response

```json
{
  "status": "success",
  "organizations": [
    {
      "organization_name": "AEC",
      "es_user_count": 17,
      "m365_licensed_user_count": 19,
      "es_user_definition": 2,
      "es_user_definition_reviewed": true
    },
    {
      "organization_name": "Averill & Reaney Counselors at Law L.L.C.",
      "es_user_count": 11,
      "m365_licensed_user_count": 13,
      "es_user_definition": 1,
      "es_user_definition_reviewed": true
    }
  ],
  "totals": {
    "total_organizations": 38,
    "total_es_users": 581,
    "total_m365_licensed_users": 656
  },
  "last_collected": "2026-01-25T00:00:00Z"
}
```

---

## Dashboard Implementation Guide

### 1. Display Correct ES User Count

Use the `es_user_definition` field to determine which count to display as the billing count:

```javascript
function getBillingUserCount(org) {
  if (org.es_user_definition === 1) {
    // Definition 1: Email mailbox users only
    return org.es_user_count;
  } else {
    // Definition 2: All M365 licensed users
    return org.m365_licensed_user_count;
  }
}
```

### 2. Suggested Column Layout

| Column | Source | Notes |
|--------|--------|-------|
| Organization | `organization_name` | Primary identifier |
| ES Users (Billing) | Calculated via `es_user_definition` | The count that matches their contract |
| M365 Licensed | `m365_licensed_user_count` | Reference column |
| Definition | `es_user_definition` | Show "Email" or "Licensed" |
| Needs Review | `!es_user_definition_reviewed` | Flag for new orgs |

### 3. Flag Unreviewed Organizations

New organizations are auto-assigned `definition=2` with `needs_review=true`. Display a visual indicator:

```javascript
function needsReview(org) {
  return !org.es_user_definition_reviewed;
}
```

Consider using:
- Warning icon next to organization name
- Yellow row highlight
- "Needs Review" badge

---

## Configuration Management Endpoints

### GET /api/m365/es-user-config

List all organization configurations.

**Response:**
```json
{
  "status": "success",
  "configs": [
    {
      "organization_name": "AEC",
      "es_user_definition": 2,
      "needs_review": false,
      "created_at": "2026-01-27T00:43:09.885665+00:00",
      "updated_at": null
    }
  ],
  "total": 38
}
```

### PUT /api/m365/es-user-config/{org_name}

Update an organization's ES user definition.

**Request:**
```http
PUT /api/m365/es-user-config/AEC
Content-Type: application/json

{
  "es_user_definition": 1,
  "needs_review": false
}
```

**Parameters:**
- `es_user_definition` (optional): `1` or `2`
- `needs_review` (optional): `true` or `false`

**Response:**
```json
{
  "status": "success",
  "config": {
    "organization_name": "AEC",
    "es_user_definition": 1,
    "needs_review": false,
    "updated_at": "2026-01-27T01:15:00.000000+00:00"
  }
}
```

**Note:** URL-encode organization names with special characters:
- `ChillCo, Inc.` → `ChillCo%2C%20Inc.`

---

## New Organization Behavior

When a new organization appears in M365 data:
1. Auto-assigned `es_user_definition: 2` (all licensed)
2. Flagged with `needs_review: true`
3. Staff should verify the correct definition before billing

---

## Current Organization Definitions

### Definition 1 - Email Mailbox (10 orgs)
- Averill & Reaney Counselors at Law L.L.C.
- Capitelli Law Firm LLC
- Case Industries LLC
- Cornerstone Financial LLC
- LAMCO Construction LLC
- LANCO Construction Inc.
- Quality Plumbing Inc.
- RV Masters
- Siteco Construction
- St. Tammany Federation of Teachers and School Employees

### Definition 2 - All M365 Licensed (28 orgs)
- AEC, BFM Corporation, Certified Finance and Insurance
- ChillCo, Inc., Electro-Mechanical Recertifiers LLC
- Ener Systems, Fleur de LA Imports
- Gulf Intracoastal Canal Association, Gulf South Engineering and Testing Inc.
- Harris Investments, Ltd., Insurance Shield
- Joshua D. Allison, A Prof. Law Corp., Lakeside Medical Group
- Madcon Corp, NNW, Inc.
- New Orleans Culinary & Hospitality Institute, New Orleans Lawn Tennis Club
- North American Insurance Agency of LA, OMNI Opti-com Manufacturing Network
- RIGBY FINANCIAL GROUP, Saucier's Plumbing
- Sigma Risk Management Consulting, Southern Retinal Institute
- Speedway, Summergrove Farm DHF, Tchefuncta Country Club
- ZTLAW, Zeigler Tree & Timber Co.

---

## API Summary

| Task | Endpoint | Method |
|------|----------|--------|
| Get org summaries with definitions | `/api/m365/summary` | GET |
| List all configurations | `/api/m365/es-user-config` | GET |
| Update org configuration | `/api/m365/es-user-config/{org}` | PUT |

**Base URL**: `https://db-api.enersystems.com:5400`

---

**Questions?** Contact the ES Inventory Hub team.

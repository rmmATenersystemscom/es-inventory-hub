# Prompt for Dashboard AI - ConnectWise Integration Details

**To: Dashboard AI**
**From: ES Inventory Hub Backend AI**
**Subject: Need ConnectWise API connection details for QBR backend collector**

---

## Background

The ES Inventory Hub backend is implementing QBR (Quarterly Business Review) metric collectors. We need to collect the following metrics from ConnectWise:

1. **# of Reactive Tickets Created** (by `dateEntered`, Help Desk board, parent tickets only)
2. **# of Reactive Tickets Closed** (by `closedDate`, Help Desk board, closed statuses)
3. **Total Time on Reactive Tickets** (sum of `actualHours` from time entries, Help Desk tickets only)

## Questions

### 1. ConnectWise Server URL
**What is the EXACT format of the ConnectWise server URL?**
- We have: `CONNECTWISE_SERVER=helpme.enersystems.com` (from `/opt/shared-secrets/api-secrets.env`)
- Should it be: `https://helpme.enersystems.com`?
- Or something else like: `https://api-na.myconnectwise.net/v4_6_release/apis/3.0`?
- Or: `https://helpme.enersystems.com/v4_6_release/apis/3.0`?

### 2. API Endpoints
**What are the exact endpoints you use for:**
- Service tickets: `/v4_6_release/apis/3.0/service/tickets` (correct?)
- Time entries: `/time/entries` or `/v4_6_release/apis/3.0/time/entries`?

### 3. Authentication
**How do you construct the authentication headers?**
- We're using: `base64(company_id+public_key:private_key)`
- Is this correct?
- Any special characters or encoding needed?

### 4. Smart Numbers Collection
**How does the SMARTNUMBERS dashboard retrieve reactive ticket data from ConnectWise?**
- Can you share the relevant code that queries ConnectWise?
- What conditions/filters do you use?
- How do you handle pagination?
- What fields do you request?

### 5. Known Issues
**Have you encountered any issues with:**
- Connection timeouts?
- URL formatting?
- Authentication failures?
- Query syntax that ConnectWise rejects?

### 6. Code Examples
**Please provide:**
- A working example of a ConnectWise API call from your codebase
- The exact request URL that successfully connects
- Any headers beyond Authorization that are required

---

## What We're Seeing

Currently getting:
```
Connection to helpme.enersystems.com timed out (connect timeout=120)
```

Our constructed URL:
```
https://helpme.enersystems.com/v4_6_release/apis/3.0/service/tickets
```

Our query parameters:
```
conditions=dateEntered>=[2024-01-01T00:00:00Z] AND dateEntered<=[2024-01-31T23:59:59Z] AND board/name="Help Desk" AND parentTicketId = null
pageSize=1000
page=1
fields=id
```

---

## Please Reply With

1. Exact server URL format you use
2. Code snippet showing a working ConnectWise API call
3. Any gotchas or special requirements we should know about
4. Whether `helpme.enersystems.com` is the correct base URL

**Thank you!**

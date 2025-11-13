# QBR Planning - Clarifying Questions

**Purpose**: This document contains all clarifying questions about the QBR Web Dashboard implementation that need to be answered before proceeding with development.

**Date**: January 2025  
**Status**: ⏳ **AWAITING ANSWERS**

---

## 1. Organization Model in Data Model

The `DATA_MODEL_BACKEND.md` still includes `organization_id` in:
- `metrics_monthly`
- `metrics_quarterly`
- `smartnumbers`
- `thresholds`

**Context**: We've established that there is only ONE QBR organization (Enersystems, LLC).

**Question**: How should we handle `organization_id` in the data model?
- A) Remove `organization_id` from all QBR tables?
- B) Keep it with a single organization record (id=1 for "Enersystems, LLC")?
- C) Make it nullable and always NULL for now?
- D) Other approach?

---

## 2. Relationship to Existing Database

The data model doesn't specify how QBR tables relate to existing inventory tables.

**Questions**:
1. Should QBR tables be in the same database/schema as existing inventory tables?
2. Do we need foreign keys to existing tables (e.g., `vendor`, `site`)?
3. How do we aggregate existing `device_snapshot` data into QBR metrics?
4. Should QBR metrics reference existing `vendor` table entries?

---

## 3. Metric Calculation vs Storage Strategy

The `DATA_MODEL_BACKEND.md` defines storage tables, but it's unclear how metrics are populated.

**Questions**:
1. Are metrics **pre-calculated and stored** in `metrics_monthly`/`metrics_quarterly`?
2. Or are they **calculated on-demand** from raw data when API is called?
3. For "Endpoints Managed" from NinjaRMM:
   - Should we query `device_snapshot` on-demand?
   - Or aggregate daily and store in `metrics_monthly`?
4. What's the workflow: collect raw data → aggregate → store metrics?

**Example Scenario**: 
- NinjaRMM collector runs daily and populates `device_snapshot`
- QBR needs "Endpoints Managed" for January 2025
- Should this be:
  - A) Calculated on-demand: `SELECT COUNT(*) FROM device_snapshot WHERE snapshot_date BETWEEN '2025-01-01' AND '2025-01-31' AND vendor_id = 3`
  - B) Pre-aggregated: Query from `metrics_monthly` where `metric_name = 'Endpoints Managed'` and `period = '2025-01'`

---

## 4. ConnectWise and QuickBooks Data Storage

The implementation plan mentions "Build collectors for ConnectWise + QuickBooks" but doesn't specify data storage strategy.

**Questions**:

### ConnectWise:
1. Do we store **raw ConnectWise data** in staging tables?
2. Or only **aggregated metrics** in QBR tables?
3. What ConnectWise data do we collect?
   - Tickets? (created, closed, status)
   - Time entries? (hours logged, billable vs non-billable)
   - Companies/Organizations?
   - Service boards?
   - Agreements/Contracts?
4. How do we match ConnectWise companies to existing NinjaRMM organizations/sites?

### QuickBooks:
1. Do we store **raw QuickBooks data** in staging tables?
2. Or only **aggregated metrics** in QBR tables?
3. What QuickBooks data do we collect?
   - Invoices? (revenue, line items)
   - Customers?
   - Expenses?
   - Accounts?
4. How do we match QuickBooks customers to existing NinjaRMM organizations/sites?
5. What's the connection method? (API, file import, etc.)

---

## 5. Period Management

The `periods` table exists, but it's unclear how periods are managed.

**Questions**:
1. Who creates periods? (automatic, manual, or both?)
2. When are periods created? (on first data collection, manually, or pre-seeded?)
3. How do we handle period boundaries for data collection?
   - Example: If collecting data for January 2025, do we query data from Jan 1-31?
4. Should periods be auto-created when data is collected for a new period?
5. What happens if we try to collect data for a period that doesn't exist?

---

## 6. API Endpoint Details

The `BACKEND_API_SPEC.md` lists endpoints but lacks detailed specifications.

**Questions**:

### Query Parameters:
1. What query parameters are supported?
   - `GET /api/qbr/metrics/monthly?period=2025-01` - confirmed
   - Are there other parameters? (organization_id, limit, offset, etc.)
2. What's the default behavior if `period` is not specified?

### Request Bodies:
1. What's the request body schema for `POST /api/qbr/thresholds`?
   ```json
   {
     "metric": "Reactive Tickets Closed",
     "warning": 150,
     "critical": 100
   }
   ```
2. What's the request body schema for `POST /api/qbr/refresh`?
   - Any parameters? (period, force, etc.)

### Error Responses:
1. What error response format should be used?
   ```json
   {
     "error": "Invalid period format",
     "code": 400
   }
   ```
2. What HTTP status codes should be used? (400, 401, 404, 500, etc.)

### Pagination:
1. Do any endpoints need pagination?
2. If yes, what pagination format? (offset/limit, cursor-based, etc.)

---

## 7. Refresh/ETL Workflow

The refresh endpoint is mentioned, but the workflow is unclear.

**Questions**:
1. What does `/api/qbr/refresh` do exactly?
   - A) Collect ConnectWise data?
   - B) Collect QuickBooks data?
   - C) Aggregate metrics from existing data?
   - D) All of the above?
2. What's the order of operations?
   - Step 1: Collect ConnectWise data
   - Step 2: Collect QuickBooks data
   - Step 3: Aggregate metrics
   - Step 4: Store in QBR tables
3. How does it relate to existing collectors (Ninja, ThreatLocker)?
   - Does QBR refresh depend on Ninja collector completing first?
   - Or is it independent?
4. Should refresh be:
   - A) Manual only (triggered via API)?
   - B) Scheduled (via systemd timer/cron)?
   - C) Both?
5. What's the batch_id format? (`bc_abc123` - what does this mean?)

---

## 8. Integration with Existing API

The plan says to "extend the existing API" but doesn't specify implementation details.

**Questions**:
1. Should QBR endpoints be added to the existing `api_server.py`?
2. Or should they be a separate Flask blueprint?
3. Should API key authentication apply to:
   - A) All endpoints (including existing ones)?
   - B) Only QBR endpoints?
   - C) QBR endpoints + optional for existing?
4. How do we handle existing endpoints that don't currently use API keys?
5. Should QBR endpoints share the same Flask app instance?
6. Should they use the same database connection pool?

---

## 9. Data Model Completeness

The data model defines tables but is missing some details.

**Questions**:
1. **Indexes**: Only `metrics_monthly` has indexes listed. Should we add indexes to:
   - `metrics_quarterly`?
   - `smartnumbers`?
   - `thresholds`?
   - `periods`?
2. **Constraints**: Should we add:
   - Unique constraints? (e.g., unique period + metric_name + organization_id)
   - Check constraints? (e.g., period format validation)
   - Not null constraints?
3. **Default Values**: Should we specify defaults?
   - `created_at` defaults to CURRENT_TIMESTAMP?
   - `is_active` defaults to TRUE?
4. **Foreign Keys**: Should we add explicit foreign key constraints?
   - `metrics_monthly.organization_id` → `organization.id`?
   - `metrics_monthly.period` → `periods.period_value`?

---

## 10. Metric Definitions and Formulas

The data model doesn't specify what metrics are collected or how they're calculated.

**Questions**:
1. **Complete Metric List**: What are ALL the metrics that will be collected?
   - From NinjaRMM: "Endpoints Managed" - confirmed
   - From ConnectWise: "Reactive Tickets Created", "Reactive Tickets Closed" - mentioned
   - From QuickBooks: What financial metrics?
   - Are there others?
2. **Metric Formulas**: How are derived metrics calculated?
   - Example: "Tickets per endpoint" = Reactive Tickets / Endpoints Managed
   - What other derived metrics exist?
3. **SmartNumbers Formulas**: How are SmartNumbers calculated?
   - "Net Revenue Retention" - what's the formula?
   - "Operational Efficiency" - what's the formula?
   - What other SmartNumbers exist?
4. **Source System Mapping**: For each metric, which source system provides it?
   - "Endpoints Managed" → NinjaOne
   - "Reactive Tickets Closed" → ConnectWise
   - "Monthly Recurring Revenue" → QuickBooks?

---

## 11. Data Collection Frequency

**Questions**:
1. How often should ConnectWise data be collected?
   - Daily? Weekly? Monthly? On-demand?
2. How often should QuickBooks data be collected?
   - Daily? Weekly? Monthly? On-demand?
3. How often should QBR metrics be aggregated/refreshed?
   - After each data collection?
   - Daily? Weekly? Monthly?
   - On-demand only?

---

## 12. Historical Data

**Questions**:
1. Do we need to collect historical data from ConnectWise and QuickBooks?
   - If yes, how far back? (1 year? 2 years?)
2. How do we handle historical periods that don't have data?
   - Show NULL/0?
   - Skip the period?
3. Should we backfill metrics for past periods?

---

## 13. Error Handling and Data Quality

**Questions**:
1. What happens if ConnectWise API is unavailable during refresh?
2. What happens if QuickBooks connection fails?
3. How do we handle partial data? (e.g., ConnectWise succeeds but QuickBooks fails)
4. Should we store error states in the database?
5. How do we handle data validation? (e.g., negative ticket counts, invalid dates)

---

## 14. Testing and Validation

**Questions**:
1. What test data should we use for development?
2. How do we test without affecting production data?
3. Should we have a separate test database?
4. How do we validate metric calculations are correct?

---

## Summary

These questions need to be answered to proceed with implementation. The highest priority items are:

1. **Organization Model** (#1) - Affects database schema design
2. **Metric Calculation Strategy** (#3) - Affects architecture and performance
3. **ConnectWise/QuickBooks Data Requirements** (#4) - Affects collector design
4. **Refresh Workflow** (#7) - Affects ETL design
5. **API Integration** (#8) - Affects implementation approach

---

**Next Steps**: Once these questions are answered, we can proceed with:
- Finalizing database schema
- Creating Alembic migrations
- Designing collector architecture
- Implementing API endpoints
- Building ETL workflows


# QBR System Implementation Guide

**Purpose**: Comprehensive implementation plan for the QBR (Quarterly Business Review) system

**Date**: January 2025

**Status**: 📋 **READY FOR IMPLEMENTATION**

---

## Table of Contents

1. [Overview](#overview)
2. [Implementation Phases](#implementation-phases)
3. [Phase 1: Database Foundation](#phase-1-database-foundation)
4. [Phase 2: Collector Development](#phase-2-collector-development)
5. [Phase 3: API Implementation](#phase-3-api-implementation)
6. [Phase 4: Testing & Validation](#phase-4-testing--validation)
7. [Phase 5: Production Deployment](#phase-5-production-deployment)
8. [Appendix: Technical Specifications](#appendix-technical-specifications)

---

## Overview

### System Purpose

The QBR System automates the collection, calculation, and presentation of business performance metrics across three data sources:
- **NinjaOne (RMM)**: Endpoint and device management data
- **ConnectWise Manage (PSA)**: Ticket and time tracking data
- **QuickBooks** (Future): Financial data

### Architecture Summary

```
┌─────────────────────────────────────────────────────────────┐
│                     QBR System Architecture                  │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Scheduled Collector (10:30pm CT)                            │
│         ↓                                                     │
│  ┌──────────────┐      ┌──────────────┐                    │
│  │ ConnectWise  │      │  NinjaOne    │                    │
│  │     API      │      │     API      │                    │
│  └──────┬───────┘      └──────┬───────┘                    │
│         │                     │                             │
│         └─────────┬───────────┘                             │
│                   ↓                                          │
│        ┌─────────────────────┐                              │
│        │  QBR Collector      │                              │
│        │  - Aggregate data   │                              │
│        │  - Calculate metrics│                              │
│        │  - Validate data    │                              │
│        └─────────┬───────────┘                              │
│                  ↓                                           │
│        ┌─────────────────────┐                              │
│        │  PostgreSQL         │                              │
│        │  qbr_* tables       │                              │
│        └─────────┬───────────┘                              │
│                  ↓                                           │
│        ┌─────────────────────┐                              │
│        │  Flask REST API     │                              │
│        │  /api/qbr/*         │                              │
│        └─────────┬───────────┘                              │
│                  ↓                                           │
│        ┌─────────────────────┐                              │
│        │  QBR Dashboard      │                              │
│        │  (Bootstrap+Chart.js│                              │
│        └─────────────────────┘                              │
└─────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

See `PLANNING_DECISIONS.md` for complete decision rationale. Key points:

- **Integration**: Same database, `qbr_` table prefix, Flask blueprint
- **Collection**: Daily at 10:30pm CT, 13 months (current + 12 historical)
- **Storage**: Pre-calculated metrics (not on-demand)
- **Manual Entry**: Support manual data entry for incomplete data
- **Testing**: Separate test database, 9-day validation before production

---

## Implementation Phases

### Phase Overview

| Phase | Focus | Duration Estimate | Dependencies |
|-------|-------|-------------------|--------------|
| **Phase 1** | Database Foundation | 2-3 days | None |
| **Phase 2** | Collector Development | 5-7 days | Phase 1 |
| **Phase 3** | API Implementation | 3-4 days | Phase 1, Phase 2 |
| **Phase 4** | Testing & Validation | 9+ days | Phase 1-3 |
| **Phase 5** | Production Deployment | 1-2 days | Phase 4 |

**Total Estimated Duration**: 20-25 days (calendar time, includes 9-day validation period)

---

## Phase 1: Database Foundation

### Objective

Create database schema for QBR tables in test environment, validate migrations.

### Tasks

#### 1.1 Create Test Database

```bash
# As postgres user
createdb -U postgres es_inventory_hub_test

# Copy schema from production
pg_dump -U postgres -s es_inventory_hub | psql -U postgres es_inventory_hub_test

# Verify tables copied
psql -U postgres -d es_inventory_hub_test -c "\dt"
```

**Expected Result**: Test database with all existing tables (vendor, site, device_snapshot, etc.)

#### 1.2 Add Vendors

```sql
-- Add ConnectWise and QuickBooks to vendor table
INSERT INTO vendor (id, name) VALUES (3, 'ConnectWise');
INSERT INTO vendor (id, name) VALUES (4, 'QuickBooks');
```

**Apply to**: Both test and production databases

#### 1.3 Create Alembic Migration

**Location**: `/opt/es-inventory-hub/storage/alembic/versions/`

**Migration File**: `YYYYMMDD_HHMMSS_create_qbr_tables.py`

**Tables to Create**:

1. **`organization`**
```sql
CREATE TABLE organization (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO organization (id, name) VALUES (1, 'Enersystems, LLC');
```

2. **`qbr_metrics_monthly`**
```sql
CREATE TABLE qbr_metrics_monthly (
    id SERIAL PRIMARY KEY,
    period VARCHAR(7) NOT NULL,  -- e.g., '2025-01'
    organization_id INTEGER NOT NULL REFERENCES organization(id),
    vendor_id INTEGER NOT NULL REFERENCES vendor(id),
    metric_name VARCHAR(100) NOT NULL,
    metric_value NUMERIC(12,2),
    data_source VARCHAR(20) DEFAULT 'collected',  -- 'collected' or 'manual'
    collected_at TIMESTAMPTZ,
    manually_entered_by VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_metrics_monthly_period_metric_org_vendor
        UNIQUE (period, metric_name, organization_id, vendor_id)
);

CREATE INDEX idx_qbr_metrics_monthly_period ON qbr_metrics_monthly(period);
CREATE INDEX idx_qbr_metrics_monthly_metric_name ON qbr_metrics_monthly(metric_name);
CREATE INDEX idx_qbr_metrics_monthly_org_id ON qbr_metrics_monthly(organization_id);
CREATE INDEX idx_qbr_metrics_monthly_vendor_id ON qbr_metrics_monthly(vendor_id);
CREATE INDEX idx_qbr_metrics_monthly_period_metric ON qbr_metrics_monthly(period, metric_name);
CREATE INDEX idx_qbr_metrics_monthly_data_source ON qbr_metrics_monthly(data_source);
```

3. **`qbr_metrics_quarterly`**
```sql
CREATE TABLE qbr_metrics_quarterly (
    id SERIAL PRIMARY KEY,
    period VARCHAR(7) NOT NULL,  -- e.g., '2025-Q1'
    organization_id INTEGER NOT NULL REFERENCES organization(id),
    metric_name VARCHAR(100) NOT NULL,
    metric_value NUMERIC(12,2),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_metrics_quarterly_period_metric_org
        UNIQUE (period, metric_name, organization_id)
);

CREATE INDEX idx_qbr_metrics_quarterly_period ON qbr_metrics_quarterly(period);
CREATE INDEX idx_qbr_metrics_quarterly_metric_name ON qbr_metrics_quarterly(metric_name);
CREATE INDEX idx_qbr_metrics_quarterly_org_id ON qbr_metrics_quarterly(organization_id);
```

4. **`qbr_smartnumbers`**
```sql
CREATE TABLE qbr_smartnumbers (
    id SERIAL PRIMARY KEY,
    period VARCHAR(7) NOT NULL,  -- e.g., '2025-01' or '2025-Q1'
    period_type VARCHAR(20) NOT NULL,  -- 'monthly' or 'quarterly'
    organization_id INTEGER NOT NULL REFERENCES organization(id),
    kpi_name VARCHAR(100) NOT NULL,
    kpi_value NUMERIC(12,4),
    calculation_method VARCHAR(200),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_smartnumbers_period_kpi_org
        UNIQUE (period, kpi_name, organization_id)
);

CREATE INDEX idx_qbr_smartnumbers_period ON qbr_smartnumbers(period);
CREATE INDEX idx_qbr_smartnumbers_kpi_name ON qbr_smartnumbers(kpi_name);
CREATE INDEX idx_qbr_smartnumbers_org_id ON qbr_smartnumbers(organization_id);
```

5. **`qbr_thresholds`**
```sql
CREATE TABLE qbr_thresholds (
    id SERIAL PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organization(id),
    metric_name VARCHAR(100) NOT NULL,
    threshold_type VARCHAR(20) NOT NULL,  -- 'warning' or 'critical'
    threshold_value NUMERIC(12,2),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_thresholds_metric_type_org
        UNIQUE (metric_name, threshold_type, organization_id)
);

CREATE INDEX idx_qbr_thresholds_metric_name ON qbr_thresholds(metric_name);
CREATE INDEX idx_qbr_thresholds_org_id ON qbr_thresholds(organization_id);
```

6. **`qbr_collection_log`**
```sql
CREATE TABLE qbr_collection_log (
    id SERIAL PRIMARY KEY,
    collection_started_at TIMESTAMPTZ NOT NULL,
    collection_ended_at TIMESTAMPTZ,
    period VARCHAR(7) NOT NULL,
    vendor_id INTEGER REFERENCES vendor(id),
    status VARCHAR(20) NOT NULL,  -- 'success', 'partial', 'failed'
    error_message TEXT,
    metrics_collected INTEGER,
    duration_seconds INTEGER,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_qbr_collection_log_started_at ON qbr_collection_log(collection_started_at);
CREATE INDEX idx_qbr_collection_log_period ON qbr_collection_log(period);
CREATE INDEX idx_qbr_collection_log_vendor_id ON qbr_collection_log(vendor_id);
CREATE INDEX idx_qbr_collection_log_status ON qbr_collection_log(status);
```

#### 1.4 Apply Migration to Test Database

```bash
cd /opt/es-inventory-hub
source .venv/bin/activate

# Apply migration to test database
PGDATABASE=es_inventory_hub_test alembic upgrade head

# Verify tables created
psql -U postgres -d es_inventory_hub_test -c "\dt qbr_*"
```

**Expected Result**: All 6 QBR tables exist in test database

#### 1.5 Validation

- [ ] Test database created successfully
- [ ] Vendors added (ConnectWise id=3, QuickBooks id=4)
- [ ] Alembic migration created
- [ ] Migration applied to test database without errors
- [ ] All QBR tables exist with correct schema
- [ ] Indexes created
- [ ] Unique constraints work (test duplicate insert fails)

---

## Phase 2: Collector Development

### Objective

Build QBR collector that gathers data from ConnectWise and NinjaOne, calculates metrics, and stores in database.

### Architecture

```
collectors/qbr/
├── __init__.py
├── collector.py           # Main collector orchestration
├── connectwise.py         # ConnectWise data collection
├── ninja.py               # NinjaOne data collection
├── calculator.py          # Metric calculation logic
├── validator.py           # Data validation
└── config.py              # Configuration

```

### Tasks

#### 2.1 Create Collector Structure

**Location**: `/opt/es-inventory-hub/collectors/qbr/`

**Files to Create**:
1. `__init__.py` - Package init
2. `collector.py` - Main orchestration
3. `connectwise.py` - ConnectWise integration
4. `ninja.py` - NinjaOne integration
5. `calculator.py` - Metrics calculation
6. `validator.py` - Data validation
7. `config.py` - Configuration

#### 2.2 ConnectWise Integration (`connectwise.py`)

**Purpose**: Collect reactive ticket metrics from ConnectWise

**Reuse**: Logic from `docs/qbr/shared/REACTIVE_TICKETS_FILTERING.md`

**Functions**:
```python
def get_tickets_created_for_period(period: str, timezone: str = 'America/Chicago') -> int:
    """Get count of reactive tickets created in period"""
    # Use existing pattern from REACTIVE_TICKETS_FILTERING.md
    pass

def get_tickets_closed_for_period(period: str, timezone: str = 'America/Chicago') -> int:
    """Get count of reactive tickets closed in period"""
    pass

def get_time_on_tickets_for_period(period: str, timezone: str = 'America/Chicago') -> float:
    """Get total hours spent on reactive tickets in period"""
    pass
```

**Integration Pattern**:
- Import existing ConnectWise API functions from main codebase
- Adapt to QBR period format (YYYY-MM)
- Handle timezone conversion using `utils.date_handling`

#### 2.3 NinjaOne Integration (`ninja.py`)

**Purpose**: Collect endpoint count metrics from NinjaOne

**Functions**:
```python
def get_endpoints_managed_for_period(period: str) -> int:
    """Get count of managed endpoints for period"""
    # Query device_snapshot table for period
    # Return count of distinct devices
    pass

def get_seats_managed_for_period(period: str) -> int:
    """Get count of managed seats for period"""
    # Similar to endpoints
    pass
```

**Data Source**: Query existing `device_snapshot` table

**SQL Pattern**:
```sql
-- Endpoints Managed for January 2025
SELECT COUNT(DISTINCT device_identity_id)
FROM device_snapshot
WHERE vendor_id = 2  -- Ninja
  AND snapshot_date = (
    SELECT MAX(snapshot_date)
    FROM device_snapshot
    WHERE vendor_id = 2
      AND snapshot_date >= '2025-01-01'
      AND snapshot_date <= '2025-01-31'
  );
```

#### 2.4 Calculator (`calculator.py`)

**Purpose**: Calculate SmartNumbers from collected metrics

**Functions**:
```python
def calculate_smartnumbers_for_period(period: str, metrics: Dict[str, float]) -> Dict[str, float]:
    """Calculate all SmartNumbers for a period"""
    # See CALCULATION_REFERENCE.md for formulas
    pass

# Individual calculation functions
def calc_tickets_per_tech_per_month(tickets_closed: int, tech_count: int, months: int = 3) -> float:
    """Reactive Tickets / Tech / Month (closed)"""
    return tickets_closed / tech_count / months if tech_count > 0 else 0

def calc_total_close_percentage(tickets_closed: int, tickets_created: int) -> float:
    """Total Close %"""
    return tickets_closed / tickets_created if tickets_created > 0 else 0

# ... etc for all 18 SmartNumbers
```

**Reference**: See `CALCULATION_REFERENCE.md` for all formulas

#### 2.5 Validator (`validator.py`)

**Purpose**: Validate collected data before storing

**Functions**:
```python
def validate_metric(metric_name: str, metric_value: float, period: str) -> ValidationResult:
    """Validate a single metric"""
    pass

class ValidationResult:
    is_valid: bool
    is_suspicious: bool
    error_message: str = None
    warning_message: str = None
```

**Validation Rules**:
```python
# Negative values
if metric_value < 0 and metric_name in ['tickets_created', 'tickets_closed', 'hours', 'endpoints']:
    return ValidationResult(is_valid=False, error_message="Negative value not allowed")

# Zero values (suspicious)
if metric_value == 0 and metric_name == 'endpoints_managed':
    return ValidationResult(is_valid=True, is_suspicious=True, warning_message="Zero endpoints")

# Dramatic changes
previous_value = get_previous_month_value(metric_name, period)
if previous_value:
    change_pct = abs((metric_value - previous_value) / previous_value)
    if change_pct > 0.50:  # 50% change
        return ValidationResult(is_valid=True, is_suspicious=True,
            warning_message=f"{change_pct*100:.0f}% change from previous month")
```

#### 2.6 Main Collector (`collector.py`)

**Purpose**: Orchestrate collection, calculation, and storage

**Main Function**:
```python
def run_qbr_collection(
    periods: List[str] = None,
    database_dsn: str = None,
    timezone: str = 'America/Chicago'
):
    """
    Main QBR collection function

    Args:
        periods: List of periods to collect (e.g., ['2025-01', '2024-12'])
                If None, collects current month + last 12 months (13 total)
        database_dsn: Database connection string (defaults to config)
        timezone: Timezone for date calculations
    """

    # 1. Determine periods to collect
    if periods is None:
        periods = get_periods_to_collect(timezone)  # Current + 12 historical

    # 2. For each period
    for period in periods:
        log_start = datetime.now(timezone='UTC')

        try:
            # 3. Collect ConnectWise data
            cw_metrics = collect_connectwise_metrics(period, timezone)

            # 4. Collect NinjaOne data
            ninja_metrics = collect_ninja_metrics(period)

            # 5. Combine metrics
            all_metrics = {**cw_metrics, **ninja_metrics}

            # 6. Validate metrics
            validation_results = validate_all_metrics(all_metrics, period)

            # 7. Store metrics (skip manually-entered ones)
            store_metrics(period, all_metrics, validation_results, database_dsn)

            # 8. Calculate SmartNumbers
            smartnumbers = calculate_smartnumbers_for_period(period, all_metrics)

            # 9. Store SmartNumbers
            store_smartnumbers(period, smartnumbers, database_dsn)

            # 10. Log success
            log_collection_success(period, log_start, len(all_metrics), database_dsn)

        except Exception as e:
            # Log failure
            log_collection_failure(period, log_start, str(e), database_dsn)
            raise
```

**Retry Logic** (for ConnectWise API failures):
```python
@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    retry=retry_if_exception_type((requests.exceptions.RequestException, TimeoutError))
)
def collect_connectwise_metrics(period: str, timezone: str) -> Dict[str, float]:
    """Collect ConnectWise metrics with retry logic"""
    pass
```

#### 2.7 Scheduled Execution

**Method**: systemd timer

**Location**: `/etc/systemd/system/qbr-collector.timer` and `/etc/systemd/system/qbr-collector.service`

**Timer File** (`qbr-collector.timer`):
```ini
[Unit]
Description=QBR Collector Daily Timer
Requires=qbr-collector.service

[Timer]
# Run daily at 10:30pm Central Time
# Note: systemd timers use system timezone
OnCalendar=22:30
Persistent=true

[Install]
WantedBy=timers.target
```

**Service File** (`qbr-collector.service`):
```ini
[Unit]
Description=QBR Collector Service
After=network.target postgresql.service

[Service]
Type=oneshot
User=rene
Group=rene
WorkingDirectory=/opt/es-inventory-hub
Environment="PATH=/opt/es-inventory-hub/.venv/bin:/usr/bin"
Environment="PGDATABASE=es_inventory_hub"
ExecStart=/opt/es-inventory-hub/.venv/bin/python -m collectors.qbr.collector
StandardOutput=append:/var/log/qbr-collector.log
StandardError=append:/var/log/qbr-collector.log

[Install]
WantedBy=multi-user.target
```

**Enable Timer**:
```bash
sudo systemctl daemon-reload
sudo systemctl enable qbr-collector.timer
# Don't start yet - wait for validation
```

#### 2.8 Testing on Test Database

**Test Script**: `collectors/qbr/test_collector.py`

```python
def test_collector_on_test_db():
    """Test collector against test database"""

    # Use test database DSN
    test_dsn = "postgresql://postgres:mK2D282lRrs6bTpXWe7@localhost/es_inventory_hub_test"

    # Test single month
    run_qbr_collection(periods=['2025-01'], database_dsn=test_dsn)

    # Verify data stored
    # Assert metrics exist
    # Assert smartnumbers calculated
```

#### 2.9 Validation

- [ ] Collector structure created
- [ ] ConnectWise integration working (real API calls)
- [ ] NinjaOne integration working (queries device_snapshot)
- [ ] Calculator produces correct SmartNumbers
- [ ] Validator catches negative values, flags suspicious data
- [ ] Main collector runs end-to-end on test database
- [ ] Retry logic tested (simulate API failures)
- [ ] Collection log entries created
- [ ] Systemd timer/service files created (not enabled yet)

---

## Phase 3: API Implementation

### Objective

Add QBR REST API endpoints to existing API server.

### Architecture

```
api/
├── api_server.py       # Main API server (existing)
├── qbr_api.py          # New: QBR Blueprint
└── ...
```

### Tasks

#### 3.1 Create QBR Blueprint (`api/qbr_api.py`)

**Structure**:
```python
from flask import Blueprint, jsonify, request
from sqlalchemy import text

qbr_bp = Blueprint('qbr', __name__, url_prefix='/api/qbr')

@qbr_bp.route('/metrics/monthly', methods=['GET'])
def get_monthly_metrics():
    """GET /api/qbr/metrics/monthly?period=2025-01&organization_id=1"""
    pass

@qbr_bp.route('/metrics/quarterly', methods=['GET'])
def get_quarterly_metrics():
    """GET /api/qbr/metrics/quarterly?period=2025-Q1&organization_id=1"""
    pass

@qbr_bp.route('/smartnumbers', methods=['GET'])
def get_smartnumbers():
    """GET /api/qbr/smartnumbers?period=2025-01&organization_id=1"""
    pass

@qbr_bp.route('/thresholds', methods=['GET'])
def get_thresholds():
    """GET /api/qbr/thresholds"""
    pass

@qbr_bp.route('/thresholds', methods=['POST'])
def update_thresholds():
    """POST /api/qbr/thresholds"""
    pass

@qbr_bp.route('/metrics/manual', methods=['POST'])
def manual_entry():
    """POST /api/qbr/metrics/manual (for manual data entry)"""
    pass
```

#### 3.2 Register Blueprint in Main API Server

**Edit**: `api/api_server.py`

```python
# Add import
from api.qbr_api import qbr_bp

# Register blueprint
app.register_blueprint(qbr_bp)
```

#### 3.3 Implement Endpoints

**Response Format Helper**:
```python
def success_response(data):
    """Standard success response"""
    return jsonify({
        "success": True,
        "data": data
    }), 200

def error_response(code, message, status=400):
    """Standard error response"""
    return jsonify({
        "success": False,
        "error": {
            "code": code,
            "message": message,
            "status": status
        }
    }), status
```

**Example Endpoint Implementation**:
```python
@qbr_bp.route('/metrics/monthly', methods=['GET'])
def get_monthly_metrics():
    """Get monthly metrics for a period"""

    # Get parameters
    period = request.args.get('period')
    organization_id = request.args.get('organization_id', 1, type=int)
    vendor_id = request.args.get('vendor_id', type=int)
    metric_name = request.args.get('metric_name')

    # Validate period format
    if not period or not re.match(r'^\d{4}-\d{2}$', period):
        return error_response('INVALID_PERIOD', 'Period format must be YYYY-MM')

    # Build query
    query = """
        SELECT
            period,
            metric_name,
            metric_value,
            vendor_id,
            data_source,
            created_at
        FROM qbr_metrics_monthly
        WHERE period = :period
          AND organization_id = :organization_id
    """
    params = {'period': period, 'organization_id': organization_id}

    if vendor_id:
        query += " AND vendor_id = :vendor_id"
        params['vendor_id'] = vendor_id

    if metric_name:
        query += " AND metric_name = :metric_name"
        params['metric_name'] = metric_name

    query += " ORDER BY metric_name"

    # Execute query
    with get_session() as session:
        result = session.execute(text(query), params)
        rows = result.fetchall()

    # Check if period exists
    if not rows:
        return error_response('PERIOD_NOT_FOUND', f'No data found for period {period}', 404)

    # Format response
    metrics = []
    for row in rows:
        metrics.append({
            'name': row.metric_name,
            'value': float(row.metric_value) if row.metric_value else None,
            'vendor_id': row.vendor_id,
            'source': row.data_source,
            'collected_at': row.created_at.isoformat() if row.created_at else None
        })

    return success_response({
        'period': period,
        'metrics': metrics
    })
```

#### 3.4 Manual Data Entry Endpoint

```python
@qbr_bp.route('/metrics/manual', methods=['POST'])
def manual_entry():
    """
    Manual data entry endpoint

    Request body:
    {
        "period": "2025-01",
        "organization_id": 1,
        "vendor_id": 3,
        "metric_name": "Reactive Tickets Created",
        "metric_value": 350,
        "entered_by": "admin",
        "notes": "Manual entry due to API outage"
    }
    """
    data = request.get_json()

    # Validate required fields
    required = ['period', 'metric_name', 'metric_value', 'entered_by']
    for field in required:
        if field not in data:
            return error_response('MISSING_FIELD', f'Missing required field: {field}')

    # Insert or update
    query = """
        INSERT INTO qbr_metrics_monthly
            (period, organization_id, vendor_id, metric_name, metric_value,
             data_source, manually_entered_by, notes, created_at, updated_at)
        VALUES
            (:period, :organization_id, :vendor_id, :metric_name, :metric_value,
             'manual', :entered_by, :notes, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ON CONFLICT (period, metric_name, organization_id, vendor_id)
        DO UPDATE SET
            metric_value = EXCLUDED.metric_value,
            data_source = 'manual',
            manually_entered_by = EXCLUDED.manually_entered_by,
            notes = EXCLUDED.notes,
            updated_at = CURRENT_TIMESTAMP
    """

    with get_session() as session:
        session.execute(text(query), {
            'period': data['period'],
            'organization_id': data.get('organization_id', 1),
            'vendor_id': data.get('vendor_id'),
            'metric_name': data['metric_name'],
            'metric_value': data['metric_value'],
            'entered_by': data['entered_by'],
            'notes': data.get('notes')
        })
        session.commit()

    return success_response({
        'message': 'Metric entered successfully',
        'period': data['period'],
        'metric_name': data['metric_name']
    })
```

#### 3.5 Testing API Endpoints

**Test Script**: `api/test_qbr_api.py`

```python
import requests

BASE_URL = 'http://localhost:5400'

def test_monthly_metrics():
    """Test GET /api/qbr/metrics/monthly"""
    response = requests.get(f'{BASE_URL}/api/qbr/metrics/monthly?period=2025-01')
    assert response.status_code == 200
    data = response.json()
    assert data['success'] == True
    assert 'metrics' in data['data']

def test_manual_entry():
    """Test POST /api/qbr/metrics/manual"""
    payload = {
        'period': '2025-01',
        'metric_name': 'Test Metric',
        'metric_value': 100,
        'entered_by': 'test_user',
        'notes': 'Test entry'
    }
    response = requests.post(f'{BASE_URL}/api/qbr/metrics/manual', json=payload)
    assert response.status_code == 200
```

#### 3.6 Validation

- [ ] QBR blueprint created
- [ ] Blueprint registered in main API server
- [ ] All 6 endpoints implemented
- [ ] Response format standardized (success/error wrappers)
- [ ] Query parameter validation working
- [ ] Manual data entry endpoint working
- [ ] Error responses return correct status codes
- [ ] Tested against test database
- [ ] API documentation updated

---

## Phase 4: Testing & Validation

### Objective

Validate QBR system works correctly before production deployment.

### Duration

**9+ days** (9-day consecutive daily update validation)

### Tasks

#### 4.1 Historical Data Validation

**Objective**: Validate all 2024-2025 historical months

**Process**:
1. Run collector for all months Jan 2024 - Current Month
2. Export metrics to CSV/Excel
3. Manually review against:
   - Existing Excel QBR spreadsheet (if accurate)
   - ConnectWise reports
   - NinjaOne reports
4. Identify discrepancies
5. Fix calculation bugs if found
6. Re-run collection for affected months

**Checklist**:
- [ ] All months Jan 2024 - Dec 2024 collected
- [ ] All months Jan 2025 - Current collected
- [ ] Metrics match expected values (spot-check key metrics)
- [ ] SmartNumbers calculated correctly
- [ ] No obvious data quality issues

#### 4.2 Current Month Daily Updates (9 Days)

**Objective**: Validate current month updates correctly each day

**Process**:
1. Enable collector timer (daily 10:30pm)
2. For 9 consecutive days:
   - Verify collector runs successfully
   - Verify current month metrics update
   - Verify previous months remain unchanged
   - Check collection log for errors
   - Review any flagged suspicious data
3. Document any issues encountered

**Daily Checklist** (repeat 9 times):
- [ ] Day N: Collector ran at 10:30pm CT
- [ ] Day N: Current month metrics updated
- [ ] Day N: Historical months unchanged
- [ ] Day N: No errors in collection log
- [ ] Day N: Suspicious data reviewed (if any)

#### 4.3 Manual Data Entry Testing

**Objective**: Validate manual data entry workflow

**Test Cases**:
1. **New manual entry**: Enter metric for period with no existing data
2. **Override collected data**: Enter manual value to override collected metric
3. **Collector respects manual**: Verify collector skips manually-entered metrics
4. **Re-collection**: Change data_source back to 'collected', verify collector updates

**Checklist**:
- [ ] Can enter new manual metric via API
- [ ] Can override collected metric
- [ ] Collector skips manual metrics
- [ ] Can flag metric for re-collection
- [ ] Manual entry audit trail works (manually_entered_by, notes)

#### 4.4 Error Handling Testing

**Objective**: Validate error handling and recovery

**Test Scenarios**:
1. **ConnectWise API down**: Simulate API failure, verify retry logic
2. **Invalid data returned**: Return suspicious data (zero tickets), verify flagging
3. **Database connection lost**: Simulate DB failure, verify error logging
4. **Partial month data**: Incomplete month, verify handling

**Checklist**:
- [ ] Retry logic works (3-5 attempts with backoff)
- [ ] Suspicious data flagged correctly
- [ ] Errors logged to qbr_collection_log
- [ ] Dashboard indicator shows errors
- [ ] Log file contains detailed error info

#### 4.5 SmartNumbers Calculation Verification

**Objective**: Validate all 18 SmartNumbers calculated correctly

**Process**:
1. Export one month's metrics and SmartNumbers
2. Manually calculate each SmartNumber using formulas from CALCULATION_REFERENCE.md
3. Compare manual calculations to stored values
4. Identify any discrepancies
5. Fix calculation bugs
6. Re-run calculation

**SmartNumbers to Verify**:
- [ ] Reactive Tickets / Tech / Month (closed)
- [ ] Total Close %
- [ ] Reactive Tickets / Endpoint / Month (new)
- [ ] RHEM (Reactive Hours / Endpoint / Month)
- [ ] Average Resolution Time
- [ ] Reactive Service %
- [ ] Net Profit %
- [ ] % of Revenue from Services
- [ ] % of Services from MRR
- [ ] Annualized Service Revenue / Employee
- [ ] Annualized Service Revenue / Technical Employee
- [ ] Average AISP
- [ ] Average MRR
- [ ] New MRR added
- [ ] Lost MRR (churn)
- [ ] Net MRR gain
- [ ] # of dials / appointment
- [ ] Sales Call Close %

#### 4.6 API Testing

**Objective**: Validate all API endpoints work correctly

**Test Cases**:
- [ ] GET /api/qbr/metrics/monthly with valid period
- [ ] GET /api/qbr/metrics/monthly with invalid period (400 error)
- [ ] GET /api/qbr/metrics/monthly with non-existent period (404 error)
- [ ] GET /api/qbr/metrics/monthly with filters (vendor_id, metric_name)
- [ ] GET /api/qbr/metrics/quarterly
- [ ] GET /api/qbr/smartnumbers
- [ ] GET /api/qbr/thresholds
- [ ] POST /api/qbr/thresholds
- [ ] POST /api/qbr/metrics/manual
- [ ] Verify CORS headers work for dashboard

#### 4.7 Performance Testing

**Objective**: Ensure acceptable performance

**Metrics**:
- [ ] Collector runtime: <5 minutes for 13-month collection
- [ ] API response time: <500ms for monthly metrics
- [ ] API response time: <1s for quarterly metrics
- [ ] Database query performance acceptable

#### 4.8 Documentation Review

**Objective**: Ensure all documentation is complete and accurate

**Checklist**:
- [ ] PLANNING_DECISIONS.md accurate
- [ ] IMPLEMENTATION_GUIDE.md accurate
- [ ] CALCULATION_REFERENCE.md complete
- [ ] API documentation updated
- [ ] README.md updated

---

## Phase 5: Production Deployment

### Objective

Deploy QBR system to production database.

### Prerequisites

- [ ] All Phase 4 validation complete
- [ ] 9-day consecutive daily update validation successful
- [ ] User approval to proceed

### Tasks

#### 5.1 Production Database Migration

**Apply Alembic Migration**:
```bash
cd /opt/es-inventory-hub
source .venv/bin/activate

# Backup production database first
pg_dump -U postgres es_inventory_hub > /tmp/es_inventory_hub_backup_$(date +%Y%m%d).sql

# Apply migration
alembic upgrade head

# Verify tables created
psql -U postgres -d es_inventory_hub -c "\dt qbr_*"
```

**Expected Result**: All 6 QBR tables exist in production database

#### 5.2 Manual Initial Backfill

**Do NOT enable timer yet**. Run initial collection manually:

```bash
cd /opt/es-inventory-hub
source .venv/bin/activate

# Run collector manually for all periods
python -m collectors.qbr.collector

# Monitor log
tail -f /var/log/qbr-collector.log
```

**Wait for completion** (may take 10-15 minutes for 13 months)

#### 5.3 Review Initial Results

**Check Data**:
```sql
-- Count metrics per period
SELECT period, COUNT(*) as metric_count
FROM qbr_metrics_monthly
GROUP BY period
ORDER BY period DESC;

-- Check for errors
SELECT *
FROM qbr_collection_log
WHERE status != 'success'
ORDER BY collection_started_at DESC;

-- Verify smartnumbers calculated
SELECT period, COUNT(*) as kpi_count
FROM qbr_smartnumbers
GROUP BY period
ORDER BY period DESC;
```

**Manual Review**:
- [ ] All expected periods have data
- [ ] Metric counts look reasonable (~40-50 per period)
- [ ] No unexpected errors in collection log
- [ ] SmartNumbers calculated for all periods
- [ ] Spot-check a few key metrics against expectations

#### 5.4 User Approval

Present results to user for approval:
- Show sample data from key periods
- Show any errors or warnings
- Show suspicious data flagged for review
- Get explicit approval to enable daily schedule

**Decision Point**: If user approves, proceed. If not, investigate issues and re-run.

#### 5.5 Enable Daily Schedule

**Only after user approval**:

```bash
# Enable and start timer
sudo systemctl enable qbr-collector.timer
sudo systemctl start qbr-collector.timer

# Verify timer active
sudo systemctl status qbr-collector.timer
systemctl list-timers qbr-collector.timer
```

**Expected Output**:
```
NEXT                          LEFT       LAST PASSED UNIT                  ACTIVATES
Tue 2025-01-21 22:30:00 CST  2h 15min   -    -      qbr-collector.timer   qbr-collector.service
```

#### 5.6 Monitor First Week

**Daily for 7 days**:
- [ ] Verify collector runs at 10:30pm
- [ ] Check collection log for errors
- [ ] Review current month metrics
- [ ] Check for flagged suspicious data
- [ ] Verify dashboard displays correctly

#### 5.7 Production Validation Complete

- [ ] Production database migration successful
- [ ] Initial backfill completed and reviewed
- [ ] User approved results
- [ ] Daily schedule enabled
- [ ] First week monitoring complete
- [ ] System running reliably

---

## Appendix: Technical Specifications

### Database Schema

See Phase 1, Section 1.3 for complete schema definitions.

### API Endpoints

See Phase 3, Section 3.1 for endpoint specifications.

### Calculation Formulas

See `CALCULATION_REFERENCE.md` for all metric and SmartNumber formulas.

### Configuration

**Environment Variables**:
```bash
# Database
PGDATABASE=es_inventory_hub
PGUSER=postgres
PGPASSWORD=mK2D282lRrs6bTpXWe7
PGHOST=localhost
PGPORT=5432

# QBR Settings
QBR_TIMEZONE=America/Chicago
QBR_COLLECTION_ENABLED=true
QBR_MONTHS_TO_COLLECT=13

# Logging
QBR_LOG_FILE=/var/log/qbr-collector.log
QBR_LOG_LEVEL=INFO
```

### Dependencies

**Python Packages** (add to requirements.txt):
```
flask>=2.3.0
flask-cors>=4.0.0
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.0
alembic>=1.12.0
requests>=2.31.0
tenacity>=8.2.0  # For retry logic
pytz>=2023.3
```

### File Locations

```
/opt/es-inventory-hub/
├── collectors/qbr/          # QBR collector
├── api/qbr_api.py           # QBR API blueprint
├── storage/alembic/versions/  # Database migrations
├── docs/qbr/                # Documentation
└── .venv/                   # Python virtual environment

/var/log/
└── qbr-collector.log        # Collector log file

/etc/systemd/system/
├── qbr-collector.service    # Collector service
└── qbr-collector.timer      # Daily timer
```

---

## Summary

This implementation guide provides a complete roadmap for building the QBR system. Follow the phases in order, complete all validation steps, and obtain user approval before enabling production collection.

**Estimated Total Timeline**: 20-25 days

**Key Success Criteria**:
- ✅ All QBR tables created and populated
- ✅ Collector runs reliably daily at 10:30pm CT
- ✅ 13 months of data (current + 12 historical)
- ✅ All SmartNumbers calculated correctly
- ✅ API endpoints functional
- ✅ Manual data entry working
- ✅ Error handling robust
- ✅ User validated and approved

---

---

**Version**: v1.21.0
**Last Updated**: November 13, 2025 03:24 UTC
**Maintainer**: ES Inventory Hub Team
**Status**: Ready for Implementation
**Next Document**: CALCULATION_REFERENCE.md

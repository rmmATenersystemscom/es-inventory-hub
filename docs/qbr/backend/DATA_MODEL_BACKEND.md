# QBR Web Dashboard – Backend Data Model

## About This Document
This document defines the proposed **PostgreSQL data model** for the QBR Web Dashboard backend.  
It is intended for **Database AI** to implement the schema via SQLAlchemy + Alembic migrations.  
It also serves as a contract reference for **Dashboard AI**, ensuring consistent API field names.

---

## Overview
The backend stores time-based business performance data (operations, financials, and KPIs) gathered from ConnectWise, NinjaOne, and QuickBooks.  
All metrics are recorded per period (month/quarter) and organization.

---

## Table: `metrics_monthly`
| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL PK | Unique record ID |
| `period` | VARCHAR(7) | e.g., `2025-01` |
| `organization_id` | INTEGER FK | Organization link |
| `metric_name` | VARCHAR(100) | e.g., `Reactive Tickets Closed` |
| `metric_value` | NUMERIC(12,2) | Actual metric value |
| `source_system` | VARCHAR(50) | e.g., `ConnectWise`, `NinjaOne`, `QuickBooks` |
| `created_at` | TIMESTAMPTZ | Record creation time |

Indexes: (`period`, `metric_name`), (`organization_id`, `period`)

---

## Table: `metrics_quarterly`
| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL PK |
| `period` | VARCHAR(7) | e.g., `2025-Q1` |
| `organization_id` | INTEGER FK |
| `metric_name` | VARCHAR(100) |
| `metric_value` | NUMERIC(12,2) |
| `created_at` | TIMESTAMPTZ |

---

## Table: `smartnumbers`
| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL PK |
| `period` | VARCHAR(7) |
| `kpi_name` | VARCHAR(100) | e.g., `Profit Margin` |
| `kpi_value` | NUMERIC(12,2) |
| `calculation_method` | VARCHAR(200) | e.g., formula |
| `organization_id` | INTEGER FK |
| `created_at` | TIMESTAMPTZ |

---

## Table: `thresholds`
| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL PK |
| `metric_name` | VARCHAR(100) |
| `threshold_type` | VARCHAR(20) | `warning` or `critical` |
| `threshold_value` | NUMERIC(12,2) |
| `organization_id` | INTEGER FK |
| `updated_at` | TIMESTAMPTZ |

---

## Table: `periods`
| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL PK |
| `period_type` | VARCHAR(20) | `monthly` or `quarterly` |
| `period_value` | VARCHAR(7) | e.g., `2025-01` |
| `start_date` | DATE |
| `end_date` | DATE |
| `is_active` | BOOLEAN |

---

## Relationships
- `metrics_monthly` → `periods.period_value`
- `metrics_quarterly` → `periods.period_value`
- `smartnumbers` → `periods.period_value`
- `thresholds.metric_name` maps to metrics.

---

## Example Query
```sql
SELECT metric_name, metric_value
FROM metrics_monthly
WHERE period = '2025-01';
```

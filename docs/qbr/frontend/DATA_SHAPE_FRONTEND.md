# QBR Web Dashboard – Data Shape Summary (Frontend API Reference)

## About This Document
This file defines the **JSON structures** returned by the backend API,  
so that **Dashboard AI** can consume and visualize data consistently.

---

## Monthly Metrics
`GET /api/qbr/metrics/monthly?period=2025-01`
```json
{
  "period": "2025-01",
  "metrics": [
    {"name": "Endpoints Managed", "value": 762, "source": "NinjaOne"},
    {"name": "Reactive Tickets Created", "value": 134, "source": "ConnectWise"}
  ]
}
```

---

## Quarterly Metrics
`GET /api/qbr/metrics/quarterly?period=2025-Q1`
```json
{
  "period": "2025-Q1",
  "metrics": [
    {"name": "Endpoints Managed", "average": 758.3},
    {"name": "Total Time on Reactive Tickets (hrs)", "sum": 543.8}
  ]
}
```

---

## SmartNumbers
`GET /api/qbr/smartnumbers`
```json
{
  "period": "2025-01",
  "smartnumbers": [
    {"kpi": "Net Revenue Retention", "value": 98.7, "unit": "%"},
    {"kpi": "Operational Efficiency", "value": 92.4, "unit": "%"}
  ]
}
```

---

## Thresholds
`GET /api/qbr/thresholds`
```json
{
  "thresholds": [
    {"metric": "Reactive Tickets Closed", "warning": 150, "critical": 100},
    {"metric": "Endpoints Managed", "warning": 600, "critical": 500}
  ]
}
```

---

## Refresh
`POST /api/qbr/refresh`
```json
{"batch_id": "bc_abc123", "status": "queued"}
```
`GET /api/qbr/refresh/status/bc_abc123`
```json
{"batch_id": "bc_abc123", "status": "running", "progress": 63}
```

---

## Periods
`GET /api/qbr/periods`
```json
{
  "periods": [
    {"period": "2025-01", "type": "monthly", "start_date": "2025-01-01", "end_date": "2025-01-31"},
    {"period": "2025-Q1", "type": "quarterly", "start_date": "2025-01-01", "end_date": "2025-03-31"}
  ]
}
```

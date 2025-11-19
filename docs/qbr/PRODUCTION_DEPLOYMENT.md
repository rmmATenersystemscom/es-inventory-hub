# QBR System - Production Deployment Guide

**Version**: v1.22.0
**Deployed**: November 15, 2025
**Status**: ✅ PRODUCTION ACTIVE

---

## Deployment Summary

The QBR (Quarterly Business Review) system is now **fully deployed and operational** in production.

**What's Running:**
- ✅ Automated daily collection at 10:30 PM Central Time
- ✅ NinjaOne metrics collection (endpoints, seats)
- ✅ ConnectWise metrics collection (tickets, time entries)
- ✅ REST API with 6 endpoints
- ✅ SmartNumbers calculator (18 KPIs)
- ✅ Manual metrics entry system
- ✅ 23 months of historical data (2024-01 through 2025-11)

---

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Systemd Timer (Daily 10:30 PM CT)          │
│                 qbr-collector.timer                      │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│              QBR Master Collector                        │
│           collectors/qbr/collect_all.py                  │
└──────────┬─────────────────────────┬────────────────────┘
           │                         │
           ▼                         ▼
┌──────────────────┐      ┌──────────────────┐
│  NinjaOne        │      │  ConnectWise     │
│  Collector       │      │  Collector       │
│  (7s runtime)    │      │  (15s runtime)   │
└────────┬─────────┘      └────────┬─────────┘
         │                         │
         └─────────┬───────────────┘
                   ▼
     ┌─────────────────────────────┐
     │   PostgreSQL Database        │
     │   qbr_metrics_monthly        │
     └──────────────┬───────────────┘
                    │
                    ▼
          ┌──────────────────┐
          │   QBR REST API    │
          │   6 Endpoints     │
          └──────────────────┘
```

---

## Production Configuration

### Systemd Timer Schedule
- **Service**: `qbr-collector.service`
- **Timer**: `qbr-collector.timer`
- **Schedule**: Daily at 10:30 PM America/Chicago
- **Persistence**: Yes (runs missed jobs on boot)
- **Next Run**: Check with `systemctl list-timers qbr-collector.timer`

### Environment Variables
Located in: `/opt/es-inventory-hub/.env`

```bash
CONNECTWISE_SERVER=https://helpme.enersystems.com
CONNECTWISE_COMPANY_ID=enersystems
CONNECTWISE_CLIENT_ID=5aa0e7b6-5500-48fb-90a8-8410802df04c
CONNECTWISE_PUBLIC_KEY=s9QF8u12JFPE22R7
CONNECTWISE_PRIVATE_KEY=vgo8s3P0mvpnPXBn
DB_DSN=postgresql://postgres:***@localhost:5432/es_inventory_hub
```

⚠️ **Security**: `.env` file has 600 permissions (owner read/write only)

### Database Tables
- `qbr_metrics_monthly` - Monthly metric storage
- `qbr_smartnumbers` - Calculated KPIs (future use)
- `qbr_thresholds` - Performance thresholds
- `qbr_collection_log` - Collection history (future use)

---

## Monitoring the System

### Check Timer Status

```bash
# View timer status
systemctl status qbr-collector.timer

# List next scheduled run
systemctl list-timers qbr-collector.timer

# Expected output:
# NEXT: Sat 2025-11-16 22:30:00 CST
```

### Check Last Collection

```bash
# View service logs from last run
sudo journalctl -u qbr-collector.service --since "24 hours ago" --no-pager

# View service status
sudo systemctl status qbr-collector.service
```

### Check Collected Data

```bash
# View latest metrics for current month
PGPASSWORD='mK2D282lRrs6bTpXWe7' psql -h localhost -U postgres -d es_inventory_hub -c "
SELECT
    metric_name,
    metric_value,
    vendor_id,
    data_source,
    TO_CHAR(updated_at, 'YYYY-MM-DD HH24:MI') as last_updated
FROM qbr_metrics_monthly
WHERE period = TO_CHAR(CURRENT_DATE, 'YYYY-MM')
ORDER BY vendor_id NULLS LAST, metric_name;
"
```

Expected output:
```
       metric_name        | metric_value | vendor_id | data_source | last_updated
--------------------------+--------------+-----------+-------------+---------------
 endpoints_managed        |       579.00 |         2 | collected   | 2025-11-15 21:36
 seats_managed            |       524.00 |         2 | collected   | 2025-11-15 21:36
 reactive_tickets_closed  |       136.00 |         3 | collected   | 2025-11-15 21:36
 reactive_tickets_created |       142.00 |         3 | collected   | 2025-11-15 21:36
 reactive_time_spent      |        78.75 |         3 | collected   | 2025-11-15 21:36
```

---

## Manual Operations

### Run Collection Manually

```bash
# Trigger immediate collection (doesn't affect scheduled run)
sudo systemctl start qbr-collector.service

# Wait for completion and check status
sleep 10
sudo systemctl status qbr-collector.service
```

### Stop Automatic Collection

```bash
# Temporarily stop timer (until next reboot)
sudo systemctl stop qbr-collector.timer

# Permanently disable timer
sudo systemctl disable qbr-collector.timer
sudo systemctl stop qbr-collector.timer
```

### Re-enable Automatic Collection

```bash
sudo systemctl enable qbr-collector.timer
sudo systemctl start qbr-collector.timer
```

---

## Adding Manual Metrics

Use the REST API to add manual metrics (revenue, employees, sales data):

```bash
# Example: Add employee counts for current month
curl -X POST "http://localhost:5400/api/qbr/metrics/manual" \
  -H "Content-Type: application/json" \
  -d '{
    "period": "2025-11",
    "organization_id": 1,
    "metrics": [
      {
        "metric_name": "employees",
        "metric_value": 8.5,
        "notes": "Total headcount including part-time"
      },
      {
        "metric_name": "technical_employees",
        "metric_value": 5.5,
        "notes": "Technical staff only"
      }
    ]
  }'
```

**Available Manual Metrics:**
- **Company**: employees, technical_employees, agreements
- **Revenue**: mrr, nrr, orr, total_revenue, product_sales, misc_revenue
- **Expenses**: employee_expense, owner_comp, owner_comp_taxes, product_cogs, other_expenses, total_expenses, net_profit
- **Sales**: telemarketing_dials, first_time_appointments, prospects_to_pbr, new_agreements, new_mrr, lost_mrr

See `/opt/es-inventory-hub/docs/qbr/QBR_API_DOCUMENTATION.md` for full API details.

---

## Accessing API Endpoints

Base URL: `http://localhost:5400` (or `https://db-api.enersystems.com:5400`)

### Get Monthly Metrics

```bash
curl "http://localhost:5400/api/qbr/metrics/monthly?period=2025-11"
```

### Get Quarterly Metrics

```bash
curl "http://localhost:5400/api/qbr/metrics/quarterly?period=2025-Q4"
```

### Calculate SmartNumbers

```bash
curl "http://localhost:5400/api/qbr/smartnumbers?period=2025-Q4"
```

**Returns 18 KPIs:**
- Operations (6): tickets per tech, close %, RHEM, resolution time, etc.
- Profit (1): net profit %
- Revenue (2): revenue mix, services from MRR %
- Leverage (4): revenue per employee, AISP, MRR per agreement
- Sales (5): new MRR, lost MRR, net gain, dials per appointment, close %

---

## Troubleshooting

### Collection Failing

**Check logs:**
```bash
sudo journalctl -u qbr-collector.service -n 100 --no-pager
```

**Common issues:**

1. **ConnectWise API Error**
   - Check credentials in `/opt/es-inventory-hub/.env`
   - Verify API access at https://helpme.enersystems.com
   - Check rate limits

2. **Database Connection Error**
   - Verify PostgreSQL is running: `sudo systemctl status postgresql`
   - Check DB_DSN in `.env` file
   - Test connection manually

3. **NinjaOne API Error**
   - Check NinjaOne API credentials
   - Verify API token hasn't expired

### Timer Not Running

```bash
# Check timer status
systemctl status qbr-collector.timer

# If not active, restart
sudo systemctl restart qbr-collector.timer
```

### Missing Data

**Check collection log:**
```bash
sudo journalctl -u qbr-collector.service --since "7 days ago" | grep -E "(SUCCESS|FAILED)"
```

**Re-run collection for specific month:**
```bash
source /opt/es-inventory-hub/.venv/bin/activate
source /opt/es-inventory-hub/.env

# Run specific period
python3 -m collectors.qbr.ninja_main --period 2025-10
python3 -m collectors.qbr.connectwise_main --period 2025-10
```

---

## Performance Metrics

**Collection Performance** (Production):
- NinjaOne: ~7 seconds
- ConnectWise: ~15 seconds
- Total: ~22 seconds
- CPU Usage: ~1 second
- Memory: < 100MB

**API Response Times:**
- Monthly metrics: < 100ms
- Quarterly metrics: < 200ms
- SmartNumbers: < 300ms

---

## Maintenance

### Weekly Tasks

1. **Verify collection ran successfully**
   ```bash
   sudo journalctl -u qbr-collector.service --since "7 days ago" | grep "Status:"
   ```

2. **Check data accuracy** - Compare against source systems

3. **Monitor disk usage**
   ```bash
   PGPASSWORD='mK2D282lRrs6bTpXWe7' psql -h localhost -U postgres -d es_inventory_hub -c "
   SELECT pg_size_pretty(pg_total_relation_size('qbr_metrics_monthly'));
   "
   ```

### Monthly Tasks

1. **Add manual metrics** for previous month (revenue, employees, sales)
2. **Review SmartNumbers** for trends
3. **Update thresholds** if needed
4. **Check for system updates**

### Quarterly Tasks

1. **Generate QBR report** using SmartNumbers API
2. **Validate historical data** for accuracy
3. **Review and update documentation**
4. **Performance optimization** if needed

---

## Backup and Recovery

### Database Backup

```bash
# Backup QBR tables
PGPASSWORD='mK2D282lRrs6bTpXWe7' pg_dump -h localhost -U postgres -d es_inventory_hub \
  -t qbr_metrics_monthly \
  -t qbr_thresholds \
  > /backup/qbr_backup_$(date +%Y%m%d).sql
```

### Restore from Backup

```bash
PGPASSWORD='mK2D282lRrs6bTpXWe7' psql -h localhost -U postgres -d es_inventory_hub \
  < /backup/qbr_backup_20251115.sql
```

---

## Future Enhancements

**Planned Features:**
- [ ] Email alerts on collection failures
- [ ] Web dashboard for viewing SmartNumbers
- [ ] Automated trend analysis
- [ ] Integration with QuickBooks for revenue data
- [ ] Mobile app for viewing metrics
- [ ] Automated QBR report generation (PDF)

---

## Support and Documentation

**Documentation:**
- API Reference: `/opt/es-inventory-hub/docs/qbr/QBR_API_DOCUMENTATION.md`
- Testing Results: `/opt/es-inventory-hub/docs/qbr/PHASE4_TESTING_VALIDATION.md`
- Backend Readiness: `/opt/es-inventory-hub/docs/qbr/QBR_BACKEND_READINESS.md`

**Quick Reference Commands:**

```bash
# Check what's scheduled
systemctl list-timers qbr-collector.timer

# View last run
sudo journalctl -u qbr-collector.service -n 50

# Trigger manual run
sudo systemctl start qbr-collector.service

# View current month data
PGPASSWORD='mK2D282lRrs6bTpXWe7' psql -h localhost -U postgres -d es_inventory_hub -c \
  "SELECT * FROM qbr_metrics_monthly WHERE period = TO_CHAR(CURRENT_DATE, 'YYYY-MM');"

# Get SmartNumbers for current quarter
curl "http://localhost:5400/api/qbr/smartnumbers?period=2025-Q4"
```

---

## System Health Check

Run this health check script weekly:

```bash
#!/bin/bash
echo "=== QBR System Health Check ==="
echo ""

echo "1. Timer Status:"
systemctl is-active qbr-collector.timer && echo "   ✓ Timer Active" || echo "   ✗ Timer Inactive"

echo ""
echo "2. Last Collection:"
sudo journalctl -u qbr-collector.service --since "48 hours ago" --no-pager | grep "Status:" | tail -1

echo ""
echo "3. Data Freshness:"
PGPASSWORD='mK2D282lRrs6bTpXWe7' psql -h localhost -U postgres -d es_inventory_hub -t -c \
  "SELECT 'Last Update: ' || MAX(updated_at) FROM qbr_metrics_monthly WHERE period = TO_CHAR(CURRENT_DATE, 'YYYY-MM');"

echo ""
echo "4. Record Count:"
PGPASSWORD='mK2D282lRrs6bTpXWe7' psql -h localhost -U postgres -d es_inventory_hub -t -c \
  "SELECT COUNT(*) || ' total metrics' FROM qbr_metrics_monthly;"

echo ""
echo "5. Next Scheduled Run:"
systemctl list-timers qbr-collector.timer --no-pager | grep qbr-collector | awk '{print "   " $1, $2, $3}'

echo ""
echo "=== Health Check Complete ==="
```

---

**Version**: v1.22.0
**Last Updated**: November 15, 2025
**Maintainer**: ES Inventory Hub Team
**Status**: ✅ PRODUCTION

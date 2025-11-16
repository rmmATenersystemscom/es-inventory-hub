# QBR System: 9-Day Monitoring Plan

**Purpose**: Monitor automated daily collection for 9 consecutive days to validate system stability before production deployment.

**Start Date**: TBD (after systemd timer installation)
**Expected Completion**: Day 9 + 1 day for final review

---

## Overview

This monitoring plan ensures the QBR collection system runs reliably for 9 consecutive days, automatically collecting NinjaOne and ConnectWise metrics at 2:00 AM Central Time daily.

**Success Criteria**:
- 9/9 days successful collection (100% success rate)
- All metrics collected accurately
- No system errors or crashes
- Performance remains consistent
- Data validates against source systems

If any day fails, the 9-day counter resets and monitoring restarts.

---

## Pre-Monitoring Setup

### 1. Install Systemd Timer

Create systemd timer for automated daily collection:

```bash
# Copy timer and service files
sudo cp /opt/es-inventory-hub/systemd/qbr-collector.service /etc/systemd/system/
sudo cp /opt/es-inventory-hub/systemd/qbr-collector.timer /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable and start timer
sudo systemctl enable qbr-collector.timer
sudo systemctl start qbr-collector.timer

# Verify timer is active
sudo systemctl status qbr-collector.timer
sudo systemctl list-timers | grep qbr
```

Expected output:
```
qbr-collector.timer - QBR Daily Collection Timer
   Loaded: loaded
   Active: active (waiting)
  Trigger: Tomorrow at 02:00:00 CST
```

### 2. Set Up Monitoring Dashboard

Create monitoring script:

```bash
cat > /opt/es-inventory-hub/scripts/qbr_monitoring.sh << 'EOF'
#!/bin/bash
# QBR Daily Monitoring Script

PERIOD=$(date -d "yesterday" '+%Y-%m')
DB_DSN="postgresql://postgres:mK2D282lRrs6bTpXWe7@localhost:5432/es_inventory_hub"

echo "========================================"
echo "QBR Collection Monitoring - $(date)"
echo "========================================"
echo ""

# Check if collection ran
echo "1. Collection Log Status:"
PGPASSWORD='mK2D282lRrs6bTpXWe7' psql -h localhost -U postgres -d es_inventory_hub -c "
SELECT
    period,
    collector_name,
    status,
    records_collected,
    TO_CHAR(started_at, 'YYYY-MM-DD HH24:MI:SS') as started,
    TO_CHAR(completed_at, 'YYYY-MM-DD HH24:MI:SS') as completed,
    EXTRACT(EPOCH FROM (completed_at - started_at)) as duration_seconds
FROM qbr_collection_log
WHERE started_at >= CURRENT_DATE - INTERVAL '1 day'
ORDER BY started_at DESC
LIMIT 10;
"

echo ""
echo "2. Latest Metrics for Current Month ($PERIOD):"
PGPASSWORD='mK2D282lRrs6bTpXWe7' psql -h localhost -U postgres -d es_inventory_hub -c "
SELECT
    metric_name,
    metric_value,
    vendor_id,
    data_source,
    TO_CHAR(updated_at, 'YYYY-MM-DD HH24:MI') as last_updated
FROM qbr_metrics_monthly
WHERE period = '$PERIOD'
ORDER BY vendor_id NULLS LAST, metric_name;
"

echo ""
echo "3. System Health Check:"
journalctl -u qbr-collector.service --since "24 hours ago" --no-pager | tail -20

echo ""
echo "========================================"
echo "Monitoring Complete"
echo "========================================"
EOF

chmod +x /opt/es-inventory-hub/scripts/qbr_monitoring.sh
```

### 3. Configure Alerts (Optional)

Set up email alerts for collection failures:

```bash
# Edit /etc/systemd/system/qbr-collector.service
# Add OnFailure directive
[Unit]
OnFailure=status-email@%n.service
```

---

## Daily Monitoring Checklist

**Execute daily at 8:00 AM CT** (after 2:00 AM collection completes)

### Day X Monitoring Tasks

**Date**: ___________
**Day of Monitoring**: ___ / 9
**Monitored By**: ___________

#### 1. Check Collection Status

```bash
# Run monitoring script
/opt/es-inventory-hub/scripts/qbr_monitoring.sh
```

**Expected Results**:
- [ ] Both collectors (NinjaOne, ConnectWise) completed successfully
- [ ] Status = 'success' for all collectors
- [ ] No errors in collection log
- [ ] Duration < 30 seconds for each collector

**Actual Results**:
```
NinjaOne: ____________
ConnectWise: ____________
Errors: ____________
```

#### 2. Validate Metric Counts

**Current Month Metrics**:
- [ ] ConnectWise: 3 metrics (tickets_created, tickets_closed, time_spent)
- [ ] NinjaOne: 2 metrics (endpoints_managed, seats_managed)
- [ ] All metrics have updated_at from last night

**Expected Record Counts**:
```sql
SELECT COUNT(*) FROM qbr_metrics_monthly WHERE period = CURRENT_MONTH;
-- Expected: 5 records minimum (3 ConnectWise + 2 NinjaOne)
```

**Actual Count**: ___________

#### 3. Check Service Logs

```bash
# Check for errors in systemd logs
sudo journalctl -u qbr-collector.service --since "24 hours ago" -p err
```

**Expected**: No error messages

**Errors Found** (if any):
```
____________
```

#### 4. Validate Data Accuracy

Compare against source systems:

**ConnectWise Validation**:
```bash
# Get yesterday's ticket count from system
echo "Tickets created yesterday: "
# TODO: Compare with ConnectWise Manage report
```

**NinjaOne Validation**:
```bash
# Get current endpoint count
echo "Endpoints managed: "
# TODO: Compare with NinjaOne dashboard
```

**Validation Results**:
- [ ] ConnectWise tickets match source
- [ ] NinjaOne endpoints match source
- [ ] Time entries reasonable (between 0-500 hours/month)

#### 5. Performance Check

**Collection Times** (from monitoring script):
- NinjaOne duration: _____ seconds (target: <10s)
- ConnectWise duration: _____ seconds (target: <20s)

**Database Size**:
```bash
PGPASSWORD='mK2D282lRrs6bTpXWe7' psql -h localhost -U postgres -d es_inventory_hub -c "
SELECT COUNT(*) as total_metrics,
       COUNT(DISTINCT period) as periods,
       pg_size_pretty(pg_total_relation_size('qbr_metrics_monthly')) as table_size
FROM qbr_metrics_monthly;
"
```

Table size: ___________

#### 6. System Resource Check

```bash
# Check disk space
df -h /opt/es-inventory-hub

# Check memory usage
free -h

# Check database connections
PGPASSWORD='mK2D282lRrs6bTpXWe7' psql -h localhost -U postgres -c "
SELECT count(*) FROM pg_stat_activity WHERE datname = 'es_inventory_hub';
"
```

**Resource Status**:
- [ ] Disk usage < 80%
- [ ] Memory available > 1GB
- [ ] DB connections < 50

#### 7. Daily Summary

**Status**: ⬜ PASS ⬜ FAIL

**Notes**:
```
____________
____________
____________
```

**Issues Found** (if any):
```
____________
____________
```

**Action Items** (if any):
```
____________
____________
```

---

## Monitoring Log

### Day 1
- Date: ___________
- Status: ___________
- Notes: ___________

### Day 2
- Date: ___________
- Status: ___________
- Notes: ___________

### Day 3
- Date: ___________
- Status: ___________
- Notes: ___________

### Day 4
- Date: ___________
- Status: ___________
- Notes: ___________

### Day 5
- Date: ___________
- Status: ___________
- Notes: ___________

### Day 6
- Date: ___________
- Status: ___________
- Notes: ___________

### Day 7
- Date: ___________
- Status: ___________
- Notes: ___________

### Day 8
- Date: ___________
- Status: ___________
- Notes: ___________

### Day 9
- Date: ___________
- Status: ___________
- Notes: ___________

---

## Failure Response Plan

### If Collection Fails (Day X)

**Immediate Actions**:

1. **Check service status**:
```bash
sudo systemctl status qbr-collector.service
journalctl -u qbr-collector.service -n 100 --no-pager
```

2. **Check logs for errors**:
```bash
tail -100 /var/log/es-inventory-hub/qbr-collector.log
```

3. **Test manual collection**:
```bash
source /opt/es-inventory-hub/.venv/bin/activate
python3 -m collectors.qbr.ninja_main
python3 -m collectors.qbr.connectwise_main
```

4. **Document the failure**:
- Error messages
- Time of failure
- System state
- Recovery steps taken

5. **Reset monitoring period**:
- Restart 9-day count from Day 1
- Document reason for reset

### Common Issues and Resolutions

**Issue**: ConnectWise API timeout
- **Resolution**: Check network connectivity, retry collection
- **Prevention**: Increase timeout in `connectwise_api.py`

**Issue**: NinjaOne authentication failure
- **Resolution**: Refresh API credentials
- **Prevention**: Implement credential rotation

**Issue**: Database connection error
- **Resolution**: Restart PostgreSQL, check max_connections
- **Prevention**: Optimize connection pooling

**Issue**: Systemd timer not triggering
- **Resolution**: Check timer status, verify system time
- **Prevention**: Monitor timer with alerting

---

## Success Metrics

After 9 consecutive successful days, verify:

### Data Completeness
- [ ] All 9 days have collection log entries
- [ ] All 9 days have updated metrics
- [ ] No missing data or gaps
- [ ] All periods consistent (5+ metrics per day)

### Performance Consistency
- [ ] Average collection time < 30 seconds
- [ ] No performance degradation over time
- [ ] Database size growth reasonable
- [ ] No memory leaks detected

### Accuracy Validation
- [ ] Spot-checked 3+ days against source systems
- [ ] All comparisons within ±1% tolerance
- [ ] No systematic errors detected
- [ ] Timezone handling correct

### System Reliability
- [ ] No service crashes or restarts
- [ ] No database errors
- [ ] No API rate limiting issues
- [ ] No resource exhaustion

---

## Post-Monitoring Review

**After 9 successful days, complete the following**:

### 1. Final Data Audit

Run comprehensive data validation:

```bash
# Check for gaps
PGPASSWORD='mK2D282lRrs6bTpXWe7' psql -h localhost -U postgres -d es_inventory_hub -c "
WITH expected_dates AS (
    SELECT generate_series(
        CURRENT_DATE - INTERVAL '9 days',
        CURRENT_DATE - INTERVAL '1 day',
        '1 day'::interval
    )::date as date
)
SELECT
    ed.date,
    COUNT(DISTINCT qcl.collector_name) as collectors_run,
    COUNT(DISTINCT qmm.metric_name) as metrics_collected
FROM expected_dates ed
LEFT JOIN qbr_collection_log qcl ON DATE(qcl.started_at) = ed.date
LEFT JOIN qbr_metrics_monthly qmm ON qmm.period = TO_CHAR(ed.date, 'YYYY-MM')
GROUP BY ed.date
ORDER BY ed.date;
"
```

Expected: 2 collectors run per day, 5+ metrics collected

### 2. Performance Summary

Calculate average metrics:

```bash
PGPASSWORD='mK2D282lRrs6bTpXWe7' psql -h localhost -U postgres -d es_inventory_hub -c "
SELECT
    collector_name,
    COUNT(*) as runs,
    AVG(EXTRACT(EPOCH FROM (completed_at - started_at))) as avg_duration_seconds,
    MAX(EXTRACT(EPOCH FROM (completed_at - started_at))) as max_duration_seconds,
    AVG(records_collected) as avg_records
FROM qbr_collection_log
WHERE started_at >= CURRENT_DATE - INTERVAL '9 days'
  AND status = 'success'
GROUP BY collector_name;
"
```

### 3. Create Monitoring Report

Document results in `QBR_9DAY_MONITORING_REPORT.md`:
- Summary of 9 days
- Issues encountered and resolved
- Performance metrics
- Data accuracy validation results
- Recommendations for production

### 4. Approval for Production

**Monitoring Complete**: ⬜ YES ⬜ NO

**Approved By**: ___________
**Date**: ___________
**Ready for Phase 5**: ⬜ YES ⬜ NO

---

## Phase 5 Transition

Once monitoring is complete and approved:

1. **Create production configuration**
   - Finalize systemd timer schedule
   - Configure production alerting
   - Set up log rotation

2. **Deploy to production**
   - Enable timer permanently
   - Configure monitoring dashboards
   - Set up automated reporting

3. **Ongoing monitoring**
   - Weekly data validation
   - Monthly performance review
   - Quarterly system audit

---

## Appendix: Quick Reference Commands

### Check Timer Status
```bash
sudo systemctl status qbr-collector.timer
sudo systemctl list-timers | grep qbr
```

### Manual Collection Test
```bash
source /opt/es-inventory-hub/.venv/bin/activate
python3 -m collectors.qbr.ninja_main
python3 -m collectors.qbr.connectwise_main
```

### View Recent Logs
```bash
journalctl -u qbr-collector.service --since "24 hours ago"
```

### Check Latest Metrics
```bash
PGPASSWORD='mK2D282lRrs6bTpXWe7' psql -h localhost -U postgres -d es_inventory_hub -c "
SELECT period, metric_name, metric_value, TO_CHAR(updated_at, 'MM-DD HH24:MI') as updated
FROM qbr_metrics_monthly
WHERE period = TO_CHAR(CURRENT_DATE, 'YYYY-MM')
ORDER BY updated_at DESC
LIMIT 10;
"
```

### Database Status
```bash
PGPASSWORD='mK2D282lRrs6bTpXWe7' psql -h localhost -U postgres -d es_inventory_hub -c "
SELECT COUNT(*) FROM qbr_metrics_monthly;
SELECT COUNT(*) FROM qbr_collection_log WHERE started_at >= CURRENT_DATE - INTERVAL '9 days';
"
```

---

**Version**: v1.22.0  
**Last Updated**: November 16, 2025 02:32 UTC  
**Maintainer**: ES Inventory Hub Team

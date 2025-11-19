# ES Inventory Hub - Collector Services Fix

**Date**: November 16, 2025
**Issue**: All collectors stopped working after creating `.env` file for QBR system
**Status**: ✅ ALL FIXED

---

## Problem

When we created `/opt/es-inventory-hub/.env` on November 15, 2025 for the new QBR collector, we only included ConnectWise credentials. This caused all other collectors (Ninja, ThreatLocker, and cross-vendor checks) to fail because they couldn't access their required credentials.

### Timeline
- **Nov 14**: All collectors working ✅
- **Nov 15**: Created `.env` with only QBR/ConnectWise credentials
- **Nov 15-16**: All non-QBR collectors failing ❌
- **Nov 16**: Fixed by adding all credentials to `.env` ✅

---

## Root Cause

All collector services use the same environment file (`/opt/es-inventory-hub/.env`) but each needs different API credentials:

1. **QBR Collector** → ConnectWise credentials
2. **Ninja Collectors** → NinjaRMM credentials
3. **ThreatLocker Collectors** → ThreatLocker credentials
4. **Cross-Vendor Checks** → Database credentials (was working via systemd EnvironmentFile)

When we created the `.env` file with only ConnectWise credentials, the Ninja and ThreatLocker collectors couldn't find their required environment variables.

---

## Solution

Updated `/opt/es-inventory-hub/.env` to include **all** required credentials:

### ConnectWise (QBR Collector)
```bash
CONNECTWISE_SERVER=https://helpme.enersystems.com
CONNECTWISE_COMPANY_ID=enersystems
CONNECTWISE_CLIENT_ID=5aa0e7b6-5500-48fb-90a8-8410802df04c
CONNECTWISE_PUBLIC_KEY=s9QF8u12JFPE22R7
CONNECTWISE_PRIVATE_KEY=vgo8s3P0mvpnPXBn
```

### NinjaRMM (Ninja Collectors)
```bash
NINJA_BASE_URL=https://app.ninjarmm.com
NINJA_CLIENT_ID=amRqddIagVDindNeMH9j5JiQd2A
NINJA_CLIENT_SECRET=4dh6gZviBEe9OneAANJjVJSGLCT0uwVJ04Z7TXOXGjNJlvZdHQV8QQ
NINJA_REFRESH_TOKEN=ebb3f730-ea7e-4103-b40e-16baf6b1cd41.zG4wwCFoKuV7xT7oT1asqAxqXfkox2rg_etLcZ0tmhc
```

### ThreatLocker (ThreatLocker Collectors)
```bash
THREATLOCKER_API_BASE_URL=https://portalapi.g.threatlocker.com
THREATLOCKER_API_KEY=24248BE80D8E0D4B85182FF90E7E141DBB99F90020F0B2C0D7C9269F1334CC24
THREATLOCKER_ORGANIZATION_ID=dd850352-ee85-436b-8e41-818bdb52712c
```

### Database (All Collectors)
```bash
DB_DSN=postgresql://postgres:mK2D282lRrs6bTpXWe7@localhost:5432/es_inventory_hub
```

### File Permissions
```bash
Owner: rene
Group: svc_es-hub
Permissions: 640 (rw-r-----)
```

This allows the `svc_es-hub` service user to read the file while keeping it secure.

---

## All Collector Services

### Evening Collections (10:30 PM - 11:30 PM Central)

| Service | Timer | Schedule | Status | Purpose |
|---------|-------|----------|--------|---------|
| qbr-collector | qbr-collector.timer | 10:30 PM | ✅ Working | QBR metrics (ConnectWise + NinjaOne) |
| es-inventory-ninja | es-inventory-ninja.timer | 11:00 PM | ✅ Working | Device inventory snapshots |
| es-inventory-threatlocker | es-inventory-threatlocker.timer | 11:15 PM | ✅ Working | ThreatLocker device snapshots |
| es-cross-vendor-evening | es-cross-vendor-evening.timer | 11:30 PM | ✅ Working | Cross-vendor consistency checks |

### Morning Collections (2:45 AM - 3:15 AM Central)

| Service | Timer | Schedule | Status | Purpose |
|---------|-------|----------|--------|---------|
| es-ninja-morning | es-ninja-morning.timer | 2:45 AM | ✅ Working | Device inventory snapshots |
| es-threatlocker-morning | es-threatlocker-morning.timer | 3:00 AM | ✅ Working | ThreatLocker device snapshots |
| es-cross-vendor-morning | es-cross-vendor-morning.timer | 3:15 AM | ✅ Working | Cross-vendor consistency checks |

**Total**: 7 active collectors (8 timers including the generic cross-vendor-checks timer)

---

## Verification

### Check All Timers
```bash
systemctl list-timers | grep -E "(ninja|qbr|threatlocker|cross)"
```

### Test Individual Services
```bash
# QBR Collector
sudo systemctl start qbr-collector.service
sudo journalctl -u qbr-collector.service -n 20

# Ninja Collector
sudo systemctl start es-inventory-ninja.service
sudo journalctl -u es-inventory-ninja.service -n 20

# ThreatLocker Collector
sudo systemctl start es-inventory-threatlocker.service
sudo journalctl -u es-inventory-threatlocker.service -n 20

# Cross-Vendor Checks
sudo systemctl start es-cross-vendor-evening.service
sudo journalctl -u es-cross-vendor-evening.service -n 20
```

### Expected Success Messages
- **QBR**: "Status: ✓ ALL COLLECTORS SUCCESSFUL"
- **Ninja**: "Ninja collection completed successfully"
- **ThreatLocker**: "ThreatLocker collection completed successfully"
- **Cross-Vendor**: "Cross-vendor consistency checks completed"

---

## Lessons Learned

1. **Centralized Environment File**: All services now use `/opt/es-inventory-hub/.env`
2. **Complete Credentials**: The `.env` file must contain ALL required credentials for ALL services
3. **Permission Management**: Edit tool resets file permissions - must fix permissions after each edit
4. **Service Dependencies**: Multiple services can depend on the same environment file

---

## Monitoring

### Check for Failed Services
```bash
systemctl list-units --type=service --state=failed | grep -E "(ninja|qbr|threatlocker|cross)"
```

### View Recent Logs
```bash
# All collector services in last 24 hours
sudo journalctl --since "24 hours ago" | grep -E "(ninja|qbr|threatlocker|cross)" | grep -E "(SUCCESS|FAILED|ERROR)"
```

### Check Database for Recent Collections
```bash
# Check device snapshots
psql -U postgres -h localhost -d es_inventory_hub -c "
SELECT snapshot_date, vendor_id, COUNT(*)
FROM device_snapshot
WHERE snapshot_date >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY snapshot_date, vendor_id
ORDER BY snapshot_date DESC, vendor_id;
"

# Check QBR metrics
psql -U postgres -h localhost -d es_inventory_hub -c "
SELECT period, COUNT(*) as total_metrics
FROM qbr_metrics_monthly
WHERE updated_at >= NOW() - INTERVAL '7 days'
GROUP BY period
ORDER BY period DESC;
"
```

---

## Future Considerations

1. **Automated Testing**: Create a health check script that verifies all collectors
2. **Alerting**: Set up alerts if collectors fail to run
3. **Credential Rotation**: Document process for updating API credentials
4. **Backup Strategy**: Ensure `.env` file is included in backups (securely)

---

**Status**: ✅ All 7 collectors working and scheduled
**Next Scheduled Runs**: See timer output above
**Documented By**: Claude Code
**Last Updated**: November 16, 2025

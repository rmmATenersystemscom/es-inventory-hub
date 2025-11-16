# Secrets Synchronization Plan

**Plan for periodically syncing API secrets from shared secrets to local .env**

---

## Objective

Keep `/opt/es-inventory-hub/.env` synchronized with the latest API credentials from `/opt/shared-secrets/api-secrets.env` (the source of truth).

---

## Implementation Summary

### ✅ Components Created

1. **Sync Script** (`scripts/sync_secrets.py`)
   - Python script that compares and syncs variables
   - Handles file parsing, comparison, and updates
   - Creates backups before changes
   - Supports dry-run mode
   - Comprehensive logging

2. **Wrapper Script** (`scripts/sync_secrets.sh`)
   - Bash wrapper that handles sudo access
   - Simplifies execution for users

3. **Systemd Service** (`ops/systemd/sync-secrets.service`)
   - Service definition for automated runs
   - Runs as user `rene`
   - Logs to systemd journal

4. **Systemd Timer** (`ops/systemd/sync-secrets.timer`)
   - Daily schedule: 3:00 AM Central (8:00 AM UTC)
   - Persistent (runs if missed)
   - Randomized delay to avoid thundering herd

5. **Documentation** (`docs/GUIDE_SECRETS_SYNC.md`)
   - Complete usage guide
   - Troubleshooting section
   - Security considerations

---

## Variables Managed

### Synced Variables (from shared secrets)

**NinjaRMM**:
- `NINJA_BASE_URL`
- `NINJA_CLIENT_ID`
- `NINJA_CLIENT_SECRET`
- `NINJA_REFRESH_TOKEN`

**ThreatLocker**:
- `THREATLOCKER_API_BASE_URL`
- `THREATLOCKER_API_KEY`
- `THREATLOCKER_ORGANIZATION_ID`

**ConnectWise**:
- `CONNECTWISE_SERVER`
- `CONNECTWISE_COMPANY_ID`
- `CONNECTWISE_CLIENT_ID`
- `CONNECTWISE_PUBLIC_KEY`
- `CONNECTWISE_PRIVATE_KEY`

### Preserved Variables (local-only)

- `DB_DSN`
- `DATABASE_URL`
- `FLASK_ENV`
- `SECRET_KEY`
- `LOG_LEVEL`
- `LOG_FILE`
- `THREATLOCKER_BASE_URL`

---

## Usage

### Manual Sync

**Dry run** (check for changes):
```bash
cd /opt/es-inventory-hub
bash scripts/sync_secrets.sh --dry-run
```

**Apply changes**:
```bash
bash scripts/sync_secrets.sh
```

### Automated Sync

**Install systemd timer**:
```bash
sudo cp /opt/es-inventory-hub/ops/systemd/sync-secrets.service /etc/systemd/system/
sudo cp /opt/es-inventory-hub/ops/systemd/sync-secrets.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable sync-secrets.timer
sudo systemctl start sync-secrets.timer
```

**Check status**:
```bash
sudo systemctl status sync-secrets.timer
sudo journalctl -u sync-secrets.service -n 50
```

---

## Workflow

### When Shared Secrets Are Updated

1. **Admin updates** `/opt/shared-secrets/api-secrets.env` with new credentials
2. **Automated sync** runs daily at 3:00 AM Central
3. **Manual sync** can be triggered immediately if needed:
   ```bash
   sudo systemctl start sync-secrets.service
   ```
4. **Script compares** source and target files
5. **Backup created** before any changes
6. **Variables updated** in local `.env` file
7. **Logs recorded** for audit trail

### Change Detection

The script:
- Compares only variables in `SYNC_VARIABLES` list
- Updates only if values differ
- Preserves local-only variables
- Creates timestamped backups
- Logs all changes

---

## Backup Strategy

**Location**: `/opt/es-inventory-hub/.env-backups/`  
**Format**: `.env.YYYYMMDD_HHMMSS`  
**Retention**: Manual cleanup (recommend keeping last 10 backups)

Backups are created automatically before any changes are applied.

---

## Monitoring

### Logs

**Systemd Journal**:
```bash
sudo journalctl -u sync-secrets.service
```

**File Log** (if permissions allow):
- `/var/log/es-inventory-hub/sync_secrets.log`
- Or: `/opt/es-inventory-hub/logs/sync_secrets.log`

### Status Checks

**Check timer status**:
```bash
systemctl list-timers | grep sync-secrets
```

**Check last run**:
```bash
sudo journalctl -u sync-secrets.service --since "1 day ago"
```

---

## Security

### File Permissions

- Source file: Protected (requires sudo to read)
- Target file: `600` (read/write owner only)
- Backups: `600` (read/write owner only)

### Access Control

- Script requires sudo to read source file
- Service runs as user `rene` (not root)
- Only specific variables are synced
- Local-only variables are never overwritten

---

## Testing

### Initial Test (Dry Run)

```bash
cd /opt/es-inventory-hub
bash scripts/sync_secrets.sh --dry-run
```

Expected output:
- List of variables that would be updated
- Old and new values
- "DRY RUN: No changes were made" message

### Apply Changes

```bash
bash scripts/sync_secrets.sh
```

Expected behavior:
- Backup created in `.env-backups/`
- Variables updated in `.env`
- Logs show changes applied
- File permissions set to 600

### Verify Sync

```bash
# Check if variables match
grep NINJA_CLIENT_ID /opt/es-inventory-hub/.env
sudo grep NINJA_CLIENT_ID /opt/shared-secrets/api-secrets.env
```

---

## Maintenance

### Regular Tasks

1. **Monitor logs** weekly for sync activity
2. **Review backups** monthly (clean up old backups)
3. **Verify sync** after shared secrets updates
4. **Check timer** is running and scheduled correctly

### Troubleshooting

See [GUIDE_SECRETS_SYNC.md](./GUIDE_SECRETS_SYNC.md#troubleshooting) for detailed troubleshooting steps.

Common issues:
- Permission denied (use sudo)
- No changes detected (verify source file updated)
- Variables not syncing (check variable names)

---

## Future Enhancements

Potential improvements:
1. **Email notifications** on changes
2. **Automatic backup cleanup** (keep last N backups)
3. **Change validation** (test API credentials after sync)
4. **Multi-file sync** (sync to multiple locations)
5. **Change history** (track what changed when)

---

## Related Files

- `scripts/sync_secrets.py` - Main sync script
- `scripts/sync_secrets.sh` - Wrapper script
- `ops/systemd/sync-secrets.service` - Systemd service
- `ops/systemd/sync-secrets.timer` - Systemd timer
- `docs/GUIDE_SECRETS_SYNC.md` - User documentation

---

**Version**: v1.22.0  
**Last Updated**: November 16, 2025 02:32 UTC  
**Maintainer**: ES Inventory Hub Team  
**Status**: ✅ **IMPLEMENTED**  
**Next Review**: After first automated sync run


# Secrets Synchronization Guide

**Automated synchronization of API secrets from shared secrets file to local .env**

---

## Overview

The ES Inventory Hub project uses a secrets synchronization system to keep the local `.env` file up-to-date with the latest API credentials from the shared secrets file.

**Source of Truth**: `/opt/shared-secrets/api-secrets.env`  
**Local File**: `/opt/es-inventory-hub/.env`  
**Sync Script**: `/opt/es-inventory-hub/scripts/sync_secrets.py`

---

## How It Works

### Variables Synced

The sync script updates the following API-related variables from the shared secrets file:

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

### Variables Preserved

The following local-only variables are **never** overwritten:
- `DB_DSN`
- `DATABASE_URL`
- `FLASK_ENV`
- `SECRET_KEY`
- `LOG_LEVEL`
- `LOG_FILE`
- `THREATLOCKER_BASE_URL` (local-specific variant)

---

## Manual Sync

### Dry Run (Check for Changes)

Check what would be updated without making changes:

```bash
cd /opt/es-inventory-hub
bash scripts/sync_secrets.sh --dry-run
```

### Apply Changes

Sync secrets and update the local `.env` file:

```bash
cd /opt/es-inventory-hub
bash scripts/sync_secrets.sh
```

### Verbose Output

See detailed information about the sync process:

```bash
bash scripts/sync_secrets.sh --verbose
```

---

## Automated Sync

### Systemd Timer (Recommended)

The sync runs automatically via a systemd timer:

**Service**: `sync-secrets.service`  
**Timer**: `sync-secrets.timer`  
**Schedule**: Daily at 3:00 AM Central Time (8:00 AM UTC)

#### Install and Enable

```bash
# Copy service and timer files
sudo cp /opt/es-inventory-hub/ops/systemd/sync-secrets.service /etc/systemd/system/
sudo cp /opt/es-inventory-hub/ops/systemd/sync-secrets.timer /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable and start the timer
sudo systemctl enable sync-secrets.timer
sudo systemctl start sync-secrets.timer

# Check status
sudo systemctl status sync-secrets.timer
```

#### Check Timer Status

```bash
# List all timers
systemctl list-timers

# Check next run time
systemctl status sync-secrets.timer

# View logs
sudo journalctl -u sync-secrets.service -n 50
```

#### Manual Trigger

Run the sync manually (outside of scheduled time):

```bash
sudo systemctl start sync-secrets.service
```

---

## Backup System

The sync script automatically creates backups before making changes:

**Backup Location**: `/opt/es-inventory-hub/.env-backups/`  
**Backup Format**: `.env.YYYYMMDD_HHMMSS`

Backups are created automatically before any changes are applied. The last 10 backups are retained (older backups can be manually cleaned up).

---

## Logging

### Log Locations

**Systemd Journal** (for automated runs):
```bash
sudo journalctl -u sync-secrets.service
```

**File Log** (if permissions allow):
- `/var/log/es-inventory-hub/sync_secrets.log`
- Or: `/opt/es-inventory-hub/logs/sync_secrets.log` (fallback)

### Log Format

Logs include:
- Timestamp
- Variables being synced
- Old and new values
- Success/failure status
- Error messages (if any)

---

## Troubleshooting

### Permission Denied

**Error**: `Permission denied accessing source file`

**Solution**: The script requires sudo to read the shared secrets file. Use the wrapper script:
```bash
bash scripts/sync_secrets.sh
```

### No Changes Detected

If the sync reports "No changes needed" but you expect changes:

1. **Check source file**: Verify the shared secrets file has been updated
   ```bash
   sudo cat /opt/shared-secrets/api-secrets.env | grep NINJA_CLIENT_ID
   ```

2. **Check local file**: Verify current values in local .env
   ```bash
   grep NINJA_CLIENT_ID /opt/es-inventory-hub/.env
   ```

3. **Run with verbose**: See detailed comparison
   ```bash
   bash scripts/sync_secrets.sh --dry-run --verbose
   ```

### Variables Not Syncing

If a variable should be synced but isn't:

1. **Check variable name**: Ensure it matches exactly (case-sensitive)
2. **Check sync list**: Verify the variable is in `SYNC_VARIABLES` in the script
3. **Check source file**: Ensure the variable exists in the shared secrets file

### Backup Issues

If backups aren't being created:

1. **Check permissions**: Ensure write access to `/opt/es-inventory-hub/.env-backups/`
2. **Check disk space**: Ensure sufficient disk space
3. **Manual backup**: Create backup manually if needed
   ```bash
   cp /opt/es-inventory-hub/.env /opt/es-inventory-hub/.env-backups/.env.manual.$(date +%Y%m%d_%H%M%S)
   ```

---

## Security Considerations

### File Permissions

The sync script sets appropriate permissions on the `.env` file:
- **Permissions**: `600` (read/write for owner only)
- **Owner**: User running the script (typically `rene`)

### Credential Handling

- Secrets are read from the protected shared secrets file
- Only specific variables are synced (not all variables)
- Local-only variables are preserved
- Backups are created before changes

### Best Practices

1. **Never commit `.env` files** to version control
2. **Review changes** before applying (use `--dry-run`)
3. **Monitor logs** for sync activity
4. **Keep backups** for recovery if needed
5. **Rotate API keys** regularly in the shared secrets file

---

## Integration with Collectors

The synced secrets are used by:

- **Ninja Collector**: `collectors/ninja/` - Uses `NINJA_*` variables
- **ThreatLocker Collector**: `collectors/threatlocker/` - Uses `THREATLOCKER_*` variables
- **ConnectWise Collector** (future): Will use `CONNECTWISE_*` variables

Collectors read from the local `.env` file, which is kept up-to-date by this sync process.

---

## Related Documentation

- [Environment Configuration Guide](./GUIDE_ENVIRONMENT_CONFIGURATION.md) - Environment variable management
- [Systemd Configuration](./ARCH_SYSTEMD.md) - Systemd service setup
- [API Integration](./API_INTEGRATION.md) - API usage and configuration

---

## Script Reference

### Command Line Options

```bash
python3 scripts/sync_secrets.py [OPTIONS]

Options:
  --dry-run    Show what would be changed without making changes
  --verbose    Enable debug logging
  -h, --help   Show help message
```

### Exit Codes

- `0`: Success (changes applied or no changes needed)
- `1`: Error (permission denied, file not found, etc.)

---

**Version**: v1.22.0  
**Last Updated**: November 16, 2025 02:32 UTC  
**Maintainer**: ES Inventory Hub Team  
**Status**: ✅ **ACTIVE** - Automated sync enabled via systemd timer


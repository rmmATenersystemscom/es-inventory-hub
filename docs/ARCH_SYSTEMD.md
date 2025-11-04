# Systemd Services for ES Inventory Hub

This document describes how to set up automated daily collection from both the Ninja and ThreatLocker collectors using systemd services and timers.

## Overview

Both collectors are designed to run daily at specific times:
- **Ninja collector**: 02:10 AM Central Time daily
- **ThreatLocker collector**: 02:31 AM Central Time daily

The 21-minute stagger ensures they don't interfere with each other and provides time for any database locks to clear.

## Architecture

Each collector uses a three-file setup:
1. **Script** (`scripts/run_*_daily.sh`): Bash runner with error handling and logging
2. **Service** (`ops/systemd/*-collector.service`): Systemd service definition
3. **Timer** (`ops/systemd/*-collector.timer`): Systemd timer for scheduling

## Installation

### 1. Copy Unit Files

Copy both service and timer files into place:

```bash
# Copy Ninja collector units
sudo cp ops/systemd/ninja-collector.service /etc/systemd/system/
sudo cp ops/systemd/ninja-collector.timer /etc/systemd/system/

# Copy ThreatLocker collector units
sudo cp ops/systemd/threatlocker-collector.service /etc/systemd/system/
sudo cp ops/systemd/threatlocker-collector.timer /etc/systemd/system/
```

### 2. Reload Systemd

```bash
sudo systemctl daemon-reload
```

### 3. Enable and Start Timers

```bash
# Enable and start both timers (substitute your login user)
sudo systemctl enable --now ninja-collector@${USER}.timer
sudo systemctl enable --now threatlocker-collector@${USER}.timer
```

## Verification

### Check Timer Status

```bash
# Check both timers
systemctl status ninja-collector@${USER}.timer
systemctl status threatlocker-collector@${USER}.timer

# List all timers
systemctl list-timers | grep -E "(ninja|threatlocker)"
```

### Check Service Status

```bash
# Check service status (will show last run)
systemctl status ninja-collector@${USER}.service
systemctl status threatlocker-collector@${USER}.service
```

### View Logs

```bash
# View recent logs for both services
journalctl -u ninja-collector@${USER}.service -n 100 --no-pager
journalctl -u threatlocker-collector@${USER}.service -n 100 --no-pager

# Follow logs in real-time
journalctl -u ninja-collector@${USER}.service -f
journalctl -u threatlocker-collector@${USER}.service -f
```

## Manual Execution

### Run Collectors Manually

```bash
# Run Ninja collector manually
systemctl start ninja-collector@${USER}.service

# Run ThreatLocker collector manually
systemctl start threatlocker-collector@${USER}.service
```

### Check File Logs

Both collectors also log to files for easy access:

```bash
# View file logs
tail -f /var/log/es-inventory-hub/ninja_daily.log
tail -f /var/log/es-inventory-hub/threatlocker_daily.log

# Check today's logs
grep "$(date '+%Y-%m-%d')" /var/log/es-inventory-hub/ninja_daily.log
grep "$(date '+%Y-%m-%d')" /var/log/es-inventory-hub/threatlocker_daily.log
```

## Database Verification

### Verify Collection Results

```bash
# Check today's data for both collectors
psql -U postgres -h localhost -d es_inventory_hub -c "
SELECT snapshot_date, vendor_id, COUNT(*)
FROM device_snapshot
WHERE snapshot_date = CURRENT_DATE
GROUP BY snapshot_date, vendor_id
ORDER BY snapshot_date DESC, vendor_id;
"
```

## Troubleshooting

### Common Issues

1. **Service Fails to Start**
   ```bash
   # Check service logs
   journalctl -u ninja-collector@${USER}.service -n 50
   
   # Check if dependencies are running
   systemctl status network-online.target
   systemctl status postgresql.service
   ```

2. **Timer Not Running**
   ```bash
   # Check timer status
   systemctl status ninja-collector@${USER}.timer
   
   # Check if timer is enabled
   systemctl is-enabled ninja-collector@${USER}.timer
   ```

3. **Permission Issues**
   ```bash
   # Ensure scripts are executable
   chmod +x /opt/es-inventory-hub/scripts/run_ninja_daily.sh
   chmod +x /opt/es-inventory-hub/scripts/run_threatlocker_daily.sh
   
   # Check log directory permissions
   ls -ld /var/log/es-inventory-hub
   ```

### Service Dependencies

Both services depend on:
- `network-online.target`: Ensures network connectivity
- `postgresql.service`: Ensures database is available

If these dependencies fail, the collector services will not start.

## Migration from Cron

If you were previously using cron for the Ninja collector:

### 1. Remove Cron Job

```bash
# Edit crontab
crontab -e

# Remove the line:
# 10 2 * * * /opt/es-inventory-hub/scripts/run_ninja_daily.sh >> /var/log/es-inventory-hub/ninja_daily.log 2>&1
```

### 2. Verify Systemd is Working

```bash
# Check that systemd timers are running
systemctl list-timers | grep -E "(ninja|threatlocker)"

# Verify next run times
systemctl status ninja-collector@${USER}.timer
systemctl status threatlocker-collector@${USER}.timer
```

## Advantages over Cron

1. **Dependency Management**: Waits for network and PostgreSQL
2. **Automatic Restarts**: Restarts on failure with configurable delays
3. **Better Logging**: Structured logs via journald
4. **Status Visibility**: Clear status via `systemctl status`
5. **Persistent Timers**: Catches up if system was down
6. **Centralized Management**: Single interface for all services

## Service Configuration Details

### Service Type: oneshot

Both services use `Type=oneshot` because they:
- Run once and exit
- Don't stay running in the background
- Are suitable for batch jobs

### Restart Policy

- `Restart=on-failure`: Only restarts if the service fails
- `RestartSec=30s`: Waits 30 seconds between restart attempts

### User Configuration

Both services use `User=%i` which means:
- The `%i` is replaced with the username when the service is started
- Allows running as different users (e.g., `ninja-collector@john`, `ninja-collector@admin`)

## Log Rotation

Consider setting up log rotation for the file logs:

```bash
# Create logrotate configuration
sudo tee /etc/logrotate.d/es-inventory-hub << EOF
/var/log/es-inventory-hub/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 $(whoami) $(whoami)
}
EOF
```

## Security Considerations

- Services run with the privileges of the specified user
- Environment variables are loaded from `/opt/dashboard-project/es-dashboards/.env` (shared with dashboard project)
- Log files may contain sensitive information; restrict access appropriately
- Consider running as dedicated service users rather than personal accounts

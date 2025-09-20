# Cron Configuration for ES Inventory Hub

This document describes how to set up automated daily collection from the Ninja collector.

## Overview

The Ninja collector is designed to run daily at 02:10 AM Central Time to collect device inventory data. This is done via a cron job that executes the `run_ninja_daily.sh` script.

## Installation

### 1. Install the Crontab Entry

To install the cron job, edit your crontab:

```bash
crontab -e
```

Add the following line to run the Ninja collector daily at 02:10 AM Central Time:

```
10 2 * * * /opt/es-inventory-hub/scripts/run_ninja_daily.sh >> /var/log/es-inventory-hub/ninja_daily.log 2>&1
```

**Note**: This crontab entry:
- Runs at 02:10 (2:10 AM Central Time) every day
- Executes the shell script with proper error handling
- Appends both stdout and stderr to the log file
- Creates log entries with timestamps for debugging

### 2. Verify Installation

After saving the crontab, verify it was installed correctly:

```bash
crontab -l
```

You should see your new cron entry listed.

## Manual Testing

### Test the Script Directly

You can test the script manually to ensure it works correctly:

```bash
# Run the script manually
/opt/es-inventory-hub/scripts/run_ninja_daily.sh

# Check the exit code
echo "Exit code: $?"
```

### Test with Cron Environment

To test in an environment similar to what cron provides:

```bash
# Test with minimal environment (similar to cron)
env -i /bin/sh -c '/opt/es-inventory-hub/scripts/run_ninja_daily.sh'
```

## Monitoring and Logs

### View Real-time Logs

To monitor the collector in real-time:

```bash
# Tail the log file to see live output
tail -f /var/log/es-inventory-hub/ninja_daily.log
```

### Check Recent Log Entries

To see the most recent log entries:

```bash
# Show last 50 lines
tail -n 50 /var/log/es-inventory-hub/ninja_daily.log

# Show logs from today
grep "$(date '+%Y-%m-%d')" /var/log/es-inventory-hub/ninja_daily.log
```

### Log Rotation

Consider setting up log rotation to prevent the log file from growing too large:

```bash
# Create a logrotate configuration (example)
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

## Troubleshooting

### Common Issues

1. **Permission Denied**
   - Ensure the script is executable: `chmod +x /opt/es-inventory-hub/scripts/run_ninja_daily.sh`
   - Check that the log directory is writable: `ls -ld /var/log/es-inventory-hub`

2. **Environment Variables Not Found**
   - Verify the .env file exists: `ls -la /opt/dashboard-project/es-dashboards/.env`
   - Check that required variables are set in the environment file

3. **Virtual Environment Issues**
   - Ensure the venv exists: `ls -la /opt/es-inventory-hub/.venv`
   - Verify Python packages are installed: `/opt/es-inventory-hub/.venv/bin/pip list`

4. **Database Connection Issues**
   - Check database connectivity from the script environment
   - Verify DATABASE_URL or DB_DSN is properly set in the .env file

### Check Cron Logs

System cron logs can help diagnose scheduling issues:

```bash
# Check system cron logs (location varies by distribution)
# Ubuntu/Debian:
grep CRON /var/log/syslog | grep ninja

# CentOS/RHEL:
grep CRON /var/log/cron | grep ninja
```

## Script Details

The `run_ninja_daily.sh` script performs the following steps:

1. **Environment Setup**: Sources the shared .env file from `/opt/dashboard-project/es-dashboards/.env`
2. **Virtual Environment**: Activates the repository's Python virtual environment
3. **Logging**: Creates timestamped log entries for tracking and debugging
4. **Collection**: Executes the Ninja collector without any device limits
5. **Error Handling**: Exits with non-zero code on failure for cron monitoring

## Security Considerations

- The script runs with the privileges of the user who installed the crontab
- Ensure proper file permissions on the .env file to protect sensitive credentials
- Log files may contain sensitive information; restrict access appropriately
- Consider running the cron job as a dedicated service user rather than root

## Verification

### Check Cron Job Installation

To verify that the cron job is properly installed and configured:

```bash
# Run the verification script
./scripts/check_cron.sh
```

The verification script will check:

1. **Script Executability**: Ensures `run_ninja_daily.sh` is executable
2. **Cron Job Installation**: Searches for the cron job in your crontab
3. **Log Directory**: Verifies the log directory exists and is writable
4. **Log File**: Shows the last 10 lines of the log file (if it exists)

### Example Verification Output

**When cron job is installed:**
```
🔍 Cron Job Verification for ES Inventory Hub
==============================================

ℹ️  Checking if /opt/es-inventory-hub/scripts/run_ninja_daily.sh is executable...
✅ Script is executable: /opt/es-inventory-hub/scripts/run_ninja_daily.sh

ℹ️  Checking if cron job is installed...
✅ Cron job installed
Found cron line:
  10 2 * * * /opt/es-inventory-hub/scripts/run_ninja_daily.sh >> /var/log/es-inventory-hub/ninja_daily.log 2>&1

ℹ️  Checking log directory: /var/log/es-inventory-hub
✅ Log directory exists and is writable

ℹ️  Checking log file: /var/log/es-inventory-hub/ninja_daily.log
✅ Log file exists and is readable
Last 10 lines of log file:
----------------------------------------
  2025-09-01 02:10:01 === Starting Ninja daily collection ===
  2025-09-01 02:10:01 Sourcing environment from /opt/dashboard-project/es-dashboards/.env
  2025-09-01 02:10:01 Activating virtual environment: /opt/es-inventory-hub/.venv
  2025-09-01 02:10:01 Starting Ninja collector...
  2025-09-01 02:10:15 Ninja collector completed successfully
  2025-09-01 02:10:15 === Ninja daily collection finished ===
----------------------------------------

==============================================
✅ All checks passed! Cron job should be working correctly.
```

**When cron job is NOT installed:**
```
🔍 Cron Job Verification for ES Inventory Hub
==============================================

ℹ️  Checking if /opt/es-inventory-hub/scripts/run_ninja_daily.sh is executable...
✅ Script is executable: /opt/es-inventory-hub/scripts/run_ninja_daily.sh

ℹ️  Checking if cron job is installed...
❌ Cron job not installed
ℹ️  Install with: crontab -e and add:
  10 2 * * * /opt/es-inventory-hub/scripts/run_ninja_daily.sh >> /var/log/es-inventory-hub/ninja_daily.log 2>&1

ℹ️  Checking log directory: /var/log/es-inventory-hub
⚠️  Log directory not found: /var/log/es-inventory-hub
ℹ️  Directory will be created when cron job runs

ℹ️  Checking log file: /var/log/es-inventory-hub/ninja_daily.log
⚠️  Log file not found: /var/log/es-inventory-hub/ninja_daily.log
ℹ️  This is normal if the cron job hasn't run yet

==============================================
❌ Some checks failed. Please review the issues above.
ℹ️  For installation help, see: ops/CRON.md
```

### Exit Codes

The verification script returns:
- **Exit code 0**: All checks passed, cron job should be working
- **Exit code 1**: Some checks failed, review the issues above

### Troubleshooting with Verification

Use the verification script to diagnose common issues:

```bash
# Check if cron job is installed
./scripts/check_cron.sh

# If script is not executable
chmod +x /opt/es-inventory-hub/scripts/run_ninja_daily.sh

# If cron job is missing, install it
crontab -e
# Add: 10 2 * * * /opt/es-inventory-hub/scripts/run_ninja_daily.sh >> /var/log/es-inventory-hub/ninja_daily.log 2>&1

# Check again
./scripts/check_cron.sh
```

# QBR Collector Systemd Service & Timer

This directory contains systemd service and timer files for automated QBR metrics collection.

## Files

- `qbr-collector.service` - Systemd service that runs the QBR collector
- `qbr-collector.timer` - Systemd timer that schedules daily collection at 10:30pm Central Time

## Schedule

- **Frequency**: Daily
- **Time**: 10:30pm America/Chicago (Central Time)
- **What it collects**: Current month metrics from NinjaOne and ConnectWise

## Installation

### 1. Copy service files to systemd directory

```bash
sudo cp /opt/es-inventory-hub/systemd/qbr-collector.service /etc/systemd/system/
sudo cp /opt/es-inventory-hub/systemd/qbr-collector.timer /etc/systemd/system/
```

### 2. Reload systemd daemon

```bash
sudo systemctl daemon-reload
```

### 3. Enable the timer (starts on boot)

```bash
sudo systemctl enable qbr-collector.timer
```

### 4. Start the timer immediately

```bash
sudo systemctl start qbr-collector.timer
```

## Verification

### Check timer status

```bash
sudo systemctl status qbr-collector.timer
```

### List all timers and find next run time

```bash
systemctl list-timers qbr-collector.timer
```

### Check service logs

```bash
# View recent logs
sudo journalctl -u qbr-collector.service -n 100

# Follow logs in real-time
sudo journalctl -u qbr-collector.service -f

# View logs for specific date
sudo journalctl -u qbr-collector.service --since "2025-01-15" --until "2025-01-16"
```

## Manual Execution

### Run the collector manually (for testing)

```bash
# Run directly
source /opt/es-inventory-hub/.venv/bin/activate
python3 -m collectors.qbr.collect_all

# Or via systemd (same as scheduled run)
sudo systemctl start qbr-collector.service
```

### Run for specific period

```bash
source /opt/es-inventory-hub/.venv/bin/activate
python3 -m collectors.qbr.collect_all --period 2025-01
```

### Skip specific collectors

```bash
# Skip NinjaOne
python3 -m collectors.qbr.collect_all --skip-ninja

# Skip ConnectWise
python3 -m collectors.qbr.collect_all --skip-connectwise
```

## Disabling

### Stop the timer temporarily

```bash
sudo systemctl stop qbr-collector.timer
```

### Disable timer (prevent starting on boot)

```bash
sudo systemctl disable qbr-collector.timer
```

### Completely remove

```bash
sudo systemctl stop qbr-collector.timer
sudo systemctl disable qbr-collector.timer
sudo rm /etc/systemd/system/qbr-collector.{service,timer}
sudo systemctl daemon-reload
```

## Troubleshooting

### Timer not running

1. Check if timer is enabled and active:
   ```bash
   sudo systemctl status qbr-collector.timer
   ```

2. Check for errors in timer logs:
   ```bash
   sudo journalctl -u qbr-collector.timer
   ```

### Service failing

1. Check service logs:
   ```bash
   sudo journalctl -u qbr-collector.service -n 100
   ```

2. Run manually to see errors:
   ```bash
   source /opt/es-inventory-hub/.venv/bin/activate
   python3 -m collectors.qbr.collect_all
   ```

3. Verify environment file exists:
   ```bash
   ls -l /opt/es-inventory-hub/.env
   ```

4. Test database connectivity:
   ```bash
   source /opt/es-inventory-hub/.venv/bin/activate
   python3 -c "from storage.database import Database; db = Database(); print('DB OK')"
   ```

### Wrong timezone

The timer uses `America/Chicago` timezone. If this is incorrect:

1. Edit `/etc/systemd/system/qbr-collector.timer`
2. Change `America/Chicago` to your timezone
3. Reload: `sudo systemctl daemon-reload`
4. Restart timer: `sudo systemctl restart qbr-collector.timer`

## Monitoring

### Check last run time

```bash
systemctl list-timers qbr-collector.timer
```

Output shows:
- `NEXT`: When the timer will run next
- `LEFT`: How much time until next run
- `LAST`: When it last ran
- `PASSED`: How long ago it last ran

### Check last run status

```bash
sudo systemctl status qbr-collector.service
```

### Get execution history

```bash
# Last 10 runs
sudo journalctl -u qbr-collector.service -n 10 --no-pager

# All runs today
sudo journalctl -u qbr-collector.service --since today
```

## Production Deployment Notes

Per `PLANNING_DECISIONS.md`:

1. **Initial deployment**: Timer should start **disabled**
2. **Manual backfill**: Run manual collection for historical months first
3. **Review results**: Validate data before enabling automated collection
4. **Enable timer**: Only after manual validation approves the results

### Initial deployment sequence:

```bash
# 1. Install but don't enable
sudo cp systemd/*.{service,timer} /etc/systemd/system/
sudo systemctl daemon-reload

# 2. Run manual backfill (example for 2024)
source /opt/es-inventory-hub/.venv/bin/activate
python3 -m collectors.qbr.ninja_main --period 2024-01
python3 -m collectors.qbr.connectwise_main --period 2024-01
# Repeat for each month...

# 3. Review results in database

# 4. Enable timer only after approval
sudo systemctl enable qbr-collector.timer
sudo systemctl start qbr-collector.timer
```

## See Also

- `docs/qbr/IMPLEMENTATION_GUIDE.md` - Full implementation details
- `docs/qbr/PLANNING_DECISIONS.md` - Architecture decisions
- `collectors/qbr/README.md` - Collector documentation

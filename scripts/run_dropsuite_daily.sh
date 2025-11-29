#!/bin/bash
set -euo pipefail

# Ensure log directory exists
mkdir -p /var/log/es-inventory-hub

# Log file path
LOG_FILE="/var/log/es-inventory-hub/dropsuite_daily.log"

# Function to log with timestamp
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Log start
log_message "Starting Dropsuite daily collection"

# Load environment variables
set -a
. /opt/es-inventory-hub/.env
. /opt/shared-secrets/api-secrets.env
set +a

# Activate virtual environment
source /opt/es-inventory-hub/.venv/bin/activate

# Run the collector
if python3 -m collectors.dropsuite.main; then
    log_message "Dropsuite collection finished OK"
    exit 0
else
    EXIT_CODE=$?
    log_message "Dropsuite collection FAILED with exit code $EXIT_CODE"
    exit $EXIT_CODE
fi

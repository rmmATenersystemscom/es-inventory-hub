#!/bin/bash
# ES Inventory Hub Cross-Vendor Checks Script
# Runs cross-vendor consistency checks between Ninja and ThreatLocker

set -e

# Configuration
SCRIPT_DIR="/opt/es-inventory-hub"
LOG_DIR="/var/log/es-inventory-hub"
LOG_FILE="$LOG_DIR/cross_vendor_checks.log"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Function to log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "Starting cross-vendor consistency checks..."

# Change to project directory
cd "$SCRIPT_DIR"

# Load environment variables
set -a
. /opt/es-inventory-hub/.env
set +a

# Run cross-vendor checks via API (only cross-vendor, not collectors)
log "Triggering cross-vendor checks via API..."
RESPONSE=$(curl -s -X POST http://localhost:5400/api/collectors/run \
    -H "Content-Type: application/json" \
    -d '{"run_cross_vendor": true, "run_ninja": false, "run_threatlocker": false}')

# Check if the API call was successful
if echo "$RESPONSE" | grep -q '"success": true'; then
    log "Cross-vendor checks completed successfully"
    
    # Extract and log the results
    EXCEPTIONS=$(echo "$RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    results = data.get('results', {}).get('cross_vendor', {}).get('results', {})
    total = sum(v for k, v in results.items() if k != 'DATA_QUALITY_ISSUES')
    print(f'Total exceptions found: {total}')
    for k, v in results.items():
        if k != 'DATA_QUALITY_ISSUES':
            print(f'  {k}: {v}')
except:
    print('Could not parse results')
")
    log "$EXCEPTIONS"
    
    # Log the full response for debugging
    log "Full API response: $RESPONSE"
    
else
    log "ERROR: Cross-vendor checks failed"
    log "API Response: $RESPONSE"
    exit 1
fi

log "Cross-vendor consistency checks completed"
exit 0

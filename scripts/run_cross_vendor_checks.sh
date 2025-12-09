#!/bin/bash
# ES Inventory Hub Cross-Vendor Checks Script (Fixed)
# Runs cross-vendor consistency checks between Ninja and ThreatLocker

set -e

# Configuration
SCRIPT_DIR="/opt/es-inventory-hub"
LOG_DIR="/var/log/es-inventory-hub"
LOG_FILE="$LOG_DIR/cross_vendor_checks.log"

# Ensure log directory exists and has proper permissions
mkdir -p "$LOG_DIR"

# Function to log with timestamp (without tee to avoid permission issues)
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE" 2>/dev/null || true
}

log "Starting cross-vendor consistency checks..."

# Change to project directory
cd "$SCRIPT_DIR"

# Load environment variables
set -a
. /opt/shared-secrets/api-secrets.env
. /opt/es-inventory-hub/.env
set +a

# Run cross-vendor checks via API (only cross-vendor, not collectors)
log "Triggering cross-vendor checks via API..."
RESPONSE=$(curl -k -s -X POST https://localhost:5400/api/collectors/cross-vendor/run \
    -H "Content-Type: application/json" \
    -d '{}')

# Check if the API call was successful
if echo "$RESPONSE" | grep -q '"success": true'; then
    log "Cross-vendor checks completed successfully"
    
    # Extract and log the results
    EXCEPTIONS=$(echo "$RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    output = data.get('output', '')
    print(output)
except:
    print('Could not parse results')
")
    log "$EXCEPTIONS"
    
else
    log "ERROR: Cross-vendor checks failed"
    log "API Response: $RESPONSE"
    exit 1
fi

log "Cross-vendor consistency checks completed"
exit 0

#!/bin/bash
set -euo pipefail

# Ensure log directory exists
mkdir -p /var/log/es-inventory-hub

# Log file path
LOG_FILE="/var/log/es-inventory-hub/threatlocker_daily.log"

# Function to log with timestamp
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Log start
log_message "Starting ThreatLocker daily collection"

# Load environment variables
set -a
. /opt/es-inventory-hub/.env
set +a

# Activate virtual environment
source /opt/es-inventory-hub/.venv/bin/activate

# Run the collector
if python3 -m collectors.threatlocker.main; then
    log_message "ThreatLocker collection finished OK"
    
    # Run cross-vendor checks after successful collection
    log_message "Starting cross-vendor consistency checks"
    if python3 -c "
import sys
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from collectors.checks.cross_vendor import run_cross_vendor_checks

# Connect to database
import os
dsn = os.getenv('DB_DSN', 'postgresql://postgres:mK2D282lRrs6bTpXWe7@localhost:5432/es_inventory_hub')
engine = create_engine(dsn)
Session = sessionmaker(bind=engine)
session = Session()

try:
    results = run_cross_vendor_checks(session, date.today())
    total_variances = sum([
        results.get('MISSING_NINJA', 0),
        results.get('DUPLICATE_TL', 0), 
        results.get('SITE_MISMATCH', 0),
        results.get('SPARE_MISMATCH', 0),
        results.get('DISPLAY_NAME_MISMATCH', 0)
    ])
    print(f'Cross-vendor checks completed: {total_variances} variances found')
    session.close()
except Exception as e:
    print(f'Cross-vendor checks failed: {e}')
    session.close()
    sys.exit(1)
"; then
        log_message "Cross-vendor checks completed successfully"
    else
        EXIT_CODE=$?
        log_message "Cross-vendor checks FAILED with exit code $EXIT_CODE"
        # Don't exit here - collection was successful, just variance checks failed
    fi
    
    exit 0
else
    EXIT_CODE=$?
    log_message "ThreatLocker collection FAILED with exit code $EXIT_CODE"
    exit $EXIT_CODE
fi

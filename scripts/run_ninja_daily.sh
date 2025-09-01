#!/bin/sh
#
# Daily Ninja collector runner script
# This script is designed to be run from cron daily at 02:10
#

set -euo pipefail

# Configuration
REPO_ROOT="/opt/es-inventory-hub"
ENV_FILE="/opt/dashboard-project/es-dashboards/.env"
VENV_PATH="${REPO_ROOT}/.venv"
LOG_DIR="/var/log/es-inventory-hub"
LOG_FILE="${LOG_DIR}/ninja_daily.log"

# Create log directory if it doesn't exist
mkdir -p "${LOG_DIR}"

# Function to log with timestamp
log_with_timestamp() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1"
}

# Change to repository root
cd "${REPO_ROOT}"

# Log start of run
log_with_timestamp "=== Starting Ninja daily collection ===" >> "${LOG_FILE}"

# Source the shared environment file
if [ ! -f "${ENV_FILE}" ]; then
    log_with_timestamp "ERROR: Environment file not found: ${ENV_FILE}" >> "${LOG_FILE}"
    exit 1
fi

log_with_timestamp "Sourcing environment from ${ENV_FILE}" >> "${LOG_FILE}"
set -a  # Export all variables
. "${ENV_FILE}"
set +a  # Stop exporting

# Activate virtual environment
if [ ! -d "${VENV_PATH}" ]; then
    log_with_timestamp "ERROR: Virtual environment not found: ${VENV_PATH}" >> "${LOG_FILE}"
    exit 1
fi

log_with_timestamp "Activating virtual environment: ${VENV_PATH}" >> "${LOG_FILE}"
. "${VENV_PATH}/bin/activate"

# Verify Python environment
if ! command -v python3 >/dev/null 2>&1; then
    log_with_timestamp "ERROR: python3 not found in PATH" >> "${LOG_FILE}"
    exit 1
fi

# Run the Ninja collector
log_with_timestamp "Starting Ninja collector..." >> "${LOG_FILE}"

if python3 -m collectors.ninja.main >> "${LOG_FILE}" 2>&1; then
    log_with_timestamp "Ninja collector completed successfully" >> "${LOG_FILE}"
    exit_code=0
else
    exit_code=$?
    log_with_timestamp "ERROR: Ninja collector failed with exit code ${exit_code}" >> "${LOG_FILE}"
fi

log_with_timestamp "=== Ninja daily collection finished ===" >> "${LOG_FILE}"
exit ${exit_code}

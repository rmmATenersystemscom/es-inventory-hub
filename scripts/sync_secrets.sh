#!/bin/bash
# Wrapper script to sync secrets with sudo access
#
# This script requires sudo to read /opt/shared-secrets/api-secrets.env
# Run with: bash scripts/sync_secrets.sh [OPTIONS]
# Or: sudo python3 scripts/sync_secrets.py [OPTIONS]

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Change to project directory
cd "$PROJECT_DIR" || exit 1

# Check if running as root or with sudo
if [ "$EUID" -eq 0 ]; then
    # Running as root, execute directly
    python3 "$SCRIPT_DIR/sync_secrets.py" "$@"
else
    # Not root, use sudo (will prompt for password)
    sudo python3 "$SCRIPT_DIR/sync_secrets.py" "$@"
fi


#!/bin/sh
#
# Cron job verification script for ES Inventory Hub
# Checks if the Ninja daily collection cron job is properly installed
#

set -eu

# Configuration
SCRIPT_PATH="/opt/es-inventory-hub/scripts/run_ninja_daily.sh"
LOG_FILE="/var/log/es-inventory-hub/ninja_daily.log"
CRON_PATTERN="run_ninja_daily.sh"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    printf "${GREEN}✅ %s${NC}\n" "$1"
}

print_error() {
    printf "${RED}❌ %s${NC}\n" "$1"
}

print_warning() {
    printf "${YELLOW}⚠️  %s${NC}\n" "$1"
}

print_info() {
    printf "${BLUE}ℹ️  %s${NC}\n" "$1"
}

# Function to check if script is executable
check_script_executable() {
    print_info "Checking if $SCRIPT_PATH is executable..."
    
    if [ ! -f "$SCRIPT_PATH" ]; then
        print_error "Script not found: $SCRIPT_PATH"
        return 1
    fi
    
    if [ ! -x "$SCRIPT_PATH" ]; then
        print_error "Script not executable: $SCRIPT_PATH"
        print_info "Run: chmod +x $SCRIPT_PATH"
        return 1
    fi
    
    print_success "Script is executable: $SCRIPT_PATH"
    return 0
}

# Function to check if cron job is installed
check_cron_job() {
    print_info "Checking if cron job is installed..."
    
    # Get current crontab
    if ! crontab_output=$(crontab -l 2>/dev/null); then
        print_error "No crontab found for current user"
        print_info "Install cron job with: crontab -e"
        return 1
    fi
    
    # Search for the cron job pattern
    if echo "$crontab_output" | grep -q "$CRON_PATTERN"; then
        print_success "Cron job installed"
        printf "${GREEN}Found cron line:${NC}\n"
        echo "$crontab_output" | grep "$CRON_PATTERN" | sed 's/^/  /'
        return 0
    else
        print_error "Cron job not installed"
        print_info "Install with: crontab -e and add:"
        print_info "  10 2 * * * $SCRIPT_PATH >> $LOG_FILE 2>&1"
        return 1
    fi
}

# Function to check log file
check_log_file() {
    print_info "Checking log file: $LOG_FILE"
    
    if [ ! -f "$LOG_FILE" ]; then
        print_warning "Log file not found: $LOG_FILE"
        print_info "This is normal if the cron job hasn't run yet"
        return 0
    fi
    
    if [ ! -r "$LOG_FILE" ]; then
        print_error "Log file not readable: $LOG_FILE"
        return 1
    fi
    
    print_success "Log file exists and is readable"
    
    # Show last 10 lines
    print_info "Last 10 lines of log file:"
    echo "----------------------------------------"
    tail -n 10 "$LOG_FILE" | sed 's/^/  /'
    echo "----------------------------------------"
    
    return 0
}

# Function to check log directory
check_log_directory() {
    local log_dir
    log_dir=$(dirname "$LOG_FILE")
    
    print_info "Checking log directory: $log_dir"
    
    if [ ! -d "$log_dir" ]; then
        print_warning "Log directory not found: $log_dir"
        print_info "Directory will be created when cron job runs"
        return 0
    fi
    
    if [ ! -w "$log_dir" ]; then
        print_error "Log directory not writable: $log_dir"
        return 1
    fi
    
    print_success "Log directory exists and is writable"
    return 0
}

# Main verification function
main() {
    echo "🔍 Cron Job Verification for ES Inventory Hub"
    echo "=============================================="
    echo
    
    local exit_code=0
    
    # Check script executable
    if ! check_script_executable; then
        exit_code=1
    fi
    echo
    
    # Check cron job installation
    if ! check_cron_job; then
        exit_code=1
    fi
    echo
    
    # Check log directory
    if ! check_log_directory; then
        exit_code=1
    fi
    echo
    
    # Check log file
    if ! check_log_file; then
        exit_code=1
    fi
    echo
    
    # Summary
    echo "=============================================="
    if [ $exit_code -eq 0 ]; then
        print_success "All checks passed! Cron job should be working correctly."
    else
        print_error "Some checks failed. Please review the issues above."
        print_info "For installation help, see: ops/CRON.md"
    fi
    
    exit $exit_code
}

# Run main function
main "$@"

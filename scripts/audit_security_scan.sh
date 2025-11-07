#!/bin/bash
#
# ES Inventory Hub Security Scanning Script
# Runs all automated security scans and generates reports
#
# Usage: ./scripts/audit_security_scan.sh
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REPORTS_DIR="$PROJECT_ROOT/reports"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Create reports directory
mkdir -p "$REPORTS_DIR"

echo "=========================================="
echo "ES Inventory Hub Security Scan"
echo "Timestamp: $(date)"
echo "=========================================="
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to run bandit scan
run_bandit() {
    echo -e "${YELLOW}[1/5] Running Bandit (Python Static Analysis)...${NC}"
    if command_exists bandit; then
        cd "$PROJECT_ROOT"
        bandit -r . \
            --exclude tests,venv,.venv,__pycache__,migrations,research-and-development \
            -f json \
            -o "$REPORTS_DIR/bandit-report-${TIMESTAMP}.json" 2>&1 || true
        bandit -r . \
            --exclude tests,venv,.venv,__pycache__,migrations,research-and-development \
            -f txt \
            -o "$REPORTS_DIR/bandit-report-${TIMESTAMP}.txt" 2>&1 || true
        echo -e "${GREEN}✓ Bandit scan complete${NC}"
    else
        echo -e "${RED}✗ Bandit not installed. Install with: pip install bandit${NC}"
    fi
    echo ""
}

# Function to run safety check
run_safety() {
    echo -e "${YELLOW}[2/5] Running Safety (Dependency Vulnerability Scanner)...${NC}"
    if command_exists safety; then
        cd "$PROJECT_ROOT"
        # Check main requirements
        if [ -f requirements.txt ]; then
            safety check --json --file requirements.txt > "$REPORTS_DIR/safety-main-${TIMESTAMP}.json" 2>&1 || true
            safety check --file requirements.txt > "$REPORTS_DIR/safety-main-${TIMESTAMP}.txt" 2>&1 || true
        fi
        # Check API requirements
        if [ -f api/requirements-api.txt ]; then
            safety check --json --file api/requirements-api.txt > "$REPORTS_DIR/safety-api-${TIMESTAMP}.json" 2>&1 || true
            safety check --file api/requirements-api.txt > "$REPORTS_DIR/safety-api-${TIMESTAMP}.txt" 2>&1 || true
        fi
        echo -e "${GREEN}✓ Safety scan complete${NC}"
    else
        echo -e "${RED}✗ Safety not installed. Install with: pip install safety${NC}"
    fi
    echo ""
}

# Function to run gitleaks
run_gitleaks() {
    echo -e "${YELLOW}[3/5] Running GitLeaks (Secret Detection)...${NC}"
    if command_exists gitleaks; then
        cd "$PROJECT_ROOT"
        gitleaks detect \
            --source . \
            --report-path "$REPORTS_DIR/gitleaks-report-${TIMESTAMP}.json" \
            --no-banner 2>&1 || true
        echo -e "${GREEN}✓ GitLeaks scan complete${NC}"
    else
        echo -e "${RED}✗ GitLeaks not installed. See docs/AUDIT_SCANNING_SETUP.md for installation${NC}"
    fi
    echo ""
}

# Function to run custom Python security scan
run_python_security() {
    echo -e "${YELLOW}[4/5] Running Custom Python Security Scan...${NC}"
    if [ -f "$PROJECT_ROOT/tools/security_scan.py" ]; then
        cd "$PROJECT_ROOT"
        if command_exists python3; then
            python3 tools/security_scan.py \
                --output "$REPORTS_DIR/custom-security-${TIMESTAMP}.json" 2>&1 || true
            echo -e "${GREEN}✓ Custom security scan complete${NC}"
        else
            echo -e "${RED}✗ Python3 not found${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ Custom security scan script not found (tools/security_scan.py)${NC}"
    fi
    echo ""
}

# Function to check file permissions
run_permission_check() {
    echo -e "${YELLOW}[5/5] Checking File Permissions...${NC}"
    cd "$PROJECT_ROOT"
    
    # Check for world-writable files
    find . -type f -perm -002 ! -path "./.git/*" ! -path "./venv/*" ! -path "./.venv/*" ! -path "./__pycache__/*" \
        > "$REPORTS_DIR/permissions-check-${TIMESTAMP}.txt" 2>&1 || true
    
    # Check for files with sensitive permissions
    find . -type f \( -perm -4000 -o -perm -2000 \) ! -path "./.git/*" \
        >> "$REPORTS_DIR/permissions-check-${TIMESTAMP}.txt" 2>&1 || true
    
    PERM_COUNT=$(wc -l < "$REPORTS_DIR/permissions-check-${TIMESTAMP}.txt" || echo "0")
    if [ "$PERM_COUNT" -eq 0 ]; then
        echo "No permission issues found" > "$REPORTS_DIR/permissions-check-${TIMESTAMP}.txt"
    fi
    
    echo -e "${GREEN}✓ Permission check complete${NC}"
    echo ""
}

# Function to generate summary
generate_summary() {
    echo "=========================================="
    echo "Scan Summary"
    echo "=========================================="
    echo "Reports generated in: $REPORTS_DIR"
    echo ""
    echo "Generated Reports:"
    ls -lh "$REPORTS_DIR"/*"${TIMESTAMP}"* 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}' || echo "  No reports generated"
    echo ""
    echo "Next Steps:"
    echo "1. Review reports in $REPORTS_DIR"
    echo "2. Address high/critical findings"
    echo "3. Update docs/AUDIT_SECURITY_CHECKLIST.md"
    echo "4. Document findings in docs/AUDIT_SECURITY_REPORT.md"
    echo ""
}

# Main execution
main() {
    cd "$PROJECT_ROOT"
    
    run_bandit
    run_safety
    run_gitleaks
    run_python_security
    run_permission_check
    
    generate_summary
    
    echo -e "${GREEN}Security scan complete!${NC}"
}

# Run main function
main


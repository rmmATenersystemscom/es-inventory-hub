#!/bin/bash
#
# ES Inventory Hub Secret Detection Script
# Focused secret detection using multiple methods
#
# Usage: ./scripts/audit_check_secrets.sh
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
echo "ES Inventory Hub Secret Detection Scan"
echo "Timestamp: $(date)"
echo "=========================================="
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check for common secret patterns
check_secret_patterns() {
    echo -e "${YELLOW}[1/4] Checking for common secret patterns...${NC}"
    cd "$PROJECT_ROOT"
    
    SECRET_PATTERNS=(
        "password\s*=\s*['\"][^'\"]+['\"]"
        "secret\s*=\s*['\"][^'\"]+['\"]"
        "api_key\s*=\s*['\"][^'\"]+['\"]"
        "apikey\s*=\s*['\"][^'\"]+['\"]"
        "token\s*=\s*['\"][^'\"]+['\"]"
        "credential\s*=\s*['\"][^'\"]+['\"]"
        "BEGIN\s+(RSA|DSA|EC|OPENSSH)\s+PRIVATE KEY"
        "-----BEGIN.*PRIVATE KEY-----"
    )
    
    SECRET_FOUND=0
    REPORT_FILE="$REPORTS_DIR/secret-patterns-${TIMESTAMP}.txt"
    
    echo "Scanning for secret patterns..." > "$REPORT_FILE"
    echo "==========================================" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    
    for pattern in "${SECRET_PATTERNS[@]}"; do
        # Search in Python files
        while IFS= read -r file; do
            if grep -lE "$pattern" "$file" 2>/dev/null | grep -vE "(test_|__pycache__|\.pyc)" > /dev/null; then
                echo "WARNING: Potential secret found in $file" >> "$REPORT_FILE"
                echo "Pattern: $pattern" >> "$REPORT_FILE"
                grep -nE "$pattern" "$file" >> "$REPORT_FILE" 2>/dev/null || true
                echo "" >> "$REPORT_FILE"
                SECRET_FOUND=1
            fi
        done < <(find . -type f -name "*.py" ! -path "./.git/*" ! -path "./venv/*" ! -path "./.venv/*" ! -path "./__pycache__/*" ! -path "./migrations/*" 2>/dev/null)
    done
    
    if [ $SECRET_FOUND -eq 0 ]; then
        echo "No obvious secret patterns found." >> "$REPORT_FILE"
        echo -e "${GREEN}✓ No obvious secret patterns found${NC}"
    else
        echo -e "${RED}✗ Potential secrets found! Review $REPORT_FILE${NC}"
    fi
    echo ""
}

# Function to check .env files
check_env_files() {
    echo -e "${YELLOW}[2/4] Checking .env file exposure...${NC}"
    cd "$PROJECT_ROOT"
    
    REPORT_FILE="$REPORTS_DIR/env-check-${TIMESTAMP}.txt"
    
    echo "Checking for .env files..." > "$REPORT_FILE"
    echo "==========================================" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    
    # Check if .env is in .gitignore
    if grep -q "^\.env$" .gitignore 2>/dev/null; then
        echo "✓ .env is in .gitignore" >> "$REPORT_FILE"
        echo -e "${GREEN}✓ .env is properly ignored${NC}"
    else
        echo "✗ WARNING: .env is NOT in .gitignore" >> "$REPORT_FILE"
        echo -e "${RED}✗ WARNING: .env is NOT in .gitignore${NC}"
    fi
    
    # Check for .env files in git
    if command_exists git; then
        if git ls-files | grep -q "\.env$"; then
            echo "✗ WARNING: .env files are tracked in git!" >> "$REPORT_FILE"
            git ls-files | grep "\.env$" >> "$REPORT_FILE"
            echo -e "${RED}✗ WARNING: .env files are tracked in git!${NC}"
        else
            echo "✓ No .env files tracked in git" >> "$REPORT_FILE"
            echo -e "${GREEN}✓ No .env files tracked in git${NC}"
        fi
    fi
    
    echo ""
}

# Function to run gitleaks
run_gitleaks() {
    echo -e "${YELLOW}[3/4] Running GitLeaks...${NC}"
    if command_exists gitleaks; then
        cd "$PROJECT_ROOT"
        gitleaks detect \
            --source . \
            --report-path "$REPORTS_DIR/gitleaks-secrets-${TIMESTAMP}.json" \
            --no-banner 2>&1 || true
        
        # Check if any leaks were found
        if [ -f "$REPORTS_DIR/gitleaks-secrets-${TIMESTAMP}.json" ]; then
            LEAK_COUNT=$(jq '. | length' "$REPORTS_DIR/gitleaks-secrets-${TIMESTAMP}.json" 2>/dev/null || echo "0")
            if [ "$LEAK_COUNT" -gt 0 ] && [ "$LEAK_COUNT" != "null" ]; then
                echo -e "${RED}✗ GitLeaks found $LEAK_COUNT potential secret(s)!${NC}"
            else
                echo -e "${GREEN}✓ GitLeaks found no secrets${NC}"
            fi
        fi
    else
        echo -e "${YELLOW}⚠ GitLeaks not installed. Skipping...${NC}"
    fi
    echo ""
}

# Function to check git history
check_git_history() {
    echo -e "${YELLOW}[4/4] Checking git history for secrets...${NC}"
    cd "$PROJECT_ROOT"
    
    if ! command_exists git; then
        echo -e "${YELLOW}⚠ Git not available. Skipping history check...${NC}"
        echo ""
        return
    fi
    
    REPORT_FILE="$REPORTS_DIR/git-history-secrets-${TIMESTAMP}.txt"
    
    echo "Checking git history for common secret patterns..." > "$REPORT_FILE"
    echo "==========================================" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    
    # Check for common patterns in git history
    SECRET_KEYWORDS=("password" "secret" "api_key" "token" "credential")
    FOUND_ANY=0
    
    for keyword in "${SECRET_KEYWORDS[@]}"; do
        if git log --all --source --full-history -S "$keyword" --pretty=format:"%H %s" 2>/dev/null | head -5 > /tmp/git_secrets_check.txt 2>/dev/null; then
            if [ -s /tmp/git_secrets_check.txt ]; then
                echo "Found commits with '$keyword':" >> "$REPORT_FILE"
                cat /tmp/git_secrets_check.txt >> "$REPORT_FILE"
                echo "" >> "$REPORT_FILE"
                FOUND_ANY=1
            fi
        fi
    done
    
    if [ $FOUND_ANY -eq 0 ]; then
        echo "No obvious secret-related commits found in recent history." >> "$REPORT_FILE"
        echo -e "${GREEN}✓ No obvious secrets in git history${NC}"
    else
        echo -e "${YELLOW}⚠ Review git history for potential secrets${NC}"
    fi
    
    rm -f /tmp/git_secrets_check.txt
    echo ""
}

# Function to generate summary
generate_summary() {
    echo "=========================================="
    echo "Secret Detection Summary"
    echo "=========================================="
    echo "Reports generated in: $REPORTS_DIR"
    echo ""
    echo "Generated Reports:"
    ls -lh "$REPORTS_DIR"/*"${TIMESTAMP}"* 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}' || echo "  No reports generated"
    echo ""
    echo "Next Steps:"
    echo "1. Review all secret detection reports"
    echo "2. Verify any findings are false positives"
    echo "3. Remove any actual secrets from code/history"
    echo "4. Update credentials if secrets were exposed"
    echo ""
}

# Main execution
main() {
    cd "$PROJECT_ROOT"
    
    check_secret_patterns
    check_env_files
    run_gitleaks
    check_git_history
    
    generate_summary
    
    echo -e "${GREEN}Secret detection scan complete!${NC}"
}

# Run main function
main


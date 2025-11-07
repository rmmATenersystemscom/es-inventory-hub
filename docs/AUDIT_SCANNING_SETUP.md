# Automated Security Scanning Setup Guide

**Configuration and setup for automated security scanning tools for ES Inventory Hub**

**Last Updated**: November 6, 2025  
**Status**: Active  
**Version**: v1.0.0

---

## Overview

This document provides instructions for setting up and configuring automated security scanning tools for the ES Inventory Hub project. These tools will help identify security vulnerabilities, code quality issues, and compliance problems.

## Tools Overview

### 1. Bandit (Python Static Analysis)
**Purpose**: Scan Python code for security vulnerabilities

**Installation:**
```bash
pip install bandit[toml]
```

**Configuration File**: `.bandit` (in project root)
```ini
[bandit]
exclude_dirs = tests,venv,.venv,__pycache__,migrations
skips = B101,B601
```

**Usage:**
```bash
# Scan all Python files
bandit -r . -f json -o reports/bandit-report.json

# Scan with HTML output
bandit -r . -f html -o reports/bandit-report.html

# Scan specific directory
bandit -r api/ -f json -o reports/bandit-api.json
```

---

### 2. Safety (Dependency Vulnerability Scanner)
**Purpose**: Check Python dependencies for known security vulnerabilities

**Installation:**
```bash
pip install safety
```

**Usage:**
```bash
# Check main requirements
safety check --json --file requirements.txt > reports/safety-main.json

# Check API requirements
safety check --json --file api/requirements-api.txt > reports/safety-api.json

# Check with full report
safety check --full-report --file requirements.txt
```

**Note**: Safety requires an API key for full vulnerability database access. Free tier available.

---

### 3. GitLeaks (Secret Detection)
**Purpose**: Scan git repository for leaked secrets and credentials

**Installation:**
```bash
# Download from GitHub releases
wget https://github.com/gitleaks/gitleaks/releases/download/v8.18.0/gitleaks_8.18.0_linux_x64.tar.gz
tar -xzf gitleaks_8.18.0_linux_x64.tar.gz
sudo mv gitleaks /usr/local/bin/
```

**Configuration File**: `.gitleaksignore` (optional)
```
# Ignore test files
**/test_*.py
**/tests/**
```

**Usage:**
```bash
# Scan current repository
gitleaks detect --source . --report-path reports/gitleaks-report.json

# Scan with verbose output
gitleaks detect --source . --verbose --report-path reports/gitleaks-report.json

# Scan git history
gitleaks detect --source . --no-git --report-path reports/gitleaks-history.json
```

---

### 4. SQLFluff (SQL Security Analysis)
**Purpose**: Analyze SQL queries for security issues and best practices

**Installation:**
```bash
pip install sqlfluff
```

**Configuration File**: `.sqlfluff` (in project root)
```ini
[sqlfluff]
dialect = postgres
templater = python

[sqlfluff:rules]
# Enable security-focused rules
L010 = capitalisation_policy = lower
L014 = inconsistent_capitalisation = True
```

**Usage:**
```bash
# Lint SQL in Python files (requires custom script)
python tools/sqlfluff_scan.py

# Direct SQL file linting (if SQL files exist)
sqlfluff lint --format json sql/ > reports/sqlfluff-report.json
```

---

### 5. Custom Scanning Scripts

#### Security Scan Script (`scripts/audit_security_scan.sh`)
Main orchestration script that runs all security scans.

#### Secret Check Script (`scripts/audit_check_secrets.sh`)
Focused secret detection using multiple methods.

#### Python Security Utility (`tools/security_scan.py`)
Custom Python security checks and analysis.

---

## Installation Steps

### Step 1: Install Python Security Tools
```bash
cd /opt/es-inventory-hub
source .venv/bin/activate
pip install bandit[toml] safety sqlfluff
```

### Step 2: Install GitLeaks
```bash
# Download and install GitLeaks
wget https://github.com/gitleaks/gitleaks/releases/download/v8.18.0/gitleaks_8.18.0_linux_x64.tar.gz
tar -xzf gitleaks_8.18.0_linux_x64.tar.gz
sudo mv gitleaks /usr/local/bin/
gitleaks version
```

### Step 3: Create Reports Directory
```bash
mkdir -p /opt/es-inventory-hub/reports
echo "reports/" >> .gitignore
```

### Step 4: Create Configuration Files
```bash
# Create .bandit configuration
cat > .bandit << 'EOF'
[bandit]
exclude_dirs = tests,venv,.venv,__pycache__,migrations,research-and-development
skips = B101,B601
EOF

# Create .sqlfluff configuration
cat > .sqlfluff << 'EOF'
[sqlfluff]
dialect = postgres
templater = python
EOF
```

### Step 5: Run Initial Scans
```bash
# Run all scans
./scripts/audit_security_scan.sh
```

---

## Integration with CI/CD

### GitHub Actions Example
```yaml
name: Security Scan

on: [push, pull_request]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install bandit safety
      - name: Run Bandit
        run: bandit -r . -f json -o bandit-report.json
      - name: Run Safety
        run: safety check --json --file requirements.txt
```

---

## Scheduled Scanning

### Cron Job Example
```bash
# Run security scans weekly
0 2 * * 0 cd /opt/es-inventory-hub && ./scripts/audit_security_scan.sh >> /var/log/es-inventory-hub/security-scan.log 2>&1
```

### Systemd Timer Example
Create `ops/systemd/security-scan.timer`:
```ini
[Unit]
Description=Weekly Security Scan
Requires=security-scan.service

[Timer]
OnCalendar=weekly
Persistent=true

[Install]
WantedBy=timers.target
```

---

## Report Interpretation

### Bandit Report
- **Severity Levels**: LOW, MEDIUM, HIGH
- **Test IDs**: B101-B999 (specific vulnerability types)
- **Focus Areas**: SQL injection, command injection, hardcoded secrets

### Safety Report
- **Vulnerability IDs**: CVE numbers
- **Severity**: Critical, High, Medium, Low
- **Affected Packages**: Package name and version

### GitLeaks Report
- **Rule IDs**: Specific secret patterns detected
- **File Locations**: Where secrets were found
- **Commit Hashes**: If found in git history

---

## Troubleshooting

### Bandit Issues
```bash
# If bandit fails on specific files
bandit -r . --exclude tests,venv

# Skip specific test IDs
bandit -r . --skip B101,B601
```

### Safety API Key
```bash
# Set API key for full database access
export SAFETY_API_KEY=your_key_here
safety check --file requirements.txt
```

### GitLeaks False Positives
```bash
# Add to .gitleaksignore
echo "**/test_data/**" >> .gitleaksignore
```

---

## Best Practices

1. **Run scans regularly**: Weekly or on every commit
2. **Review all findings**: Don't ignore warnings
3. **Fix high/critical issues immediately**: Prioritize by severity
4. **Document exceptions**: If a finding is a false positive, document why
5. **Keep tools updated**: Update scanning tools regularly
6. **Integrate with CI/CD**: Catch issues before merge

---

## Maintenance

### Updating Tools
```bash
pip install --upgrade bandit safety sqlfluff
# Update GitLeaks manually from GitHub releases
```

### Reviewing Reports
- Review reports in `reports/` directory
- Compare reports over time to track improvements
- Document resolved issues

---

**Version**: v1.20.0  
**Last Updated**: November 6, 2025 07:20 UTC  
**Maintainer**: ES Inventory Hub Team


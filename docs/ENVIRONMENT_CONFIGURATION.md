# Environment Configuration Guide

**Environment Variable Management for ES Inventory Hub**

---

## 🔧 **Environment Variable Sources**

### **Primary Source: Dashboard Project**
- **Location**: `/opt/dashboard-project/es-dashboards/.env`
- **Type**: Symbolic link to `/opt/shared-secrets/api-secrets.env`
- **Used By**: Systemd services, daily collection scripts, automated processes
- **Contains**: NinjaRMM and ThreatLocker API credentials

### **Local Source: ES Inventory Hub**
- **Location**: `/opt/es-inventory-hub/.env`
- **Type**: Local configuration file
- **Contains**: ConnectWise credentials and local configuration
- **Note**: Some API credentials may be duplicated here

---

## 📋 **Required Environment Variables**

### **NinjaRMM API Configuration**
```bash
# Required for Ninja collector
NINJA_CLIENT_ID=your_ninja_client_id_here
NINJA_CLIENT_SECRET=your_ninja_client_secret_here
NINJA_REFRESH_TOKEN=your_ninja_refresh_token_here
NINJA_BASE_URL=https://app.ninjarmm.com
```

### **ThreatLocker API Configuration**
```bash
# Required for ThreatLocker collector
THREATLOCKER_API_KEY=your_threatlocker_api_key
THREATLOCKER_API_SECRET=your_threatlocker_api_secret
THREATLOCKER_ORG_ID=your_threatlocker_org_id_here
```

### **Database Configuration**
```bash
# Required for database connection
DB_DSN=postgresql://username:password@hostname:port/database_name
DATABASE_URL=postgresql://username:password@hostname:port/database_name
```

### **ConnectWise Configuration**
```bash
# Optional: ConnectWise integration
CONNECTWISE_SERVER=your_connectwise_server_here
CONNECTWISE_COMPANY_ID=your_company_id_here
CONNECTWISE_CLIENT_ID=your_connectwise_client_id_here
CONNECTWISE_PUBLIC_KEY=your_connectwise_public_key_here
CONNECTWISE_PRIVATE_KEY=your_connectwise_private_key_here
```

---

## 🚀 **Manual Testing Commands**

### **Running Collectors Manually**

#### **Method 1: Source Dashboard Environment (Recommended)**
```bash
cd /opt/es-inventory-hub

# Source environment variables from dashboard project
source /opt/dashboard-project/es-dashboards/.env

# Activate virtual environment
source .venv/bin/activate

# Set database connection
export DB_DSN="postgresql://username:password@hostname:port/database_name"

# Run collectors
python3 -m collectors.ninja.main --limit 5
python3 -m collectors.threatlocker.main --limit 5
```

#### **Method 2: Explicit Environment Variables**
```bash
cd /opt/es-inventory-hub
source .venv/bin/activate

# Set all required environment variables explicitly
export NINJA_CLIENT_ID="your_ninja_client_id_here"
export NINJA_CLIENT_SECRET="your_ninja_client_secret_here"
export NINJA_REFRESH_TOKEN="your_ninja_refresh_token_here"
export DB_DSN="postgresql://username:password@hostname:port/database_name"

# Run collectors
python3 -m collectors.ninja.main --limit 5
python3 -m collectors.threatlocker.main --limit 5
```

### **Running Cross-Vendor Checks**
```bash
cd /opt/es-inventory-hub
source .venv/bin/activate
export DB_DSN="postgresql://username:password@hostname:port/database_name"

python3 -c "
from collectors.checks.cross_vendor import run_cross_vendor_checks
from common.db import SessionLocal
session = SessionLocal()
result = run_cross_vendor_checks(session)
print('Cross-vendor checks completed:', result)
session.close()
"
```

---

## 🔍 **Environment Variable Verification**

### **Check Environment Variables**
```bash
# Check if environment variables are set
echo "NINJA_CLIENT_ID: $NINJA_CLIENT_ID"
echo "NINJA_CLIENT_SECRET: $NINJA_CLIENT_SECRET"
echo "DB_DSN: $DB_DSN"

# Check from Python
python3 -c "import os; print('NINJA_CLIENT_ID:', os.getenv('NINJA_CLIENT_ID'))"
```

### **Verify Environment File Sources**
```bash
# Check dashboard project environment file
ls -la /opt/dashboard-project/es-dashboards/.env

# Check local environment file
ls -la /opt/es-inventory-hub/.env

# Check shared secrets (if accessible)
ls -la /opt/shared-secrets/api-secrets.env
```

---

## 🛠️ **Troubleshooting**

### **Common Issues**

#### **1. Missing Environment Variables**
**Error**: `Missing required NinjaRMM environment variables: NINJA_CLIENT_ID and NINJA_CLIENT_SECRET`

**Solution**:
```bash
# Source the correct environment file
source /opt/dashboard-project/es-dashboards/.env

# Verify variables are set
echo $NINJA_CLIENT_ID
```

#### **2. Environment Variables Not Passed to Python**
**Error**: Environment variables are set in shell but not available in Python

**Solution**:
```bash
# Explicitly export variables
export NINJA_CLIENT_ID="your_client_id"
export NINJA_CLIENT_SECRET="your_client_secret"

# Or use explicit environment in Python
python3 -c "import os; print(os.getenv('NINJA_CLIENT_ID'))"
```

#### **3. Database Connection Issues**
**Error**: `Database connection string not found`

**Solution**:
```bash
# Set database connection string
export DB_DSN="postgresql://username:password@hostname:port/database_name"

# Test database connection
python3 -c "from common.db import engine; print('Database connected:', engine)"
```

#### **4. Environment File Not Found**
**Error**: `No such file or directory: /opt/dashboard-project/es-dashboards/.env`

**Solution**:
```bash
# Check if file exists
ls -la /opt/dashboard-project/es-dashboards/.env

# Check if symlink is broken
readlink /opt/dashboard-project/es-dashboards/.env

# Use local environment file as fallback
source /opt/es-inventory-hub/.env
```

---

## 🔄 **Systemd Service Configuration**

### **Service Environment Files**
The systemd services are configured to use the dashboard project's environment file:

```ini
# /opt/es-inventory-hub/ops/systemd/ninja-collector.service
[Service]
EnvironmentFile=/opt/dashboard-project/es-dashboards/.env
ExecStart=/bin/bash -lc '/opt/es-inventory-hub/scripts/run_ninja_daily.sh'
```

### **Script Environment Loading**
The daily collection scripts also source the dashboard environment:

```bash
# /opt/es-inventory-hub/scripts/run_ninja_daily.sh
set -a
. /opt/dashboard-project/es-dashboards/.env
set +a
```

---

## 📁 **File Locations Summary**

| File | Location | Purpose | Used By |
|------|----------|---------|---------|
| **Primary .env** | `/opt/dashboard-project/es-dashboards/.env` | API credentials | Systemd services, scripts |
| **Local .env** | `/opt/es-inventory-hub/.env` | Local config | Manual testing, local development |
| **Shared Secrets** | `/opt/shared-secrets/api-secrets.env` | Source of truth | Dashboard project symlink |

---

## ⚠️ **Important Notes**

### **Security Considerations**
- **Environment files contain sensitive credentials**
- **Never commit .env files to version control**
- **Use appropriate file permissions (600 or 640)**
- **Regularly rotate API keys and secrets**

### **Maintenance**
- **Primary source**: Always use dashboard project's .env for production
- **Local development**: Can use local .env for testing
- **Updates**: Update shared secrets file, not individual .env files
- **Backup**: Ensure environment files are backed up securely

---

## 📚 **Related Documentation**

- **[Main README](../README.md)** - Project overview and environment setup
- **[Systemd Configuration](./SYSTEMD.md)** - Service configuration and environment loading
- **[Cron Configuration](./CRON.md)** - Alternative scheduling with environment setup
- **[API Documentation](../api/README.md)** - API server environment requirements

---

**Last Updated**: September 22, 2025  
**Status**: ✅ **ACTIVE** - Environment configuration in use

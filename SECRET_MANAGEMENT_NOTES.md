# Secret Management Notes for Dashboard Project

## Shared Secret Management

This project shares API secrets with the es-inventory-hub project using a centralized approach to avoid duplication and maintain security.

### Shared Secrets Location
**File:** `/opt/shared-secrets/api-secrets.env`

### Setup Instructions

```bash
# Create shared secrets directory (if not exists)
sudo mkdir -p /opt/shared-secrets

# Copy current secrets to shared location (if not already done)
sudo cp /opt/dashboard-project/es-dashboards/.env /opt/shared-secrets/api-secrets.env

# Create dedicated group for secrets access
sudo groupadd -f es-secrets
sudo usermod -a -G es-secrets $USER

# Set secure permissions (root owner, es-secrets group, 640 permissions)
sudo chown root:es-secrets /opt/shared-secrets/api-secrets.env
sudo chmod 640 /opt/shared-secrets/api-secrets.env

# Create symlink in this project (replace existing .env)
rm /opt/dashboard-project/es-dashboards/.env
ln -s /opt/shared-secrets/api-secrets.env /opt/dashboard-project/es-dashboards/.env
```

### Security Considerations

- **File Permissions:** 640 (owner read/write, group read)
- **Ownership:** root:es-secrets (dedicated group for authorized users)
- **Access Control:** Only users in es-secrets group can read the file
- **Audit Monitoring:** Monitor access with auditd
- **Backup Strategy:** Secure backup of secrets file

### Monitoring Access

```bash
# Monitor access to shared secrets
auditctl -w /opt/shared-secrets/api-secrets.env -p wa -k shared_secrets

# Check audit logs
ausearch -k shared_secrets
```

### Migration Path

**Current (Phase 1):** Shared symlinked file
- Both projects symlink to `/opt/shared-secrets/api-secrets.env`
- Simple to implement and maintain
- Single source of truth

**Future (Phase 2):** HashiCorp Vault or AWS Secrets Manager
- Centralized secret management
- Automatic rotation
- Access control and audit logs
- Environment-specific secrets

**Future (Phase 3):** Automated secret rotation and access controls
- Regular secret rotation
- Fine-grained access controls
- Integration with CI/CD pipelines

### Troubleshooting

**If .env file is not found:**
```bash
# Check if symlink exists
ls -la /opt/dashboard-project/es-dashboards/.env

# Recreate symlink if needed
ln -s /opt/shared-secrets/api-secrets.env /opt/dashboard-project/es-dashboards/.env
```

**If permissions are wrong:**
```bash
# Fix permissions
sudo chown root:es-secrets /opt/shared-secrets/api-secrets.env
sudo chmod 640 /opt/shared-secrets/api-secrets.env
```

**If secrets are not loading:**
```bash
# Check file exists and is readable
sudo cat /opt/shared-secrets/api-secrets.env

# Verify symlink target
readlink -f /opt/dashboard-project/es-dashboards/.env
```

### Environment Variables

The shared secrets file should contain:
```bash
# NinjaRMM API Configuration
NINJA_CLIENT_ID=your_ninja_client_id_here
NINJA_BASE_URL=https://eu.ninjarmm.com
NINJA_TIMEOUT=30

# ThreatLocker API Configuration
THREATLOCKER_API_KEY=your_threatlocker_api_key_here
THREATLOCKER_BASE_URL=https://api.threatlocker.com
THREATLOCKER_TIMEOUT=30

# Database Configuration (if shared)
DATABASE_URL=postgresql://es_inventory_user:password@localhost/es_inventory_db
DB_HOST=localhost
DB_PORT=5432
DB_NAME=es_inventory_db
DB_USER=es_inventory_user
DB_PASSWORD=your_secure_password_here
```

### Notes for Future AI Assistants

- Both projects now share secrets from `/opt/shared-secrets/api-secrets.env`
- Always check symlink status when troubleshooting environment issues
- Use `sudo` for file operations on shared secrets
- Monitor access with auditd for security compliance
- Consider migrating to proper secret management service for production

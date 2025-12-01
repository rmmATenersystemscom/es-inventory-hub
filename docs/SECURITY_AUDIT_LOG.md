# Security Audit Log

This document tracks security audits, hardening changes, and remediation actions performed on the ES Inventory Hub server infrastructure.

---

## Audit: 2025-11-30 - Server Security Hardening

**Server:** goldberry (192.168.99.246)
**Performed by:** Claude Code AI Assistant
**Date:** November 30, 2025

### Summary

Comprehensive security audit of inbound ports and firewall configuration, followed by implementation of hardening measures for HIGH and MEDIUM risk items.

### Findings Before Remediation

| Risk Level | Issue | Status |
|------------|-------|--------|
| HIGH | PostgreSQL pg_hba.conf allowed connections from 0.0.0.0/0 (any IP) | FIXED |
| HIGH | SSH open to Anywhere with password authentication enabled | FIXED |
| MEDIUM | No fail2ban brute-force protection | NOT ADDRESSED |
| MEDIUM | Port 5400 (API) open to Anywhere | FIXED |
| MEDIUM | Port 443 allowed but nothing listening | KEPT (future use) |
| MEDIUM | PostgreSQL listening on all interfaces | NOT ADDRESSED |
| LOW | X11 Forwarding enabled | FIXED |
| LOW | PermitRootLogin not explicitly disabled | FIXED |

### Changes Implemented

#### 1. SSH Hardening

**Files Modified:**
- `/etc/ssh/sshd_config` - Added hardening settings
- `/etc/ssh/sshd_config.d/10-security-hardening.conf` - Created to override cloud-init defaults

**Settings Applied:**
```
PasswordAuthentication no
PermitRootLogin no
X11Forwarding no
```

**Verification:**
```bash
$ sshd -T | grep -E "passwordauth|permitroot|x11forward"
permitrootlogin no
passwordauthentication no
x11forwarding no
```

#### 2. UFW Firewall - SSH Access Restricted

**Before:**
```
22/tcp (OpenSSH)    ALLOW IN    Anywhere
```

**After:**
```
22/tcp    ALLOW    192.168.99.0/24    # SSH from local subnet
22/tcp    ALLOW    192.168.5.0/24     # SSH from office
22/tcp    ALLOW    10.9.8.0/24        # SSH from VPN
```

#### 3. PostgreSQL pg_hba.conf - Access Restricted

**File Modified:** `/etc/postgresql/16/main/pg_hba.conf`

**Before:**
```
host    es_inventory_hub    postgres    0.0.0.0/0    md5
```

**After:**
```
host    es_inventory_hub    postgres    192.168.99.0/24    scram-sha-256
host    es_inventory_hub    postgres    192.168.5.0/24     scram-sha-256
host    es_inventory_hub    postgres    10.9.8.0/24        scram-sha-256
```

**Notes:**
- Changed authentication from `md5` to `scram-sha-256` (more secure)
- Restricted to only authorized subnets

#### 4. UFW Firewall - Port 5400 (API) Restricted

**Before:**
```
5400    ALLOW IN    Anywhere
```

**After:**
```
5400       ALLOW    192.168.99.245
5400       ALLOW    192.168.5.0/24
5400       ALLOW    10.9.8.0/24
5400/tcp   ALLOW    192.168.99.0/24    # API from local subnet
```

### Authorized Networks

All services are now restricted to these networks only:

| Network | Purpose |
|---------|---------|
| 192.168.99.0/24 | Local subnet (server network) |
| 192.168.5.0/24 | Office network |
| 10.9.8.0/24 | VPN network |

### Items Not Addressed (Future Consideration)

1. **fail2ban** - Not installed. Recommend installing for brute-force protection.
2. **PostgreSQL listen_addresses** - Still set to `'*'`. Consider changing to `'localhost'` if remote DB access not needed.

### Rollback Instructions

If SSH access is lost:
1. Access server via Proxmox/VMware console
2. Revert SSH config: `sudo rm /etc/ssh/sshd_config.d/10-security-hardening.conf`
3. Restart SSH: `sudo systemctl restart ssh`
4. Re-add UFW rule: `sudo ufw allow OpenSSH`

### Verification Commands

```bash
# Check UFW rules
sudo ufw status numbered

# Check SSH effective settings
sudo sshd -T | grep -E "passwordauth|permitroot|x11forward"

# Check PostgreSQL pg_hba.conf
sudo grep "es_inventory_hub" /etc/postgresql/16/main/pg_hba.conf | grep -v "^#"

# Test PostgreSQL connection
PGPASSWORD='[password]' psql -h localhost -U postgres -d es_inventory_hub -c "SELECT 1;"
```

---

**Version**: v1.28.0
**Last Updated**: December 01, 2025 01:26 UTC
**Maintainer**: ES Inventory Hub Team

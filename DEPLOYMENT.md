# ES Inventory Hub - Deployment Guide

This guide covers all deployment options for the ES Inventory Hub project.

## Prerequisites

### System Requirements

- **OS**: Ubuntu 20.04+ or similar Linux distribution
- **Python**: 3.9+
- **PostgreSQL**: 16+ (can be containerized or native)
- **Docker**: 20.10+ (for containerized deployment)
- **Memory**: 2GB+ RAM
- **Storage**: 10GB+ free space

### Required Software

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and pip
sudo apt install -y python3 python3-pip python3-venv

# Install PostgreSQL (if not using Docker)
sudo apt install -y postgresql postgresql-contrib

# Install Docker (for containerized deployment)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

## Deployment Options

### Option 1: Docker Compose (Development/Testing)

Best for development, testing, and small-scale deployments.

#### Quick Start

```bash
# Clone the repository
git clone <repository-url>
cd es-inventory-hub

# Set up shared secrets (if not already done)
sudo mkdir -p /opt/shared-secrets
sudo cp /path/to/your/api-secrets.env /opt/shared-secrets/api-secrets.env
sudo chown root:es-secrets /opt/shared-secrets/api-secrets.env
sudo chmod 640 /opt/shared-secrets/api-secrets.env

# Start services
docker-compose up -d

# Check status
docker-compose ps
docker-compose logs -f dashboard
```

#### Manual Collector Runs

```bash
# Run NinjaRMM collector
docker-compose run --rm ninja-collector

# Run ThreatLocker collector
docker-compose run --rm threatlocker-collector

# Run data processing
docker-compose run --rm data-processor
```

### Option 2: Production Deployment (Recommended)

Best for production environments with automated scheduling.

#### Step 1: Prepare the Environment

```bash
# Clone the repository
git clone <repository-url>
cd es-inventory-hub

# Set up Python virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set up shared secrets
sudo mkdir -p /opt/shared-secrets
sudo cp /path/to/your/api-secrets.env /opt/shared-secrets/api-secrets.env
sudo chown root:es-secrets /opt/shared-secrets/api-secrets.env
sudo chmod 640 /opt/shared-secrets/api-secrets.env

# Create symlink
ln -s /opt/shared-secrets/api-secrets.env .env
```

#### Step 2: Database Setup

```bash
# Create database and user
sudo -u postgres psql
CREATE DATABASE es_inventory_db;
CREATE USER es_inventory_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE es_inventory_db TO es_inventory_user;
\q

# Run migrations
cd storage
alembic upgrade head
```

#### Step 3: Deploy Services

```bash
# Build Docker images
./docker/build.sh

# Deploy with systemd services
sudo ./docker/deploy.sh
```

#### Step 4: Verify Deployment

```bash
# Check service status
systemctl status es-inventory-dashboard.service
systemctl list-timers es-inventory-*.timer

# Test dashboard
curl http://localhost:5000/api/health

# View logs
journalctl -u es-inventory-dashboard -f
```

## Configuration

### Environment Variables

The following environment variables are required:

```bash
# Database Configuration
DATABASE_URL=postgresql://es_inventory_user:password@localhost/es_inventory_db
DB_HOST=localhost
DB_PORT=5432
DB_NAME=es_inventory_db
DB_USER=es_inventory_user
DB_PASSWORD=your_secure_password

# NinjaRMM API Configuration
NINJA_CLIENT_ID=your_ninja_client_id
NINJA_CLIENT_SECRET=your_ninja_client_secret
NINJA_BASE_URL=https://app.ninjarmm.com

# ThreatLocker API Configuration
THREATLOCKER_API_KEY=your_threatlocker_api_key
THREATLOCKER_API_BASE_URL=https://portalapi.g.threatlocker.com
THREATLOCKER_ORGANIZATION_ID=your_org_id

# Dashboard Configuration
DASHBOARD_PORT=5000
FLASK_DEBUG=False
```

### Secret Management

The project uses shared secrets stored in `/opt/shared-secrets/api-secrets.env`:

```bash
# Create shared secrets directory
sudo mkdir -p /opt/shared-secrets

# Create dedicated group
sudo groupadd -f es-secrets
sudo usermod -a -G es-secrets $USER

# Set up secrets file
sudo cp your-secrets.env /opt/shared-secrets/api-secrets.env
sudo chown root:es-secrets /opt/shared-secrets/api-secrets.env
sudo chmod 640 /opt/shared-secrets/api-secrets.env

# Create symlink in project
ln -s /opt/shared-secrets/api-secrets.env .env
```

## Service Management

### Systemd Services

The deployment creates the following services:

- **es-inventory-dashboard.service**: Flask dashboard (port 5000)
- **es-inventory-ninja.service**: NinjaRMM collector (manual run)
- **es-inventory-threatlocker.service**: ThreatLocker collector (manual run)
- **es-inventory-ninja.timer**: Daily NinjaRMM collection at 2 AM
- **es-inventory-threatlocker.timer**: Daily ThreatLocker collection at 3 AM

### Service Commands

```bash
# Check service status
systemctl status es-inventory-dashboard.service
systemctl list-timers es-inventory-*.timer

# View logs
journalctl -u es-inventory-dashboard -f
journalctl -u es-inventory-ninja -f
journalctl -u es-inventory-threatlocker -f

# Manual collector runs
systemctl start es-inventory-ninja.service
systemctl start es-inventory-threatlocker.service

# Restart services
systemctl restart es-inventory-dashboard.service

# Disable services
systemctl disable es-inventory-ninja.timer
systemctl disable es-inventory-threatlocker.timer
```

## Monitoring and Logging

### Health Checks

The dashboard provides a health check endpoint:

```bash
curl http://localhost:5000/api/health
```

Response:
```json
{
  "status": "healthy",
  "database": "connected",
  "stats": {
    "sites": 5,
    "devices": 150,
    "snapshots": 300
  },
  "timestamp": "2024-03-15T10:30:00Z"
}
```

### Log Monitoring

```bash
# View real-time logs
journalctl -u es-inventory-dashboard -f
journalctl -u es-inventory-ninja -f

# View logs for specific time period
journalctl -u es-inventory-dashboard --since "1 hour ago"

# View error logs only
journalctl -u es-inventory-dashboard -p err
```

### Performance Monitoring

```bash
# Check system resources
htop
df -h
free -h

# Check database connections
sudo -u postgres psql -c "SELECT count(*) FROM pg_stat_activity;"

# Check service resource usage
systemctl show es-inventory-dashboard.service --property=MemoryCurrent
```

## Troubleshooting

### Common Issues

#### 1. Database Connection Failed

```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Check connection string
grep DATABASE_URL .env

# Test connection
psql $DATABASE_URL -c "SELECT 1;"
```

#### 2. API Authentication Errors

```bash
# Check API keys
grep -E "(NINJA_CLIENT_ID|THREATLOCKER_API_KEY)" .env

# Test API connections
python -c "from collectors.ninja.client import NinjaRMMClient; NinjaRMMClient().test_connection()"
```

#### 3. Service Won't Start

```bash
# Check service status
systemctl status es-inventory-dashboard.service

# View detailed logs
journalctl -u es-inventory-dashboard -n 50

# Check file permissions
ls -la /opt/es-inventory-hub/
ls -la /opt/shared-secrets/
```

#### 4. Dashboard Not Accessible

```bash
# Check if service is running
systemctl status es-inventory-dashboard.service

# Check port binding
netstat -tlnp | grep 5000

# Check firewall
sudo ufw status
sudo ufw allow 5000
```

### Recovery Procedures

#### Service Recovery

```bash
# Restart failed service
systemctl restart es-inventory-dashboard.service

# Reset failed timer
systemctl reset-failed es-inventory-ninja.timer

# Re-enable services
systemctl enable es-inventory-dashboard.service
systemctl enable es-inventory-ninja.timer
```

#### Data Recovery

```bash
# Backup database
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore database
psql $DATABASE_URL < backup_file.sql

# Re-run data processing
python scripts/process_data.py
```

## Security Considerations

### File Permissions

```bash
# Secure project directory
sudo chown -R es-inventory:es-inventory /opt/es-inventory-hub
sudo chmod -R 755 /opt/es-inventory-hub

# Secure secrets
sudo chown root:es-secrets /opt/shared-secrets/api-secrets.env
sudo chmod 640 /opt/shared-secrets/api-secrets.env
```

### Network Security

```bash
# Configure firewall
sudo ufw allow 5000/tcp  # Dashboard
sudo ufw allow 5432/tcp  # PostgreSQL (if external)

# Use reverse proxy (recommended)
sudo apt install nginx
# Configure nginx to proxy to localhost:5000
```

### Service Security

The systemd services include security hardening:

- `NoNewPrivileges=true`: Prevents privilege escalation
- `PrivateTmp=true`: Isolated temporary directories
- `ProtectSystem=strict`: Protects system directories
- `ProtectHome=true`: Protects home directories

## Backup and Maintenance

### Regular Backups

```bash
#!/bin/bash
# backup.sh - Daily backup script

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/backups/es-inventory-hub"

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup database
pg_dump $DATABASE_URL > $BACKUP_DIR/db_backup_$DATE.sql

# Backup configuration
cp /opt/shared-secrets/api-secrets.env $BACKUP_DIR/secrets_$DATE.env

# Compress backups
gzip $BACKUP_DIR/db_backup_$DATE.sql
gzip $BACKUP_DIR/secrets_$DATE.env

# Clean old backups (keep 30 days)
find $BACKUP_DIR -name "*.gz" -mtime +30 -delete
```

### Maintenance Tasks

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Update Python dependencies
pip install -r requirements.txt --upgrade

# Restart services after updates
systemctl restart es-inventory-dashboard.service

# Check for disk space
df -h
du -sh /opt/es-inventory-hub/
```

## Support

For support and troubleshooting:

1. Check the logs: `journalctl -u es-inventory-* -f`
2. Verify configuration: Check `.env` file and database connection
3. Test individual components: Run collectors manually
4. Check system resources: Monitor CPU, memory, and disk usage

The project includes comprehensive logging and health checks to help identify and resolve issues quickly.

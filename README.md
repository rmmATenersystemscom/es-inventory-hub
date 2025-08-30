# ES Inventory Hub

**Current Version**: v1.0.0 (stable)

Historical device inventory hub for Ener Systems — collects daily NinjaRMM & ThreatLocker snapshots, stores in PostgreSQL, and powers dashboards to compare today vs last month.

## Features

- **Daily Data Collection**: Automated collection from NinjaRMM and ThreatLocker APIs
- **Smart Retention**: 65 days of daily data + month-end snapshots for historical analysis
- **Device Classification**: Automatic spare device detection and server/workstation classification
- **Site Unification**: Maps Ninja Sites and ThreatLocker Tenants to canonical site names
- **Dashboard Analytics**: Compare today's inventory vs last month-end across multiple dimensions
- **Docker Deployment**: Containerized collectors and dashboard for easy deployment

## Business Rules

### Spare Device Detection
A device is classified as "spare" if any of these conditions are met:
- Display Name contains "spare" (case-insensitive)
- Location contains "spare" (case-insensitive)  
- Node Class equals "VMWARE_VM_GUEST"

### Data Retention
- **Daily snapshots**: Retained for 65 days
- **Month-end snapshots**: Retained for 2 years
- **Older data**: Automatically purged based on retention policy

## Architecture

The ES Inventory Hub collectors reuse existing API integration code from working dashboards:

- **NinjaRMM Collector**: Reuses API logic from `/opt/dashboard-project/es-dashboards/dashboards/ninja-seat-count-monthly`
- **ThreatLocker Collector**: Reuses API logic from `/opt/dashboard-project/es-dashboards/dashboards/threatlocker-stats`

This ensures proven authentication patterns, field coverage, and data processing logic. The collectors preserve all fields used by the dashboard modals and maintain the same data processing patterns.

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   NinjaRMM      │    │  ThreatLocker   │    │   PostgreSQL    │
│   Collector     │    │   Collector     │    │   Database      │
│ (reuses API)    │    │  (reuses API)   │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   Dashboard     │
                    │   (Flask)       │
                    └─────────────────┘
```

## Quick Start

### Prerequisites

- PostgreSQL 16+
- Python 3.9+
- Docker (optional)

### Data Processing Pipeline

The system includes an automated data processing pipeline that:

1. **Daily Rollups**: Aggregates device snapshots into daily counts by site
2. **Month-End Snapshots**: Creates month-end summaries for retention
3. **Retention Policy**: Automatically purges old data (>65 days) while preserving month-end snapshots

The pipeline runs automatically after each collector execution, or can be run independently:

```bash
# Run data processing independently
python scripts/process_data.py

# Or run the full pipeline
python storage/rollups.py
```

### Secret Management

This project shares API secrets with the dashboard project using a centralized approach:

**Shared Secrets Location:** `/opt/shared-secrets/api-secrets.env`

**Setup:**
```bash
# Create shared secrets directory (if not exists)
sudo mkdir -p /opt/shared-secrets

# Copy secrets from dashboard project (if not already done)
sudo cp /opt/dashboard-project/es-dashboards/.env /opt/shared-secrets/api-secrets.env

# Create dedicated group for secrets access
sudo groupadd -f es-secrets
sudo usermod -a -G es-secrets $USER

# Set secure permissions (root owner, es-secrets group, 640 permissions)
sudo chown root:es-secrets /opt/shared-secrets/api-secrets.env
sudo chmod 640 /opt/shared-secrets/api-secrets.env

# Create symlink in this project
ln -s /opt/shared-secrets/api-secrets.env /opt/es-inventory-hub/.env

# Activate group membership (or log out and back in)
newgrp es-secrets
```

**Security Notes:**
- Secrets are stored in `/opt/shared-secrets/api-secrets.env` with 640 permissions
- Owner: root, Group: es-secrets (dedicated group for authorized users)
- Both projects symlink to this shared file
- Only users in es-secrets group can read the file
- Monitor access with: `auditctl -w /opt/shared-secrets/api-secrets.env -p wa -k shared_secrets`

**Future Migration:**
- Phase 1: Shared symlinked file (current)
- Phase 2: HashiCorp Vault or AWS Secrets Manager
- Phase 3: Automated secret rotation and access controls

### 1. Database Setup

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

### 2. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env
```

Required environment variables:
- `NINJA_CLIENT_ID`: Your NinjaRMM client ID
- `THREATLOCKER_API_KEY`: Your ThreatLocker API key  
- `DB_PASSWORD`: PostgreSQL password

### 3. Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Initialize database
python -c "from storage.models import Base; from common.db import engine; Base.metadata.create_all(engine)"
```

### 4. Run Collectors

```bash
# Run Ninja collector (includes data processing)
python collectors/ninja/collector.py

# Run ThreatLocker collector (includes data processing)
python collectors/threatlocker/collector.py

# Run data processing independently
python scripts/process_data.py
```

### 5. Start Dashboard

```bash
# Start Flask dashboard
python dashboard_diffs/app.py
```

The dashboard will be available at `http://localhost:5000` and provides:

- **Today's Summary**: Current device counts by type and source
- **Comparison Charts**: Today vs last month-end visualization
- **Site Breakdown**: Per-site device counts and changes
- **Device Details**: Filterable device list with pagination
- **Health Monitoring**: System status and database connectivity

### Dashboard Features

- **Real-time Data**: Auto-refresh capability
- **Interactive Charts**: Chart.js powered visualizations
- **Responsive Design**: Works on desktop and mobile
- **Filtering**: Filter devices by type, source system, and site
- **Pagination**: Load devices in batches for performance

## Docker Deployment

### Option 1: Docker Compose (Development/Testing)

```bash
# Build and run all services
docker-compose up -d

# Run only specific services
docker-compose up -d postgres dashboard

# Run collectors manually
docker-compose run --rm ninja-collector
docker-compose run --rm threatlocker-collector
docker-compose run --rm data-processor

# View logs
docker-compose logs -f dashboard
docker-compose logs -f postgres
```

### Option 2: Production Deployment (Recommended)

```bash
# Build Docker images
./docker/build.sh

# Deploy with systemd services (requires sudo)
sudo ./docker/deploy.sh
```

### Production Services

The deployment creates the following systemd services:

- **es-inventory-dashboard.service**: Flask dashboard (port 5000)
- **es-inventory-ninja.timer**: Daily NinjaRMM collection at 2 AM
- **es-inventory-threatlocker.timer**: Daily ThreatLocker collection at 3 AM

### Service Management

```bash
# Check service status
systemctl status es-inventory-dashboard.service
systemctl list-timers es-inventory-*.timer

# View logs
journalctl -u es-inventory-dashboard -f
journalctl -u es-inventory-ninja -f

# Manual collector runs
systemctl start es-inventory-ninja.service
systemctl start es-inventory-threatlocker.service

# Restart services
systemctl restart es-inventory-dashboard.service
```

## Project Structure

```
es-inventory-hub/
├── collectors/           # Data collection modules
│   ├── ninja/           # NinjaRMM collector
│   └── threatlocker/    # ThreatLocker collector
├── storage/             # Database models and migrations
│   ├── models.py        # SQLAlchemy models
│   ├── rollups.py       # Data processing and rollups
│   └── migrations/      # Alembic migrations
├── scripts/             # Standalone scripts
│   └── process_data.py  # Data processing script
├── dashboard_diffs/     # Flask dashboard application
│   ├── app.py          # Main Flask application
│   └── templates/      # HTML templates
├── common/             # Shared utilities
│   ├── config.py       # Configuration management
│   ├── db.py          # Database connection
│   └── logging.py     # Structured logging
├── docker/            # Docker configuration
│   ├── Dockerfile.collectors    # Collectors container
│   ├── Dockerfile.dashboard     # Dashboard container
│   ├── systemd/                # Systemd service files
│   ├── build.sh               # Build script
│   └── deploy.sh              # Deployment script
├── tests/             # Test suite
├── docker-compose.yml # Docker Compose configuration
├── requirements.txt   # Python dependencies
└── README.md         # This file
```

## Database Schema

### Core Tables

- **sites**: Canonical site names unifying Ninja Sites + ThreatLocker Tenants
- **devices**: Core device information with classification flags
- **device_snapshots**: Daily snapshots with full data payloads
- **daily_counts**: Rollup counts for dashboard performance
- **month_end_counts**: Month-end snapshots for retention

### Key Relationships

- Devices belong to Sites
- Snapshots belong to Devices
- Daily/Month-end counts aggregate by Site

## API Endpoints

### Dashboard API

- `GET /` - Main dashboard page
- `GET /api/health` - Health check and system status
- `GET /api/dashboard/today` - Today's inventory summary
- `GET /api/dashboard/comparison` - Today vs last month comparison
- `GET /api/dashboard/sites` - Site-wise breakdown
- `GET /api/dashboard/devices` - Device details with filtering

### API Response Examples

**Today's Summary:**
```json
{
  "date": "2024-03-15T00:00:00+00:00",
  "totals": {
    "total_devices": 150,
    "servers": 25,
    "workstations": 125,
    "spare_devices": 8,
    "billable_devices": 142,
    "ninja_devices": 90,
    "threatlocker_devices": 60
  },
  "sites": [...],
  "site_count": 5
}
```

**Comparison Data:**
```json
{
  "today_date": "2024-03-15T00:00:00+00:00",
  "last_month_end_date": "2024-02-29T00:00:00+00:00",
  "today_totals": {...},
  "last_month_totals": {...},
  "changes": {
    "total_devices": {
      "current": 150,
      "previous": 145,
      "change": 5,
      "change_percent": 3.4
    }
  }
}
```

## Scheduling

### Automated Scheduling (Production)

The deployment automatically sets up systemd timers for daily collection:

- **NinjaRMM Collector**: Daily at 2:00 AM
- **ThreatLocker Collector**: Daily at 3:00 AM

### Manual Scheduling

```bash
# Check timer status
systemctl list-timers es-inventory-*.timer

# Run collectors manually
systemctl start es-inventory-ninja.service
systemctl start es-inventory-threatlocker.service

# View next run times
systemctl list-timers es-inventory-*.timer --all
```

### Cron Alternative (Legacy)

```bash
# Add to crontab for manual scheduling
0 2 * * * /usr/bin/python3 /opt/es-inventory-hub/collectors/ninja/collector.py
0 3 * * * /usr/bin/python3 /opt/es-inventory-hub/collectors/threatlocker/collector.py
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=.

# Run specific test module
pytest tests/test_ninja_collector.py
```

### Code Quality

```bash
# Format code
black .

# Lint code
flake8 .

# Type checking
mypy .
```

## Monitoring

### Health Checks

- Database connection status
- API endpoint availability
- Collector execution logs
- Data freshness indicators

### Logs

Structured JSON logging with correlation IDs for tracing requests across services.

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Check PostgreSQL service status
   - Verify connection string in `.env`
   - Ensure database user has proper permissions

2. **API Authentication Errors**
   - Verify API keys are correct
   - Check API endpoint URLs
   - Ensure network connectivity

3. **Data Not Updating**
   - Check collector logs for errors
   - Verify scheduling is working
   - Check database constraints and unique keys

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

Proprietary - Ener Systems

## Support

For support and questions, contact the development team at Ener Systems.

## Version History

### Current Version (v1.0.0)

- **Initial Release**: Complete ES Inventory Hub implementation
- **API Integration**: Refactored collectors to reuse existing dashboard API code
- **Database Schema**: PostgreSQL with SQLAlchemy ORM and Alembic migrations
- **Data Processing**: Daily rollups, month-end snapshots, and retention policies
- **Dashboard**: Flask-based web interface for inventory comparisons
- **Deployment**: Docker containers with systemd scheduling
- **Testing**: Comprehensive test suite with 60+ tests
- **Documentation**: Complete setup and deployment guides

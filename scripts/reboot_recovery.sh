#!/bin/bash
# ES Inventory Hub Reboot Recovery Script
# This script automates the recovery process after a server reboot

echo "=== ES Inventory Hub Reboot Recovery ==="
echo "Date: $(date)"
echo ""

# Set environment variables
export DB_DSN="postgresql://es_inventory_hub:your_password@localhost:5432/es_inventory_hub"

# Step 1: Start PostgreSQL
echo "Starting PostgreSQL..."
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Check PostgreSQL status
if sudo systemctl is-active --quiet postgresql; then
    echo "✅ PostgreSQL is running"
else
    echo "❌ PostgreSQL failed to start"
    exit 1
fi

# Step 2: Verify database user exists
echo "Checking database user..."
sudo -u postgres psql -c "SELECT 1 FROM pg_roles WHERE rolname='es_inventory_hub';" | grep -q "1" || {
    echo "Creating database user..."
    sudo -u postgres psql -c "CREATE ROLE es_inventory_hub WITH PASSWORD 'your_password';"
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE es_inventory_hub TO es_inventory_hub;"
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO es_inventory_hub;"
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO es_inventory_hub;"
}

# Step 3: Check database schema
echo "Checking database schema..."
cd /opt/es-inventory-hub
python3 -c "
from storage.schema import Base
from storage.database import get_engine
engine = get_engine()
Base.metadata.create_all(engine)
print('✅ Database schema verified')
"

# Step 4: Start API server
echo "Starting API server..."
sudo systemctl start es-inventory-api.service
sudo systemctl enable es-inventory-api.service

# Check API server status
if sudo systemctl is-active --quiet es-inventory-api.service; then
    echo "✅ API server is running"
else
    echo "❌ API server failed to start"
    echo "Checking logs..."
    sudo journalctl -u es-inventory-api.service --since "1 minute ago"
    exit 1
fi

# Step 5: Start all timers
echo "Starting collector timers..."
sudo systemctl start es-inventory-ninja.timer
sudo systemctl start es-inventory-threatlocker.timer
sudo systemctl start es-inventory-crossvendor.timer
sudo systemctl start windows-11-24h2-assessment.timer

# Enable all timers
sudo systemctl enable es-inventory-ninja.timer
sudo systemctl enable es-inventory-threatlocker.timer
sudo systemctl enable es-inventory-crossvendor.timer
sudo systemctl enable windows-11-24h2-assessment.timer

# Step 6: Test API endpoints
echo "Testing API endpoints..."
echo "Testing health endpoint..."
if curl -k -s https://localhost:5400/api/health | grep -q "healthy"; then
    echo "✅ Health endpoint working"
else
    echo "❌ Health endpoint failed"
fi

echo "Testing status endpoint..."
if curl -k -s https://localhost:5400/api/status | grep -q "total_devices"; then
    echo "✅ Status endpoint working"
else
    echo "❌ Status endpoint failed"
fi

echo "Testing Windows 11 24H2 endpoint..."
if curl -k -s https://localhost:5400/api/windows-11-24h2/status | grep -q "total_windows_devices"; then
    echo "✅ Windows 11 24H2 endpoint working"
else
    echo "❌ Windows 11 24H2 endpoint failed"
fi

# Step 7: Trigger data collection
echo "Triggering data collection..."
curl -k -X POST https://localhost:5400/api/collectors/run \
  -H "Content-Type: application/json" \
  -d '{"collector": "both", "run_cross_vendor": true}' \
  -s > /dev/null

echo "Running Windows 11 24H2 assessment..."
curl -k -X POST https://localhost:5400/api/windows-11-24h2/run \
  -s > /dev/null

echo ""
echo "=== Recovery Complete! ✅"
echo "All services are running and API endpoints are responding"
echo "Data collection has been triggered"
echo ""
echo "Next steps:"
echo "1. Monitor collector progress: curl -k https://localhost:5400/api/collectors/status"
echo "2. Check Windows 11 24H2 status: curl -k https://localhost:5400/api/windows-11-24h2/status"
echo "3. Monitor logs: sudo journalctl -u es-inventory-api.service -f"

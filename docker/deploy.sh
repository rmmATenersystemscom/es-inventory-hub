#!/bin/bash
# Deployment script for ES Inventory Hub

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    print_error "This script must be run as root (use sudo)"
    exit 1
fi

# Configuration
PROJECT_DIR="/opt/es-inventory-hub"
SERVICE_USER="es-inventory"
SERVICE_GROUP="es-inventory"
SYSTEMD_DIR="/etc/systemd/system"

print_status "Deploying ES Inventory Hub..."

# Create service user and group
if ! id "$SERVICE_USER" &>/dev/null; then
    print_status "Creating service user: $SERVICE_USER"
    useradd --system --create-home --shell /bin/bash "$SERVICE_USER"
else
    print_status "Service user $SERVICE_USER already exists"
fi

# Create service group if it doesn't exist
if ! getent group "$SERVICE_GROUP" > /dev/null 2>&1; then
    print_status "Creating service group: $SERVICE_GROUP"
    groupadd "$SERVICE_GROUP"
fi

# Add user to group
usermod -a -G "$SERVICE_GROUP" "$SERVICE_USER"

# Set up project directory permissions
if [ -d "$PROJECT_DIR" ]; then
    print_status "Setting up project directory permissions..."
    chown -R "$SERVICE_USER:$SERVICE_GROUP" "$PROJECT_DIR"
    chmod -R 755 "$PROJECT_DIR"
else
    print_error "Project directory $PROJECT_DIR does not exist"
    exit 1
fi

# Copy systemd service files
print_status "Installing systemd service files..."
cp docker/systemd/*.service "$SYSTEMD_DIR/"
cp docker/systemd/*.timer "$SYSTEMD_DIR/"

# Set proper permissions on service files
chmod 644 "$SYSTEMD_DIR"/es-inventory-*.service
chmod 644 "$SYSTEMD_DIR"/es-inventory-*.timer

# Reload systemd
print_status "Reloading systemd..."
systemctl daemon-reload

# Enable and start services
print_status "Enabling and starting services..."

# Enable dashboard service
systemctl enable es-inventory-dashboard.service
systemctl start es-inventory-dashboard.service

# Enable timers
systemctl enable es-inventory-ninja.timer
systemctl enable es-inventory-threatlocker.timer

# Start timers
systemctl start es-inventory-ninja.timer
systemctl start es-inventory-threatlocker.timer

# Check service status
print_status "Checking service status..."
systemctl status es-inventory-dashboard.service --no-pager -l

print_status "Checking timer status..."
systemctl list-timers es-inventory-*.timer

print_status "Deployment completed successfully!"
print_status ""
print_status "Services installed:"
print_status "  - es-inventory-dashboard.service (running on port 5000)"
print_status "  - es-inventory-ninja.timer (runs daily at 2 AM)"
print_status "  - es-inventory-threatlocker.timer (runs daily at 3 AM)"
print_status ""
print_status "Useful commands:"
print_status "  - View dashboard logs: journalctl -u es-inventory-dashboard -f"
print_status "  - View collector logs: journalctl -u es-inventory-ninja -f"
print_status "  - Check timer status: systemctl list-timers es-inventory-*.timer"
print_status "  - Manual collector run: systemctl start es-inventory-ninja.service"

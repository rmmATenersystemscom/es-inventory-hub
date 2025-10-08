#!/bin/bash
# ES Inventory Hub Configuration Backup Script
# This script backs up critical configuration files for disaster recovery

echo "=== ES Inventory Hub Configuration Backup ==="
echo "Date: $(date)"
echo ""

# Create backup directory
BACKUP_DIR="/opt/es-inventory-hub/backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "Backing up to: $BACKUP_DIR"

# Backup systemd service files
echo "Backing up systemd service files..."
sudo cp /etc/systemd/system/es-inventory-*.service "$BACKUP_DIR/" 2>/dev/null || echo "No service files found"
sudo cp /etc/systemd/system/es-inventory-*.timer "$BACKUP_DIR/" 2>/dev/null || echo "No timer files found"

# Backup environment configuration
echo "Backing up environment configuration..."
cp /opt/es-inventory-hub/.env "$BACKUP_DIR/" 2>/dev/null || echo "No .env file found"

# Backup SSL certificates
echo "Backing up SSL certificates..."
cp -r /opt/es-inventory-hub/ssl "$BACKUP_DIR/" 2>/dev/null || echo "No SSL directory found"

# Backup database schema
echo "Backing up database schema..."
psql postgresql://es_inventory_hub:your_password@localhost:5432/es_inventory_hub -c "\dt" > "$BACKUP_DIR/database_tables.txt" 2>/dev/null || echo "Database backup failed"

# Backup current configuration state
echo "Backing up current configuration state..."
cat > "$BACKUP_DIR/current_config.txt" << EOF
=== ES Inventory Hub Configuration Backup ===
Date: $(date)
Backup Directory: $BACKUP_DIR

=== Service Status ===
EOF

# Add service status to backup
sudo systemctl status es-inventory-api.service >> "$BACKUP_DIR/current_config.txt" 2>/dev/null
sudo systemctl status es-inventory-ninja.timer >> "$BACKUP_DIR/current_config.txt" 2>/dev/null
sudo systemctl status es-inventory-threatlocker.timer >> "$BACKUP_DIR/current_config.txt" 2>/dev/null
sudo systemctl status es-inventory-crossvendor.timer >> "$BACKUP_DIR/current_config.txt" 2>/dev/null
sudo systemctl status windows-11-24h2-assessment.timer >> "$BACKUP_DIR/current_config.txt" 2>/dev/null

# Add database schema to backup
echo "" >> "$BACKUP_DIR/current_config.txt"
echo "=== Database Schema ===" >> "$BACKUP_DIR/current_config.txt"
psql postgresql://es_inventory_hub:your_password@localhost:5432/es_inventory_hub -c "\dt" >> "$BACKUP_DIR/current_config.txt" 2>/dev/null

# Add API health check to backup
echo "" >> "$BACKUP_DIR/current_config.txt"
echo "=== API Health Check ===" >> "$BACKUP_DIR/current_config.txt"
curl -k -s https://localhost:5400/api/health >> "$BACKUP_DIR/current_config.txt" 2>/dev/null || echo "API health check failed" >> "$BACKUP_DIR/current_config.txt"

# Create recovery script
echo "Creating recovery script..."
cat > "$BACKUP_DIR/restore_config.sh" << 'EOF'
#!/bin/bash
# ES Inventory Hub Configuration Restore Script
# This script restores configuration from backup

echo "=== ES Inventory Hub Configuration Restore ==="
echo "Date: $(date)"
echo ""

# Restore systemd service files
echo "Restoring systemd service files..."
sudo cp es-inventory-*.service /etc/systemd/system/ 2>/dev/null || echo "No service files to restore"
sudo cp es-inventory-*.timer /etc/systemd/system/ 2>/dev/null || echo "No timer files to restore"

# Reload systemd
sudo systemctl daemon-reload

# Restore environment configuration
echo "Restoring environment configuration..."
cp .env /opt/es-inventory-hub/ 2>/dev/null || echo "No .env file to restore"

# Restore SSL certificates
echo "Restoring SSL certificates..."
cp -r ssl /opt/es-inventory-hub/ 2>/dev/null || echo "No SSL certificates to restore"

# Start services
echo "Starting services..."
sudo systemctl start es-inventory-api.service
sudo systemctl start es-inventory-ninja.timer
sudo systemctl start es-inventory-threatlocker.timer
sudo systemctl start es-inventory-crossvendor.timer
sudo systemctl start windows-11-24h2-assessment.timer

# Enable services
sudo systemctl enable es-inventory-api.service
sudo systemctl enable es-inventory-ninja.timer
sudo systemctl enable es-inventory-threatlocker.timer
sudo systemctl enable es-inventory-crossvendor.timer
sudo systemctl enable windows-11-24h2-assessment.timer

echo "Configuration restore complete!"
EOF

chmod +x "$BACKUP_DIR/restore_config.sh"

# Create backup summary
echo "Creating backup summary..."
cat > "$BACKUP_DIR/backup_summary.txt" << EOF
=== ES Inventory Hub Backup Summary ===
Date: $(date)
Backup Directory: $BACKUP_DIR

Files Backed Up:
- Systemd service files
- Systemd timer files
- Environment configuration (.env)
- SSL certificates
- Database schema
- Current configuration state

Recovery Instructions:
1. Copy backup directory to target server
2. Run: cd $BACKUP_DIR && ./restore_config.sh
3. Verify services are running
4. Test API endpoints

Backup Complete!
EOF

echo ""
echo "=== Backup Complete! ✅"
echo "Backup directory: $BACKUP_DIR"
echo "Files backed up:"
ls -la "$BACKUP_DIR"
echo ""
echo "To restore: cd $BACKUP_DIR && ./restore_config.sh"

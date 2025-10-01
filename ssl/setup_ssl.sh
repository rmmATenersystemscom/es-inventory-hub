#!/bin/bash
# SSL Certificate Setup Script for ES Inventory Hub API Server

echo "🔐 SSL Certificate Setup for ES Inventory Hub API Server"
echo "========================================================"

# Check if GoDaddy credentials are provided
if [ ! -f "/opt/es-inventory-hub/ssl/godaddy.ini" ] || grep -q "YOUR_GODADDY_API_KEY_HERE" /opt/es-inventory-hub/ssl/godaddy.ini; then
    echo "❌ GoDaddy API credentials not configured!"
    echo ""
    echo "Please edit /opt/es-inventory-hub/ssl/godaddy.ini with your GoDaddy API credentials:"
    echo "  dns_godaddy_api_key = YOUR_ACTUAL_API_KEY"
    echo "  dns_godaddy_api_secret = YOUR_ACTUAL_API_SECRET"
    echo ""
    echo "You can get these from: https://developer.godaddy.com/"
    exit 1
fi

# Get domain from user
echo "What domain should the API server use? (e.g., api.enersystems.com)"
read -p "Domain: " DOMAIN

if [ -z "$DOMAIN" ]; then
    echo "❌ Domain is required!"
    exit 1
fi

echo ""
echo "🔍 Requesting SSL certificate for: $DOMAIN"
echo "This will use DNS validation with GoDaddy..."

# Request certificate using Let's Encrypt with GoDaddy DNS validation
cd /opt/es-inventory-hub
source .venv/bin/activate

certbot certonly \
    --dns-godaddy \
    --dns-godaddy-credentials /opt/es-inventory-hub/ssl/godaddy.ini \
    --dns-godaddy-propagation-seconds 60 \
    -d "$DOMAIN" \
    --non-interactive \
    --agree-tos \
    --email admin@enersystems.com

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ SSL certificate obtained successfully!"
    
    # Copy certificates to our SSL directory
    echo "📋 Copying certificates..."
    cp "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" /opt/es-inventory-hub/ssl/api.crt
    cp "/etc/letsencrypt/live/$DOMAIN/privkey.pem" /opt/es-inventory-hub/ssl/api.key
    
    # Set proper permissions
    chmod 600 /opt/es-inventory-hub/ssl/api.key
    chmod 644 /opt/es-inventory-hub/ssl/api.crt
    
    echo ""
    echo "🎉 SSL setup complete!"
    echo "API server will now run on: https://$DOMAIN:5400"
    echo ""
    echo "To restart the API server with HTTPS:"
    echo "  sudo systemctl restart es-inventory-api.service"
    echo ""
    echo "To test HTTPS:"
    echo "  curl -k https://$DOMAIN:5400/api/health"
    
else
    echo "❌ Failed to obtain SSL certificate!"
    echo "Please check your GoDaddy API credentials and domain configuration."
    exit 1
fi

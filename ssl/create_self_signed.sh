#!/bin/bash
# Create self-signed SSL certificate for testing

echo "🔐 Creating self-signed SSL certificate for testing"
echo "=================================================="

cd /opt/es-inventory-hub/ssl

# Create self-signed certificate
openssl req -x509 -newkey rsa:4096 -keyout api.key -out api.crt -days 365 -nodes \
    -subj "/C=US/ST=Louisiana/L=New Orleans/O=Ener Systems/OU=IT/CN=192.168.99.246" \
    -addext "subjectAltName=DNS:192.168.99.246,DNS:localhost,IP:192.168.99.246,IP:127.0.0.1"

# Set proper permissions
chmod 600 api.key
chmod 644 api.crt

echo ""
echo "✅ Self-signed certificate created!"
echo "📁 Certificate: /opt/es-inventory-hub/ssl/api.crt"
echo "🔑 Private Key: /opt/es-inventory-hub/ssl/api.key"
echo ""
echo "⚠️  WARNING: This is a self-signed certificate for testing only!"
echo "   Browsers will show security warnings."
echo "   For production, use Let's Encrypt with the setup_ssl.sh script."
echo ""
echo "🚀 API server will now start with HTTPS support."
echo "   Test with: curl -k https://192.168.99.246:5400/api/health"

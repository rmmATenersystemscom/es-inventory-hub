# Backend Deployment Notes

### Setup
```
sudo apt install python3-venv postgresql nginx
python3 -m venv /opt/qbr_env
source /opt/qbr_env/bin/activate
pip install flask sqlalchemy psycopg2-binary alembic
```

### Service
Systemd unit: `es-inventory-api.service`
Port: 5400 (HTTPS)

### Security
Restrict inbound traffic to dashboard IP.
Store API key in `/opt/shared-secrets/api-secrets.env`.

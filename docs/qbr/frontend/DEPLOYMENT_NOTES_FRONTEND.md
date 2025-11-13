# Frontend Deployment Notes

### Setup
```
sudo apt install python3-venv nginx
python3 -m venv /opt/dashboard_env
source /opt/dashboard_env/bin/activate
pip install flask requests weasyprint pandas xlsxwriter
```

### Service
Systemd unit: `es-qbr-dashboard.service`

### Security
- HTTPS enforced
- Outbound-only access to backend
- Shared secrets in `/opt/shared-secrets/api-secrets.env`

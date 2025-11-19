# QBR Dashboard - Authentication Implementation Guide

**Purpose**: Complete technical guide for implementing Microsoft 365 OAuth authentication on the QBR Dashboard backend

**Status**: Ready for implementation
**Estimated Time**: 2-3 hours
**Complexity**: Moderate

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [Dependencies](#dependencies)
4. [Configuration](#configuration)
5. [Implementation Steps](#implementation-steps)
6. [Testing](#testing)
7. [Security Considerations](#security-considerations)
8. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

### Authentication Flow

```
┌─────────────┐
│   User      │
│  Browser    │
└──────┬──────┘
       │
       │ 1. Visit dashboard → Redirect to /api/auth/microsoft/login
       ▼
┌──────────────────────────────────────────────────────┐
│  Backend API (db-api.enersystems.com:5400)           │
│                                                      │
│  2. Redirect to Microsoft login URL                  │
└──────┬───────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────┐
│  Microsoft 365 / Azure AD                            │
│                                                      │
│  3. User logs in with Microsoft credentials          │
│  4. User consents to permissions (first time only)   │
└──────┬───────────────────────────────────────────────┘
       │
       │ 5. Redirect back with authorization code
       ▼
┌──────────────────────────────────────────────────────┐
│  Backend: /api/auth/microsoft/callback               │
│                                                      │
│  6. Exchange code for access token                   │
│  7. Get user email from Microsoft Graph API          │
│  8. Validate email is in authorized users list       │
│  9. Create secure HTTP-only session cookie           │
│ 10. Redirect to frontend dashboard                   │
└──────┬───────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────┐
│  Frontend Dashboard (dashboards.enersystems.com/qbr) │
│                                                      │
│ 11. User sees dashboard, authenticated!              │
└──────────────────────────────────────────────────────┘

Subsequent API Requests:
┌─────────────┐
│   Browser   │ API Request + Session Cookie
└──────┬──────┘
       ▼
┌──────────────────────────────────────────────────────┐
│  Backend: @require_auth decorator                    │
│                                                      │
│  1. Check session cookie                             │
│  2. Validate session is not expired (8 hours)        │
│  3. Verify user email is still authorized            │
│  4. Allow request → Return data                      │
└──────────────────────────────────────────────────────┘
```

---

## Prerequisites

### Azure AD Setup (Complete First)
- ✅ App registration created in Azure AD
- ✅ Have: Tenant ID, Client ID, Client Secret
- ✅ Redirect URI configured: `https://db-api.enersystems.com:5400/api/auth/microsoft/callback`

See: `/opt/es-inventory-hub/docs/qbr/AZURE_AD_SETUP_GUIDE.md`

### Authorized Users
- rmmiller@enersystems.com
- jmmiller@enersystems.com

### System Requirements
- Python 3.10+
- Flask API server running
- HTTPS enabled (required for secure cookies)
- PostgreSQL (optional - for session storage)

---

## Dependencies

### Python Packages to Install

```bash
source /opt/es-inventory-hub/.venv/bin/activate

pip install msal==1.24.0
pip install flask-session==0.5.0
pip install cryptography==41.0.5
pip install redis  # Optional: for production session storage
```

**Package Purposes:**
- `msal`: Microsoft Authentication Library - handles OAuth 2.0 flow
- `flask-session`: Server-side session management
- `cryptography`: Secure session encryption
- `redis`: (Optional) Session storage for production (better than filesystem)

---

## Configuration

### Environment Variables

Add to `/opt/shared-secrets/api-secrets.env`:

```bash
# Microsoft 365 OAuth Configuration
AZURE_TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
AZURE_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
AZURE_CLIENT_SECRET=AbC123~xYz789-1234567890aBcDeFgHiJkLmNoPqRsTuVwXyZ

# Session Configuration
SESSION_SECRET_KEY=generate-a-random-secure-key-here
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax
SESSION_LIFETIME_HOURS=8

# QBR Authorized Users (comma-separated)
QBR_AUTHORIZED_USERS=rmmiller@enersystems.com,jmmiller@enersystems.com

# URLs
API_BASE_URL=https://db-api.enersystems.com:5400
FRONTEND_URL=https://dashboards.enersystems.com/qbr
```

### Generate Session Secret Key

```bash
# Generate a secure random key
python3 -c "import secrets; print(secrets.token_hex(32))"

# Copy output and use as SESSION_SECRET_KEY
```

### File Permissions

```bash
sudo chmod 600 /opt/shared-secrets/api-secrets.env
sudo chown rene:svc_es-hub /opt/shared-secrets/api-secrets.env
```

---

## Implementation Steps

### Step 1: Create Authentication Module

Create file: `/opt/es-inventory-hub/api/auth_microsoft.py`

```python
#!/usr/bin/env python3
"""
Microsoft 365 OAuth Authentication for QBR Dashboard

Implements OAuth 2.0 authorization code flow with MSAL library.
Provides secure session-based authentication using HTTP-only cookies.
"""

import os
import logging
from datetime import datetime, timedelta
from functools import wraps
from urllib.parse import urlencode

from flask import Blueprint, request, redirect, session, jsonify, url_for
from msal import ConfidentialClientApplication
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Blueprint
auth_bp = Blueprint('auth', __name__)

# Azure AD Configuration (from environment variables)
TENANT_ID = os.getenv('AZURE_TENANT_ID')
CLIENT_ID = os.getenv('AZURE_CLIENT_ID')
CLIENT_SECRET = os.getenv('AZURE_CLIENT_SECRET')
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
REDIRECT_URI = os.getenv('API_BASE_URL', 'https://db-api.enersystems.com:5400') + '/api/auth/microsoft/callback'
FRONTEND_URL = os.getenv('FRONTEND_URL', 'https://dashboards.enersystems.com/qbr')

# Scopes - what permissions we're requesting
SCOPES = ["User.Read"]  # Basic profile information

# Authorized users
AUTHORIZED_USERS = os.getenv('QBR_AUTHORIZED_USERS', '').split(',')

# Validate configuration
if not all([TENANT_ID, CLIENT_ID, CLIENT_SECRET]):
    raise ValueError("Missing Azure AD configuration. Check environment variables.")

if not AUTHORIZED_USERS or AUTHORIZED_USERS == ['']:
    raise ValueError("No authorized users configured. Check QBR_AUTHORIZED_USERS environment variable.")

logger.info(f"Auth configured for {len(AUTHORIZED_USERS)} authorized users")


def get_msal_app():
    """Create and return MSAL confidential client application"""
    return ConfidentialClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        client_credential=CLIENT_SECRET,
    )


@auth_bp.route('/api/auth/microsoft/login')
def microsoft_login():
    """
    Initiate Microsoft OAuth login flow.
    Redirects user to Microsoft login page.
    """
    logger.info("Login initiated")

    # Get MSAL app
    msal_app = get_msal_app()

    # Build authorization URL
    auth_url = msal_app.get_authorization_request_url(
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )

    logger.info(f"Redirecting to Microsoft login: {auth_url}")
    return redirect(auth_url)


@auth_bp.route('/api/auth/microsoft/callback')
def microsoft_callback():
    """
    Handle OAuth callback from Microsoft.
    Exchange authorization code for access token, validate user, create session.
    """
    logger.info("Callback received from Microsoft")

    # Get authorization code from query params
    code = request.args.get('code')
    if not code:
        error = request.args.get('error', 'unknown_error')
        error_description = request.args.get('error_description', 'No error description provided')
        logger.error(f"OAuth error: {error} - {error_description}")
        return jsonify({
            "error": "Authentication failed",
            "details": error_description
        }), 400

    try:
        # Exchange code for token
        msal_app = get_msal_app()
        result = msal_app.acquire_token_by_authorization_code(
            code,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )

        if "error" in result:
            logger.error(f"Token acquisition failed: {result.get('error_description')}")
            return jsonify({
                "error": "Failed to obtain access token",
                "details": result.get('error_description')
            }), 400

        # Get access token
        access_token = result.get('access_token')
        if not access_token:
            logger.error("No access token in response")
            return jsonify({"error": "No access token received"}), 400

        # Call Microsoft Graph API to get user profile
        graph_response = requests.get(
            'https://graph.microsoft.com/v1.0/me',
            headers={'Authorization': f'Bearer {access_token}'}
        )

        if graph_response.status_code != 200:
            logger.error(f"Graph API error: {graph_response.text}")
            return jsonify({"error": "Failed to get user profile"}), 400

        user_data = graph_response.json()
        user_email = user_data.get('userPrincipalName') or user_data.get('mail')
        user_name = user_data.get('displayName', 'Unknown User')

        logger.info(f"User authenticated: {user_email}")

        # Validate user is authorized
        if user_email not in AUTHORIZED_USERS:
            logger.warning(f"Unauthorized user attempted login: {user_email}")
            return jsonify({
                "error": "Access denied",
                "message": "Your account is not authorized to access this dashboard."
            }), 403

        # Create session
        session.clear()
        session['authenticated'] = True
        session['user_email'] = user_email
        session['user_name'] = user_name
        session['login_time'] = datetime.utcnow().isoformat()
        session.permanent = True  # Use configured session lifetime

        logger.info(f"Session created for {user_email}")

        # Redirect to frontend dashboard
        return redirect(FRONTEND_URL)

    except Exception as e:
        logger.error(f"Authentication error: {str(e)}", exc_info=True)
        return jsonify({
            "error": "Authentication failed",
            "details": str(e)
        }), 500


@auth_bp.route('/api/auth/logout', methods=['POST', 'GET'])
def logout():
    """
    Log out the current user.
    Clears session and redirects to Microsoft logout.
    """
    user_email = session.get('user_email', 'unknown')
    logger.info(f"Logout: {user_email}")

    session.clear()

    # Microsoft logout URL (clears Microsoft session too)
    microsoft_logout_url = (
        f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/logout?"
        f"post_logout_redirect_uri={FRONTEND_URL}"
    )

    return redirect(microsoft_logout_url)


@auth_bp.route('/api/auth/status')
def auth_status():
    """
    Check current authentication status.
    Returns user info if authenticated, error if not.
    """
    if session.get('authenticated'):
        return jsonify({
            "authenticated": True,
            "user_email": session.get('user_email'),
            "user_name": session.get('user_name'),
            "login_time": session.get('login_time')
        })
    else:
        return jsonify({"authenticated": False}), 401


def require_auth(f):
    """
    Decorator to protect API endpoints.
    Requires valid authenticated session.

    Usage:
        @app.route('/api/qbr/smartnumbers')
        @require_auth
        def get_smartnumbers():
            current_user = session.get('user_email')
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('authenticated'):
            logger.warning(f"Unauthorized access attempt to {request.path}")
            return jsonify({
                "error": "Authentication required",
                "message": "Please log in to access this resource"
            }), 401

        # Verify user is still authorized (in case list changed)
        user_email = session.get('user_email')
        if user_email not in AUTHORIZED_USERS:
            logger.warning(f"User no longer authorized: {user_email}")
            session.clear()
            return jsonify({
                "error": "Access denied",
                "message": "Your authorization has been revoked"
            }), 403

        return f(*args, **kwargs)

    return decorated_function


# Export decorator for use in other modules
__all__ = ['auth_bp', 'require_auth']
```

### Step 2: Update API Server

Edit `/opt/es-inventory-hub/api/api_server.py`:

```python
# Add these imports at the top
from datetime import timedelta
from flask_session import Session

# Add after existing CORS configuration (around line 84)

# Configure session management
app.config['SECRET_KEY'] = os.getenv('SESSION_SECRET_KEY')
app.config['SESSION_TYPE'] = 'filesystem'  # Or 'redis' for production
app.config['SESSION_FILE_DIR'] = '/tmp/flask_sessions'  # Or Redis URL
app.config['SESSION_COOKIE_NAME'] = 'qbr_session'
app.config['SESSION_COOKIE_SECURE'] = True  # HTTPS only
app.config['SESSION_COOKIE_HTTPONLY'] = True  # No JavaScript access
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(
    hours=int(os.getenv('SESSION_LIFETIME_HOURS', 8))
)

# Initialize session
Session(app)

# Register authentication blueprint (add after QBR blueprint registration)
from api.auth_microsoft import auth_bp, require_auth
app.register_blueprint(auth_bp)

# Update all QBR endpoint decorators (example):
@app.route('/api/qbr/smartnumbers')
@require_auth  # <-- Add this decorator
def get_smartnumbers():
    # Existing code...
    current_user = session.get('user_email')  # Available if needed
    ...
```

### Step 3: Protect All QBR Endpoints

Add `@require_auth` decorator to these endpoints in `api_server.py` and `api/qbr_api.py`:

```python
@app.route('/api/qbr/metrics/monthly')
@require_auth
def qbr_metrics_monthly():
    ...

@app.route('/api/qbr/metrics/quarterly')
@require_auth
def qbr_metrics_quarterly():
    ...

@app.route('/api/qbr/smartnumbers')
@require_auth
def qbr_smartnumbers():
    ...

@app.route('/api/qbr/thresholds')
@require_auth
def qbr_thresholds():
    ...

@app.route('/api/qbr/metrics/manual', methods=['POST'])
@require_auth
def qbr_manual_metrics():
    ...

@app.route('/api/qbr/thresholds', methods=['POST'])
@require_auth
def qbr_update_thresholds():
    ...
```

### Step 4: Create Session Storage Directory

```bash
sudo mkdir -p /tmp/flask_sessions
sudo chown svc_es-hub:svc_es-hub /tmp/flask_sessions
sudo chmod 700 /tmp/flask_sessions
```

**Production Note:** For production, use Redis instead of filesystem:
```bash
# Install Redis
sudo apt install redis-server

# Update app.config in api_server.py:
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_REDIS'] = redis.from_url('redis://localhost:6379')
```

---

## Testing

### Step 1: Update Environment Variables

```bash
# Edit the secrets file
sudo nano /opt/shared-secrets/api-secrets.env

# Add your Azure AD credentials (from Azure setup)
# Save and exit

# Reload environment
source /opt/shared-secrets/api-secrets.env
```

### Step 2: Restart API Server

```bash
sudo systemctl restart es-inventory-api.service

# Check status
sudo systemctl status es-inventory-api.service

# Check logs
sudo journalctl -u es-inventory-api.service -n 50
```

### Step 3: Test Login Flow

**Test 1: Initiate Login**
```bash
curl -v https://db-api.enersystems.com:5400/api/auth/microsoft/login

# Should return: 302 redirect to login.microsoftonline.com
```

**Test 2: Manual Browser Test**
1. Open browser
2. Go to: `https://db-api.enersystems.com:5400/api/auth/microsoft/login`
3. Should redirect to Microsoft login
4. Login with `rmmiller@enersystems.com` or `jmmiller@enersystems.com`
5. Consent to permissions (first time only)
6. Should redirect to `https://dashboards.enersystems.com/qbr`
7. Cookie should be set (`qbr_session`)

**Test 3: Check Auth Status**
```bash
# After login, with session cookie
curl -b cookies.txt https://db-api.enersystems.com:5400/api/auth/status

# Should return:
# {"authenticated":true,"user_email":"rmmiller@enersystems.com",...}
```

**Test 4: Access Protected Endpoint**
```bash
# Without auth (should fail)
curl https://db-api.enersystems.com:5400/api/qbr/smartnumbers?period=2025-Q4

# Response: {"error":"Authentication required"} 401

# With session cookie (should work)
curl -b cookies.txt https://db-api.enersystems.com:5400/api/qbr/smartnumbers?period=2025-Q4

# Response: {"success":true,"data":{...}}
```

**Test 5: Unauthorized User**
Try logging in with a Microsoft account that's NOT in the authorized users list.
- Should authenticate with Microsoft successfully
- Should be rejected at callback with 403 error
- Should see: "Access denied - Your account is not authorized"

**Test 6: Logout**
```bash
curl -X POST -b cookies.txt https://db-api.enersystems.com:5400/api/auth/logout

# Should clear session and redirect to Microsoft logout
```

---

## Security Considerations

### Session Security
- ✅ HTTP-only cookies (JavaScript can't access)
- ✅ Secure flag (HTTPS only)
- ✅ SameSite=Lax (CSRF protection)
- ✅ 8-hour expiration (configurable)
- ✅ Server-side session storage

### Authorization
- ✅ Hardcoded authorized users list
- ✅ Email validation on every request
- ✅ Session cleared if user becomes unauthorized

### Secrets Management
- ✅ Client secret stored in `/opt/shared-secrets/` (not in code)
- ✅ File permissions: 600 (owner only)
- ✅ Never committed to git
- ✅ Rotate secrets every 12-24 months

### Transport Security
- ✅ HTTPS required (secure cookies)
- ✅ TLS 1.2+ only
- ✅ Valid SSL certificate

### Logging
- ✅ Log all auth attempts (success and failure)
- ✅ Log unauthorized access attempts
- ✅ No sensitive data in logs (no tokens, passwords)

---

## Troubleshooting

### Error: "Redirect URI mismatch"
**Cause:** The redirect URI in your code doesn't match Azure AD configuration

**Fix:**
1. Check `/opt/shared-secrets/api-secrets.env` - verify `API_BASE_URL`
2. Check Azure AD app registration - verify redirect URI is exact:
   `https://db-api.enersystems.com:5400/api/auth/microsoft/callback`
3. No trailing slash, HTTPS, correct port

### Error: "Invalid client secret"
**Cause:** Wrong secret, or secret expired

**Fix:**
1. Go to Azure Portal → App registration → Certificates & secrets
2. Create new client secret
3. Update `/opt/shared-secrets/api-secrets.env` with new value
4. Restart API server

### Error: "Access denied"
**Cause:** User email not in authorized users list

**Fix:**
1. Check `/opt/shared-secrets/api-secrets.env`
2. Verify `QBR_AUTHORIZED_USERS` includes the user's email
3. Emails are case-sensitive and comma-separated
4. Restart API server after changes

### Error: "MSAL module not found"
**Cause:** Dependencies not installed

**Fix:**
```bash
source /opt/es-inventory-hub/.venv/bin/activate
pip install msal flask-session cryptography
```

### Sessions Not Persisting
**Cause:** Session storage directory doesn't exist or wrong permissions

**Fix:**
```bash
sudo mkdir -p /tmp/flask_sessions
sudo chown svc_es-hub:svc_es-hub /tmp/flask_sessions
sudo chmod 700 /tmp/flask_sessions
sudo systemctl restart es-inventory-api.service
```

### CORS Errors
**Cause:** Frontend domain not in CORS allowed origins

**Fix:** In `api_server.py`, verify CORS configuration includes:
```python
CORS(app,
     origins=['https://dashboards.enersystems.com', ...],
     supports_credentials=True  # Required for cookies
)
```

---

## Configuration Reference

### Environment Variables

| Variable | Required | Example | Description |
|----------|----------|---------|-------------|
| AZURE_TENANT_ID | Yes | xxxxxxxx-... | Azure AD tenant ID |
| AZURE_CLIENT_ID | Yes | xxxxxxxx-... | App registration client ID |
| AZURE_CLIENT_SECRET | Yes | AbC123~... | App client secret |
| SESSION_SECRET_KEY | Yes | random-hex-64-chars | Session encryption key |
| SESSION_LIFETIME_HOURS | No | 8 | Session expiration (hours) |
| QBR_AUTHORIZED_USERS | Yes | user1@...,user2@... | Comma-separated emails |
| API_BASE_URL | Yes | https://db-api... | Backend API base URL |
| FRONTEND_URL | Yes | https://dashboards... | Frontend dashboard URL |

### Session Configuration

```python
# Default values (can override in environment)
SESSION_TYPE = 'filesystem'  # or 'redis'
SESSION_COOKIE_NAME = 'qbr_session'
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_LIFETIME = 8 hours
```

---

## Deployment Checklist

Before deploying to production:

- [ ] Azure AD app registration created
- [ ] Client ID, Tenant ID, Secret obtained
- [ ] Environment variables configured in `/opt/shared-secrets/api-secrets.env`
- [ ] File permissions set correctly (600)
- [ ] Session storage directory created
- [ ] Dependencies installed (`msal`, `flask-session`)
- [ ] API server code updated with authentication
- [ ] All QBR endpoints protected with `@require_auth`
- [ ] CORS configured to support credentials
- [ ] SSL/TLS certificate valid
- [ ] Tested login flow with both authorized users
- [ ] Tested unauthorized user rejection
- [ ] Tested logout flow
- [ ] Tested session expiration
- [ ] Logs reviewed for errors
- [ ] Backend documentation updated

---

## Next Steps

After backend authentication is working:

1. **Frontend Integration**
   - Add "Login with Microsoft" button
   - Handle authentication state
   - Include credentials in API requests
   - Handle session expiration

2. **Monitoring**
   - Set up alerts for failed auth attempts
   - Monitor session storage usage
   - Track login/logout events

3. **Production Hardening**
   - Switch to Redis for session storage
   - Enable rate limiting on auth endpoints
   - Add brute force protection
   - Implement session audit logging

---

**Version**: v1.0
**Created**: November 16, 2025
**Authorized Users**: rmmiller@enersystems.com, jmmiller@enersystems.com
**Token Expiration**: 8 hours
**Security Level**: HTTP-only cookies, Single tenant OAuth


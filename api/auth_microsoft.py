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

# Load configuration from environment variables
def load_config():
    """Load Azure AD configuration from environment"""
    # Try to load from /opt/shared-secrets/api-secrets.env
    env_file = '/opt/shared-secrets/api-secrets.env'
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    if key not in os.environ:
                        os.environ[key] = value

load_config()

# Azure AD Configuration (using QBR_ prefix from secrets file)
TENANT_ID = os.getenv('QBR_AZURE_TENANT_ID') or os.getenv('AZURE_TENANT_ID')
CLIENT_ID = os.getenv('QBR_AZURE_CLIENT_ID') or os.getenv('AZURE_CLIENT_ID')
CLIENT_SECRET = os.getenv('QBR_AZURE_CLIENT_SECRET') or os.getenv('AZURE_CLIENT_SECRET')
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
REDIRECT_URI = os.getenv('API_BASE_URL', 'https://db-api.enersystems.com:5400') + '/api/auth/microsoft/callback'
FRONTEND_URL = os.getenv('FRONTEND_URL', 'https://dashboards.enersystems.com/qbr')

# Scopes - what permissions we're requesting
SCOPES = ["User.Read"]  # Basic profile information

# Authorized users
AUTHORIZED_USERS_STR = os.getenv('QBR_AUTHORIZED_USERS', '')
AUTHORIZED_USERS = [email.strip() for email in AUTHORIZED_USERS_STR.split(',') if email.strip()]

# Validate configuration
if not all([TENANT_ID, CLIENT_ID, CLIENT_SECRET]):
    raise ValueError("Missing Azure AD configuration. Check environment variables AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET.")

if not AUTHORIZED_USERS:
    raise ValueError("No authorized users configured. Check QBR_AUTHORIZED_USERS environment variable.")

logger.info(f"Auth configured for {len(AUTHORIZED_USERS)} authorized users")
logger.info(f"Redirect URI: {REDIRECT_URI}")
logger.info(f"Frontend URL: {FRONTEND_URL}")


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

    logger.info(f"Redirecting to Microsoft login")
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
            headers={'Authorization': f'Bearer {access_token}'},
            timeout=10
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
                "message": f"Your account ({user_email}) is not authorized to access this dashboard. Please contact your administrator."
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

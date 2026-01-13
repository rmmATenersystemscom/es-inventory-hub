"""
NinjaRMM Credentials Manager - handles all Ninja authentication

This module manages ALL NinjaRMM credentials for this system (DbAI):
- base_url, client_id, client_secret: Static credentials specific to this system
- refresh_token: Rotates on every use, must be persisted

IMPORTANT: Each system (DbAI vs Dashboard AI) has its own Ninja client credentials.
The shared secrets file (/opt/shared-secrets/api-secrets.env) contains Dashboard AI's
credentials, NOT DbAI's. Therefore ALL Ninja credentials must come from this JSON file.

NinjaRMM uses refresh token rotation - each time you exchange a refresh token
for an access token, NinjaRMM may return a NEW refresh token. The old token
can become invalid.
"""

import json
import os
import fcntl
import logging
import requests
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Credentials file location - stores ALL Ninja credentials for this system
CREDENTIALS_FILE_PATH = '/opt/es-inventory-hub/data/ninja_refresh_token.json'


def _read_credentials_file() -> Optional[Dict[str, Any]]:
    """Read credentials from file with locking."""
    try:
        if os.path.exists(CREDENTIALS_FILE_PATH):
            with open(CREDENTIALS_FILE_PATH, 'r') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                try:
                    return json.load(f)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except Exception as e:
        logger.warning(f"Could not read credentials file: {e}")
    return None


def _write_credentials_file(data: Dict[str, Any]) -> bool:
    """Write credentials to file with locking."""
    try:
        os.makedirs(os.path.dirname(CREDENTIALS_FILE_PATH), exist_ok=True)
        with open(CREDENTIALS_FILE_PATH, 'w') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                json.dump(data, f, indent=2)
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        os.chmod(CREDENTIALS_FILE_PATH, 0o600)  # Secure permissions
        logger.info(f"Saved credentials to {CREDENTIALS_FILE_PATH}")
        return True
    except Exception as e:
        logger.error(f"Could not write credentials file: {e}")
        return False


def get_credentials() -> Optional[Dict[str, str]]:
    """
    Get all Ninja credentials from file.

    Returns dict with: base_url, client_id, client_secret, refresh_token
    Or None if file is missing or invalid.
    """
    creds = _read_credentials_file()
    if not creds:
        logger.error(f"No credentials file found at {CREDENTIALS_FILE_PATH}")
        return None

    required = ['base_url', 'client_id', 'client_secret', 'refresh_token']
    missing = [k for k in required if not creds.get(k)]
    if missing:
        logger.error(f"Missing credentials in {CREDENTIALS_FILE_PATH}: {missing}")
        return None

    return {
        'base_url': creds['base_url'].rstrip('/'),
        'client_id': creds['client_id'],
        'client_secret': creds['client_secret'],
        'refresh_token': creds['refresh_token']
    }


def get_refresh_token() -> Optional[str]:
    """
    Get current refresh token from file.

    NinjaRMM rotates refresh tokens on every use - the JSON file is the ONLY
    valid source for the current token. Environment variables cannot be used
    because they would contain stale/invalid tokens after any API call.

    Returns:
        The current refresh token, or None if not available
    """
    creds = _read_credentials_file()
    if creds and creds.get('refresh_token'):
        logger.debug("Using refresh token from file")
        return creds['refresh_token']
    logger.error(f"No refresh token found in {CREDENTIALS_FILE_PATH}")
    return None


def save_refresh_token(new_token: str, source: str = 'api_response') -> bool:
    """
    Save new refresh token to file, preserving other credentials.

    Args:
        new_token: The new refresh token to save
        source: Description of where the token came from

    Returns:
        True if saved successfully, False otherwise
    """
    if not new_token:
        return False

    # Read existing credentials to preserve them
    existing = _read_credentials_file() or {}

    # Update only the refresh token and metadata
    existing['refresh_token'] = new_token
    existing['updated_at'] = datetime.utcnow().isoformat() + 'Z'
    existing['source'] = source

    return _write_credentials_file(existing)


def get_access_token() -> Optional[str]:
    """
    Get access token with automatic token rotation handling.

    This function:
    1. Reads ALL credentials (base_url, client_id, client_secret, refresh_token) from JSON file
    2. Exchanges refresh token for an access token
    3. Saves any new refresh token returned by the API

    NinjaRMM rotates tokens on every use - the JSON file is the ONLY valid source.
    Environment variables are NOT supported because they become stale immediately.

    Returns:
        Access token string, or None if failed
    """
    creds = get_credentials()
    if not creds:
        logger.error(f"Cannot get access token - credentials missing from {CREDENTIALS_FILE_PATH}")
        return None

    base_url = creds['base_url']
    client_id = creds['client_id']
    client_secret = creds['client_secret']
    refresh_token = creds['refresh_token']

    token_url = f"{base_url}/oauth/token"
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
        'client_id': client_id,
        'client_secret': client_secret,
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}

    try:
        logger.debug(f"Requesting access token from {token_url}")
        resp = requests.post(token_url, data=data, headers=headers, timeout=30)
        resp.raise_for_status()

        token_response = resp.json()
        access_token = token_response.get('access_token')
        new_refresh_token = token_response.get('refresh_token')

        if not access_token:
            logger.error("No access_token in response")
            return None

        # Handle token rotation - save new refresh token if provided and different
        if new_refresh_token and new_refresh_token != refresh_token:
            logger.info("NinjaRMM rotated refresh token - saving new token")
            save_refresh_token(new_refresh_token, source='token_rotation')

        logger.debug("Successfully obtained access token")
        return access_token

    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 400:
            error_detail = e.response.text
            logger.error(f"NinjaRMM token error (400): {error_detail}")
            if 'invalid_token' in error_detail or 'invalid_grant' in error_detail:
                logger.error("Refresh token may be expired or invalid. "
                           "Update refresh_token in " + CREDENTIALS_FILE_PATH)
        else:
            logger.error(f"HTTP error getting access token: {e}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error getting NinjaRMM access token: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error getting access token: {e}")
        return None


def get_credentials_status() -> Dict[str, Any]:
    """
    Get status information about stored credentials.

    Returns:
        Dict with credentials status information
    """
    creds = _read_credentials_file()
    if creds:
        has_all = all(creds.get(k) for k in ['base_url', 'client_id', 'client_secret', 'refresh_token'])
        return {
            'has_credentials': has_all,
            'has_base_url': bool(creds.get('base_url')),
            'has_client_id': bool(creds.get('client_id')),
            'has_client_secret': bool(creds.get('client_secret')),
            'has_refresh_token': bool(creds.get('refresh_token')),
            'updated_at': creds.get('updated_at'),
            'source': creds.get('source'),
            'file_path': CREDENTIALS_FILE_PATH
        }
    return {
        'has_credentials': False,
        'file_path': CREDENTIALS_FILE_PATH,
        'note': 'Credentials file missing. Create it with base_url, client_id, client_secret, refresh_token.'
    }

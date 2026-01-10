"""
NinjaRMM Token Manager - handles OAuth token rotation

NinjaRMM uses refresh token rotation - each time you exchange a refresh token
for an access token, NinjaRMM may return a NEW refresh token. The old token
can become invalid. This module handles saving the rotated tokens to prevent
authentication failures.
"""

import json
import os
import fcntl
import logging
import requests
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Token file location - outside of git-tracked directories
TOKEN_FILE_PATH = '/opt/es-inventory-hub/data/ninja_refresh_token.json'


def _read_token_file() -> Optional[Dict[str, Any]]:
    """Read token from file with locking."""
    try:
        if os.path.exists(TOKEN_FILE_PATH):
            with open(TOKEN_FILE_PATH, 'r') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                try:
                    return json.load(f)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except Exception as e:
        logger.warning(f"Could not read token file: {e}")
    return None


def _write_token_file(data: Dict[str, Any]) -> bool:
    """Write token to file with locking."""
    try:
        os.makedirs(os.path.dirname(TOKEN_FILE_PATH), exist_ok=True)
        with open(TOKEN_FILE_PATH, 'w') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                json.dump(data, f, indent=2)
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        os.chmod(TOKEN_FILE_PATH, 0o600)  # Secure permissions
        logger.info(f"Saved new refresh token to {TOKEN_FILE_PATH}")
        return True
    except Exception as e:
        logger.error(f"Could not write token file: {e}")
        return False


def get_refresh_token(env_fallback: Optional[str] = None) -> Optional[str]:
    """
    Get current refresh token from file or environment.

    Args:
        env_fallback: Fallback token from environment variable

    Returns:
        The current refresh token, or None if not available
    """
    token_data = _read_token_file()
    if token_data and token_data.get('refresh_token'):
        logger.debug("Using refresh token from file")
        return token_data['refresh_token']
    if env_fallback:
        logger.debug("Using refresh token from environment (fallback)")
    return env_fallback


def save_refresh_token(new_token: str, source: str = 'api_response') -> bool:
    """
    Save new refresh token to file.

    Args:
        new_token: The new refresh token to save
        source: Description of where the token came from

    Returns:
        True if saved successfully, False otherwise
    """
    if not new_token:
        return False
    data = {
        'refresh_token': new_token,
        'updated_at': datetime.utcnow().isoformat() + 'Z',
        'source': source
    }
    return _write_token_file(data)


def get_access_token(base_url: str, client_id: str, client_secret: str,
                     env_refresh_token: Optional[str] = None) -> Optional[str]:
    """
    Get access token with automatic token rotation handling.

    This function:
    1. Reads the current refresh token from file (or falls back to env variable)
    2. Exchanges it for an access token
    3. Saves any new refresh token returned by the API

    Args:
        base_url: NinjaRMM API base URL (e.g., https://app.ninjarmm.com)
        client_id: OAuth client ID
        client_secret: OAuth client secret
        env_refresh_token: Fallback refresh token from environment

    Returns:
        Access token string, or None if failed
    """
    refresh_token = get_refresh_token(env_refresh_token)

    if not refresh_token:
        logger.error("No refresh token available (neither in file nor environment)")
        return None

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

        # Handle token rotation - save new refresh token if provided
        if new_refresh_token:
            token_data = _read_token_file()
            current_token = token_data.get('refresh_token') if token_data else None

            # Save if token was rotated OR if we don't have a file yet
            if new_refresh_token != current_token:
                if current_token and new_refresh_token != refresh_token:
                    logger.info("NinjaRMM rotated refresh token - saving new token")
                    save_refresh_token(new_refresh_token, source='token_rotation')
                elif token_data is None:
                    logger.info("No token file exists - creating initial token file")
                    save_refresh_token(new_refresh_token, source='initial_save')

        logger.debug("Successfully obtained access token")
        return access_token

    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 400:
            error_detail = e.response.text
            logger.error(f"NinjaRMM token error (400): {error_detail}")
            if 'invalid_token' in error_detail or 'invalid_grant' in error_detail:
                logger.error("Refresh token may be expired or invalid. "
                           "You may need to generate a new refresh token manually.")
        else:
            logger.error(f"HTTP error getting access token: {e}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error getting NinjaRMM access token: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error getting access token: {e}")
        return None


def get_token_status() -> Dict[str, Any]:
    """
    Get status information about the stored token.

    Returns:
        Dict with token status information
    """
    token_data = _read_token_file()
    if token_data:
        return {
            'has_token': True,
            'updated_at': token_data.get('updated_at'),
            'source': token_data.get('source'),
            'file_path': TOKEN_FILE_PATH
        }
    return {
        'has_token': False,
        'file_path': TOKEN_FILE_PATH,
        'note': 'Will use NINJA_REFRESH_TOKEN environment variable as fallback'
    }

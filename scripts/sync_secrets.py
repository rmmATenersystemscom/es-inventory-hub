#!/usr/bin/env python3
"""
Sync API secrets from shared secrets file to local .env file.

This script:
1. Reads the source of truth: /opt/shared-secrets/api-secrets.env
2. Compares with local file: /opt/es-inventory-hub/.env
3. Updates only the API-related variables (NINJA_*, THREATLOCKER_*, CONNECTWISE_*)
4. Preserves local-only variables (DB_DSN, DATABASE_URL, FLASK_ENV, etc.)
5. Logs all changes
"""

import os
import re
import sys
import logging
from pathlib import Path
from typing import Dict, Set, Tuple
from datetime import datetime

# Configure logging
LOG_DIR = Path("/var/log/es-inventory-hub")
LOG_FILE = LOG_DIR / "sync_secrets.log"

# Try to create log directory, fallback to local if permission denied
try:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
except PermissionError:
    # Fallback to local log directory
    LOG_DIR = Path(__file__).parent.parent / "logs"
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    LOG_FILE = LOG_DIR / "sync_secrets.log"

# Configure logging handlers
handlers = [logging.StreamHandler(sys.stdout)]
try:
    handlers.append(logging.FileHandler(LOG_FILE))
except PermissionError:
    # If we can't write to log file, just use console
    pass

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=handlers
)

logger = logging.getLogger(__name__)

# Paths
SOURCE_FILE = Path("/opt/shared-secrets/api-secrets.env")
TARGET_FILE = Path("/opt/es-inventory-hub/.env")
BACKUP_DIR = Path("/opt/es-inventory-hub/.env-backups")
BACKUP_DIR.mkdir(exist_ok=True)

# Variables to sync (API secrets that come from shared secrets)
# NOTE: NinjaRMM variables are NOT synced here because:
# 1. DbAI has its own Ninja client credentials (separate from Dashboard AI)
# 2. The refresh token rotates on every use
# ALL Ninja credentials are stored in: /opt/es-inventory-hub/data/ninja_refresh_token.json
SYNC_VARIABLES = {
    # ThreatLocker
    'THREATLOCKER_API_BASE_URL',
    'THREATLOCKER_API_KEY',
    'THREATLOCKER_ORGANIZATION_ID',
    
    # ConnectWise
    'CONNECTWISE_SERVER',
    'CONNECTWISE_COMPANY_ID',
    'CONNECTWISE_CLIENT_ID',
    'CONNECTWISE_PUBLIC_KEY',
    'CONNECTWISE_PRIVATE_KEY',
}

# Variables to preserve (local-only, never overwrite)
PRESERVE_VARIABLES = {
    'DB_DSN',
    'DATABASE_URL',
    'FLASK_ENV',
    'SECRET_KEY',
    'LOG_LEVEL',
    'LOG_FILE',
    'THREATLOCKER_BASE_URL',  # Local-specific variant
}


def parse_env_file(file_path: Path) -> Dict[str, str]:
    """
    Parse an .env file and return a dictionary of key-value pairs.
    
    Handles:
    - Comments (lines starting with #)
    - Empty lines
    - Key=value format
    - Preserves original format for comments and structure
    """
    env_vars = {}
    if not file_path.exists():
        logger.warning(f"File does not exist: {file_path}")
        return env_vars
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
            
            # Parse KEY=VALUE
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                # Remove quotes if present
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                env_vars[key] = value
    
    return env_vars


def read_env_file_with_structure(file_path: Path) -> Tuple[Dict[str, str], list]:
    """
    Read .env file preserving structure (comments, blank lines, order).
    
    Returns:
        - Dictionary of key-value pairs
        - List of all lines (for reconstruction)
    """
    env_vars = {}
    lines = []
    
    if not file_path.exists():
        logger.warning(f"File does not exist: {file_path}")
        return env_vars, lines
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            lines.append(line.rstrip('\n'))
            line_stripped = line.strip()
            
            # Skip comments and empty lines
            if not line_stripped or line_stripped.startswith('#'):
                continue
            
            # Parse KEY=VALUE
            if '=' in line_stripped:
                key, value = line_stripped.split('=', 1)
                key = key.strip()
                value = value.strip()
                # Remove quotes if present
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                env_vars[key] = value
    
    return env_vars, lines


def write_env_file(file_path: Path, env_vars: Dict[str, str], original_lines: list = None):
    """
    Write .env file, preserving structure when possible.
    
    If original_lines is provided, tries to update in-place.
    Otherwise, writes a new file.
    """
    if original_lines:
        # Update existing file structure
        updated_lines = []
        updated_keys = set()
        
        for line in original_lines:
            line_stripped = line.strip()
            
            # Preserve comments and empty lines
            if not line_stripped or line_stripped.startswith('#'):
                updated_lines.append(line)
                continue
            
            # Update variable lines
            if '=' in line_stripped:
                key = line_stripped.split('=', 1)[0].strip()
                
                if key in env_vars:
                    # Update this variable
                    updated_lines.append(f"{key}={env_vars[key]}")
                    updated_keys.add(key)
                else:
                    # Preserve line (might be a variable we don't manage)
                    updated_lines.append(line)
        
        # Add any new variables that weren't in the original file
        for key, value in env_vars.items():
            if key not in updated_keys:
                updated_lines.append(f"{key}={value}")
        
        # Write updated file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(updated_lines))
            if not updated_lines[-1].endswith('\n'):
                f.write('\n')
    else:
        # Write new file
        with open(file_path, 'w', encoding='utf-8') as f:
            for key, value in sorted(env_vars.items()):
                f.write(f"{key}={value}\n")


def backup_file(file_path: Path) -> Path:
    """Create a timestamped backup of the file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"{file_path.name}.{timestamp}"
    
    if file_path.exists():
        import shutil
        shutil.copy2(file_path, backup_path)
        logger.info(f"Created backup: {backup_path}")
    
    return backup_path


def sync_secrets(dry_run: bool = False) -> Tuple[bool, Dict[str, Tuple[str, str]]]:
    """
    Sync secrets from source to target file.
    
    Returns:
        - (success: bool, changes: dict of {var_name: (old_value, new_value)})
    """
    logger.info("=" * 60)
    logger.info("Starting secrets sync")
    logger.info(f"Source: {SOURCE_FILE}")
    logger.info(f"Target: {TARGET_FILE}")
    logger.info(f"Dry run: {dry_run}")
    logger.info("=" * 60)
    
    # Check if source file exists and is readable
    try:
        if not SOURCE_FILE.exists():
            logger.error(f"Source file does not exist: {SOURCE_FILE}")
            return False, {}
    except PermissionError:
        logger.error(f"Permission denied accessing source file: {SOURCE_FILE}")
        logger.error("This script requires sudo to read the shared secrets file.")
        logger.error("Run with: sudo python3 scripts/sync_secrets.py")
        return False, {}
    
    # Read source file (shared secrets)
    source_vars = parse_env_file(SOURCE_FILE)
    logger.info(f"Read {len(source_vars)} variables from source file")
    
    # Read target file (local .env)
    target_vars, target_lines = read_env_file_with_structure(TARGET_FILE)
    logger.info(f"Read {len(target_vars)} variables from target file")
    
    # Track changes
    changes = {}
    updated_vars = target_vars.copy()
    
    # Sync variables
    for var_name in SYNC_VARIABLES:
        if var_name in source_vars:
            source_value = source_vars[var_name]
            target_value = target_vars.get(var_name, None)
            
            if source_value != target_value:
                changes[var_name] = (target_value or "(not set)", source_value)
                updated_vars[var_name] = source_value
                logger.info(f"  {var_name}: '{target_value or '(not set)'}' -> '{source_value}'")
            else:
                logger.debug(f"  {var_name}: No change")
        else:
            logger.warning(f"  {var_name}: Not found in source file")
    
    # Preserve local-only variables
    for var_name in PRESERVE_VARIABLES:
        if var_name in target_vars:
            updated_vars[var_name] = target_vars[var_name]
            logger.debug(f"  {var_name}: Preserved (local-only)")
    
    # Report changes
    if changes:
        logger.info(f"\nFound {len(changes)} variable(s) to update:")
        for var_name, (old_val, new_val) in changes.items():
            logger.info(f"  {var_name}: '{old_val}' -> '{new_val}'")
    else:
        logger.info("\nNo changes needed - all variables are up to date")
    
    # Apply changes (if not dry run)
    if changes and not dry_run:
        # Create backup
        backup_path = backup_file(TARGET_FILE)
        
        # Write updated file
        write_env_file(TARGET_FILE, updated_vars, target_lines)
        logger.info(f"\nUpdated {TARGET_FILE}")
        logger.info(f"Backup saved to: {backup_path}")
        
        # Set appropriate permissions
        os.chmod(TARGET_FILE, 0o600)
        logger.info("Set file permissions to 600")
    
    logger.info("=" * 60)
    logger.info("Secrets sync completed")
    logger.info("=" * 60)
    
    return True, changes


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Sync API secrets from shared secrets file to local .env"
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be changed without making changes'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable debug logging'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        success, changes = sync_secrets(dry_run=args.dry_run)
        
        if not success:
            logger.error("Sync failed")
            sys.exit(1)
        
        if args.dry_run and changes:
            logger.info("\nDRY RUN: No changes were made. Run without --dry-run to apply changes.")
            sys.exit(0)
        elif args.dry_run and not changes:
            logger.info("\nDRY RUN: No changes needed.")
            sys.exit(0)
        elif changes:
            logger.info(f"\nSync completed successfully. {len(changes)} variable(s) updated.")
            sys.exit(0)
        else:
            logger.info("\nSync completed. No changes needed.")
            sys.exit(0)
    
    except Exception as e:
        logger.exception(f"Error during sync: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()


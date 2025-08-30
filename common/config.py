"""Configuration utilities for es-inventory-hub."""

import os


def get_dsn() -> str:
    """
    Get database connection string from environment variables.
    
    Prefers DB_DSN, then falls back to DATABASE_URL.
    Raises RuntimeError if neither is set.
    
    Returns:
        str: Database connection string
        
    Raises:
        RuntimeError: If neither DB_DSN nor DATABASE_URL is set
    """
    dsn = os.environ.get("DB_DSN")
    if dsn:
        return dsn
    
    dsn = os.environ.get("DATABASE_URL")
    if dsn:
        return dsn
    
    raise RuntimeError(
        "Database connection string not found. "
        "Please set either DB_DSN or DATABASE_URL environment variable."
    )

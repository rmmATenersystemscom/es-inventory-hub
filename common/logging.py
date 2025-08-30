"""Logging utilities for es-inventory-hub."""

import logging
import os
import sys
from typing import Optional


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger configured to write to stdout.
    
    Args:
        name: Logger name (defaults to __name__ of calling module)
        
    Returns:
        logging.Logger: Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Only configure if logger hasn't been configured yet
    if not logger.handlers:
        # Get log level from environment, default to INFO
        log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
        
        # Create handler for stdout
        handler = logging.StreamHandler(sys.stdout)
        
        # Create formatter
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        
        # Configure logger
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, log_level, logging.INFO))
        
        # Prevent propagation to avoid duplicate logs
        logger.propagate = False
    
    return logger

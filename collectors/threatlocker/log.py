"""Logging utilities for ThreatLocker collector."""

import logging
import sys
from typing import Optional


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger configured with INFO level and timestamped format.
    
    Args:
        name: Logger name (defaults to __name__ of calling module)
        
    Returns:
        logging.Logger: Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Only configure if logger hasn't been configured yet
    if not logger.handlers:
        # Create handler for stdout
        handler = logging.StreamHandler(sys.stdout)
        
        # Create formatter with exact format specified: "%Y-%m-%d %H:%M:%S %(name)s %(levelname)s: %(message)s"
        formatter = logging.Formatter(
            fmt="%(asctime)s %(name)s %(levelname)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        
        # Configure logger
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        
        # Prevent propagation to avoid duplicate logs
        logger.propagate = False
    
    return logger

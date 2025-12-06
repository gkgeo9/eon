#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Logging configuration for Fintel.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


def setup_logging(
    name: str = "fintel",
    level: int = logging.INFO,
    log_file: Optional[Path] = None,
    log_to_console: bool = True,
    log_to_file: bool = True,
    process_id: Optional[int] = None
) -> logging.Logger:
    """
    Set up logging for the application.

    Args:
        name: Logger name
        level: Logging level (logging.DEBUG, logging.INFO, etc.)
        log_file: Path to log file (if None, uses default)
        log_to_console: Whether to log to console
        log_to_file: Whether to log to file
        process_id: Optional process ID to include in logs

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Remove existing handlers to avoid duplicates
    logger.handlers = []

    # Create formatter
    if process_id is not None:
        fmt = f'%(asctime)s - [Process-{process_id}] - %(name)s - %(levelname)s - %(message)s'
    else:
        fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    formatter = logging.Formatter(fmt)

    # Console handler
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # File handler
    if log_to_file:
        if log_file is None:
            # Default log file path
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            if process_id is not None:
                log_file = Path(f"logs/fintel_process_{process_id}_{timestamp}.log")
            else:
                log_file = Path(f"logs/fintel_{timestamp}.log")

        # Create log directory if it doesn't exist
        log_file.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str = "fintel") -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: Logger name

    Returns:
        Logger instance
    """
    return logging.getLogger(name)

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Logging configuration for Fintel.

Supports log rotation for long-running batch operations.
"""

import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


# Default log rotation settings (can be overridden via environment variables)
DEFAULT_LOG_MAX_SIZE_MB = int(os.environ.get("FINTEL_LOG_MAX_SIZE_MB", "10"))
DEFAULT_LOG_BACKUP_COUNT = int(os.environ.get("FINTEL_LOG_BACKUP_COUNT", "5"))
DEFAULT_LOG_FILE = os.environ.get("FINTEL_LOG_FILE", None)


def setup_logging(
    name: str = "fintel",
    level: int = logging.INFO,
    log_file: Optional[Path] = None,
    log_to_console: bool = True,
    log_to_file: bool = True,
    process_id: Optional[int] = None,
    max_size_mb: int = DEFAULT_LOG_MAX_SIZE_MB,
    backup_count: int = DEFAULT_LOG_BACKUP_COUNT,
    use_rotation: bool = True
) -> logging.Logger:
    """
    Set up logging for the application.

    Supports log rotation to prevent disk exhaustion during long-running
    batch operations.

    Args:
        name: Logger name
        level: Logging level (logging.DEBUG, logging.INFO, etc.)
        log_file: Path to log file (if None, uses default or FINTEL_LOG_FILE env)
        log_to_console: Whether to log to console
        log_to_file: Whether to log to file
        process_id: Optional process ID to include in logs
        max_size_mb: Maximum log file size in MB before rotation (default: 10)
        backup_count: Number of backup log files to keep (default: 5)
        use_rotation: Whether to use rotating file handler (default: True)

    Returns:
        Configured logger instance

    Environment variables:
        FINTEL_LOG_FILE: Default log file path
        FINTEL_LOG_MAX_SIZE_MB: Maximum log file size in MB (default: 10)
        FINTEL_LOG_BACKUP_COUNT: Number of backup files to keep (default: 5)
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

    # File handler with optional rotation
    if log_to_file:
        # Determine log file path
        if log_file is None:
            if DEFAULT_LOG_FILE:
                log_file = Path(DEFAULT_LOG_FILE)
            else:
                # Default log file path
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                if process_id is not None:
                    log_file = Path(f"logs/fintel_process_{process_id}_{timestamp}.log")
                else:
                    log_file = Path(f"logs/fintel_{timestamp}.log")

        # Create log directory if it doesn't exist
        log_file.parent.mkdir(parents=True, exist_ok=True)

        if use_rotation:
            # Use rotating file handler to prevent disk exhaustion
            max_bytes = max_size_mb * 1024 * 1024  # Convert MB to bytes
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding='utf-8'
            )
        else:
            # Use standard file handler
            file_handler = logging.FileHandler(log_file, encoding='utf-8')

        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def setup_batch_logging(
    batch_id: str,
    level: int = logging.INFO
) -> logging.Logger:
    """
    Set up logging specifically for batch processing.

    Creates a dedicated log file for the batch with rotation enabled.

    Args:
        batch_id: Batch job ID
        level: Logging level

    Returns:
        Configured logger instance
    """
    log_file = Path(f"logs/batch_{batch_id}.log")

    return setup_logging(
        name=f"fintel.batch.{batch_id[:8]}",
        level=level,
        log_file=log_file,
        log_to_console=True,
        log_to_file=True,
        use_rotation=True,
        max_size_mb=20,  # Larger for batch operations
        backup_count=3
    )


def get_logger(name: str = "fintel") -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: Logger name

    Returns:
        Logger instance
    """
    return logging.getLogger(name)

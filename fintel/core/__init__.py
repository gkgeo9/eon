#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Core infrastructure for Fintel.
"""

from .config import FintelConfig, get_config, reset_config
from .exceptions import (
    FintelException,
    ConfigurationError,
    DataSourceError,
    DownloadError,
    ConversionError,
    ExtractionError,
    AnalysisError,
    AIProviderError,
    RateLimitError,
    StorageError,
    ValidationError,
)
from .logging import setup_logging, get_logger
from .interfaces import (
    IKeyManager,
    IRateLimiter,
    IDownloader,
    IExtractor,
    IConfig,
    IRepository,
)
from .utils import (
    ANNUAL_FILINGS,
    QUARTERLY_FILINGS,
    EVENT_FILINGS,
    is_annual_filing,
    is_quarterly_filing,
    is_event_filing,
    mask_api_key,
    get_filing_category,
)
from .result import Result, BatchResult

__all__ = [
    # Config
    "FintelConfig",
    "get_config",
    "reset_config",
    # Exceptions
    "FintelException",
    "ConfigurationError",
    "DataSourceError",
    "DownloadError",
    "ConversionError",
    "ExtractionError",
    "AnalysisError",
    "AIProviderError",
    "RateLimitError",
    "StorageError",
    "ValidationError",
    # Logging
    "setup_logging",
    "get_logger",
    # Interfaces (Protocols)
    "IKeyManager",
    "IRateLimiter",
    "IDownloader",
    "IExtractor",
    "IConfig",
    "IRepository",
    # Utilities
    "ANNUAL_FILINGS",
    "QUARTERLY_FILINGS",
    "EVENT_FILINGS",
    "is_annual_filing",
    "is_quarterly_filing",
    "is_event_filing",
    "mask_api_key",
    "get_filing_category",
    # Result types
    "Result",
    "BatchResult",
]

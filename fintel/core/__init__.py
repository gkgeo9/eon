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
from .logging import setup_logging, setup_cli_logging, get_logger
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
from .formatting import format_duration
from .analysis_types import (
    AnalysisTypeInfo,
    ANALYSIS_TYPES,
    MULTI_YEAR_TYPES,
    CLI_ANALYSIS_CHOICES,
    DEFAULT_FILING_TYPES,
    get_analysis_type,
    is_valid_analysis_type,
    requires_multi_year,
    get_ui_options,
)
from .monitoring import (
    DiskMonitor,
    ProcessMonitor,
    HealthChecker,
    check_disk_space,
    cleanup_orphaned_chrome,
)

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
    # Formatting
    "format_duration",
    # Analysis types
    "AnalysisTypeInfo",
    "ANALYSIS_TYPES",
    "MULTI_YEAR_TYPES",
    "CLI_ANALYSIS_CHOICES",
    "DEFAULT_FILING_TYPES",
    "get_analysis_type",
    "is_valid_analysis_type",
    "requires_multi_year",
    "get_ui_options",
    # Monitoring
    "DiskMonitor",
    "ProcessMonitor",
    "HealthChecker",
    "check_disk_space",
    "cleanup_orphaned_chrome",
]

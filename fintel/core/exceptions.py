#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Custom exceptions for the Fintel platform.
"""


class FintelException(Exception):
    """Base exception for all Fintel errors."""
    pass


class ConfigurationError(FintelException):
    """Raised when there's a configuration issue."""
    pass


class DataSourceError(FintelException):
    """Raised when there's an error fetching data from a source."""
    pass


class DownloadError(DataSourceError):
    """Raised when downloading data fails."""
    pass


class ConversionError(DataSourceError):
    """Raised when converting data fails."""
    pass


class ExtractionError(DataSourceError):
    """Raised when extracting text from a document fails."""
    pass


class AnalysisError(FintelException):
    """Raised when analysis fails."""
    pass


class AIProviderError(FintelException):
    """Raised when there's an error with the AI provider."""
    pass


class RateLimitError(AIProviderError):
    """Raised when rate limit is exceeded."""
    pass


class KeyQuotaExhaustedError(AIProviderError):
    """Raised when all API keys have exhausted their daily quota."""
    pass


class StorageError(FintelException):
    """Raised when there's an error with data storage."""
    pass


class ValidationError(FintelException):
    """Raised when data validation fails."""
    pass

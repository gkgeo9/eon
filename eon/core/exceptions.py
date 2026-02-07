#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Custom exceptions for the EON platform.
"""


class EonException(Exception):
    """Base exception for all EON errors."""
    pass


class ConfigurationError(EonException):
    """Raised when there's a configuration issue."""
    pass


class DataSourceError(EonException):
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


class AnalysisError(EonException):
    """Raised when analysis fails."""
    pass


class AIProviderError(EonException):
    """Raised when there's an error with the AI provider."""
    pass


class RateLimitError(AIProviderError):
    """Raised when rate limit is exceeded."""
    pass


class KeyQuotaExhaustedError(AIProviderError):
    """Raised when all API keys have exhausted their daily quota."""
    pass


class ContextLengthExceededError(AIProviderError):
    """Raised when input exceeds the model's context length limit."""
    pass


class StorageError(EonException):
    """Raised when there's an error with data storage."""
    pass


class ValidationError(EonException):
    """Raised when data validation fails."""
    pass

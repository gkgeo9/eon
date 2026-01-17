#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Central API configuration for rate limits and usage tracking.

This file contains all configurable API limits and settings.
Modify these values to adjust rate limiting behavior.
"""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass(frozen=True)
class APILimits:
    """
    Central configuration for API rate limits.

    These values can be adjusted based on your Google Gemini API tier.
    Default values are conservative for free tier usage.
    """

    # Daily request limit per API key
    # Free tier: ~1500 RPD, but we set lower to be safe
    # Adjust this based on your API tier
    DAILY_LIMIT_PER_KEY: int = 20

    # Mandatory sleep after each request (seconds)
    # Gemini free tier has ~15 RPM limit, 65s ensures we stay under
    SLEEP_AFTER_REQUEST: int = 65

    # Requests per minute limit (for future use)
    REQUESTS_PER_MINUTE: int = 15

    # Maximum concurrent requests per key
    MAX_CONCURRENT_PER_KEY: int = 1

    # Maximum total concurrent requests across all keys
    # This controls how many parallel API calls can run simultaneously
    # Set higher for more parallelism (requires more API keys)
    MAX_CONCURRENT_REQUESTS: int = 5

    # Time zone for daily reset (Google uses Pacific time)
    RESET_TIMEZONE: str = "America/Los_Angeles"

    # Grace period before considering a key "exhausted" (percentage of limit)
    # e.g., 0.95 means warn when at 95% of daily limit
    WARNING_THRESHOLD: float = 0.80

    # Directory for storing usage data
    USAGE_DATA_DIR: str = "data/api_usage"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'daily_limit_per_key': self.DAILY_LIMIT_PER_KEY,
            'sleep_after_request': self.SLEEP_AFTER_REQUEST,
            'requests_per_minute': self.REQUESTS_PER_MINUTE,
            'max_concurrent_per_key': self.MAX_CONCURRENT_PER_KEY,
            'max_concurrent_requests': self.MAX_CONCURRENT_REQUESTS,
            'reset_timezone': self.RESET_TIMEZONE,
            'warning_threshold': self.WARNING_THRESHOLD,
            'usage_data_dir': self.USAGE_DATA_DIR,
        }


@dataclass(frozen=True)
class SECLimits:
    """
    Configuration for SEC EDGAR rate limits.

    SEC's fair access policy recommends no more than 10 requests per second.
    For batch processing, more conservative limits are recommended to avoid
    overwhelming SEC servers when running with multiple workers.

    All values are configurable via environment variables.
    """

    # Delay between SEC requests (seconds)
    # Min: 0.5 (aggressive) | Recommended: 2.0 | Max: 10.0 (very conservative)
    REQUEST_DELAY: float = 2.0

    # Maximum concurrent SEC requests
    # Limits parallel downloads to avoid overwhelming SEC servers
    # Min: 1 (sequential) | Recommended: 5 | Max: 10 (aggressive)
    MAX_CONCURRENT_REQUESTS: int = 5

    # Stagger delay between batch worker starts (seconds)
    # Prevents thundering herd when multiple workers start batch processing
    # Min: 0 (no stagger) | Recommended: 30 | Max: 120 (very conservative)
    WORKER_STAGGER_DELAY: int = 30

    # Directory for SEC lock files (same as Gemini for simplicity)
    LOCK_DIR: str = "data/api_usage"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'request_delay': self.REQUEST_DELAY,
            'max_concurrent_requests': self.MAX_CONCURRENT_REQUESTS,
            'worker_stagger_delay': self.WORKER_STAGGER_DELAY,
            'lock_dir': self.LOCK_DIR,
        }


# Global instances - import these to use the limits
API_LIMITS = APILimits()


def get_api_limits() -> APILimits:
    """Get the global API limits configuration."""
    return API_LIMITS


def get_sec_limits() -> SECLimits:
    """
    Get SEC limits from environment variables or use defaults.

    Environment variables:
        FINTEL_SEC_REQUEST_DELAY: Seconds between SEC requests (default: 2.0)
        FINTEL_SEC_MAX_CONCURRENT: Max parallel SEC requests (default: 5)
        FINTEL_SEC_WORKER_STAGGER_DELAY: Seconds between worker starts (default: 30)

    Returns:
        SECLimits instance with configured values
    """
    import os
    return SECLimits(
        REQUEST_DELAY=float(os.getenv('FINTEL_SEC_REQUEST_DELAY', 2.0)),
        MAX_CONCURRENT_REQUESTS=int(os.getenv('FINTEL_SEC_MAX_CONCURRENT', 5)),
        WORKER_STAGGER_DELAY=int(os.getenv('FINTEL_SEC_WORKER_STAGGER_DELAY', 30)),
    )

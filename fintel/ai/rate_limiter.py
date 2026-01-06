#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Rate limiting for API requests with mandatory sleep periods.

Uses the centralized API configuration and persistent usage tracker
for accurate rate limiting across multiple processes.
"""

import time
from typing import Dict, Optional, Any
from datetime import datetime, timedelta

from fintel.core import get_logger
from .api_config import get_api_limits, API_LIMITS
from .usage_tracker import get_usage_tracker, APIUsageTracker


class RateLimiter:
    """
    Rate limiter with mandatory sleep after each API request.

    Features:
    - Uses centralized API configuration from api_config.py
    - Persistent usage tracking via APIUsageTracker
    - Thread-safe for parallel execution
    - Mandatory sleep after each request for rate limit compliance

    Example:
        limiter = RateLimiter()

        # After making an API call:
        limiter.record_and_sleep(api_key)  # Records usage and sleeps
    """

    def __init__(
        self,
        sleep_after_request: Optional[int] = None,
        tracker: Optional[APIUsageTracker] = None
    ):
        """
        Initialize the rate limiter.

        Args:
            sleep_after_request: Override for sleep duration (uses config default if None)
            tracker: Optional custom usage tracker (uses global singleton if not provided)
        """
        self.limits = get_api_limits()
        self.tracker = tracker or get_usage_tracker()

        # Use provided sleep time or fall back to config
        self.sleep_after_request = (
            sleep_after_request if sleep_after_request is not None
            else self.limits.SLEEP_AFTER_REQUEST
        )

        self.logger = get_logger(f"{__name__}.RateLimiter")
        self.logger.info(
            f"Initialized rate limiter "
            f"(sleep={self.sleep_after_request}s, limit={self.limits.DAILY_LIMIT_PER_KEY}/key/day)"
        )

    def record_and_sleep(self, api_key: str, error: bool = False):
        """
        Record API usage and sleep for the configured duration.

        This is the MANDATORY pattern after every API call:
        1. Record the usage to persistent storage
        2. Sleep for configured seconds (default from api_config.py)

        Args:
            api_key: The API key that was just used
            error: Whether the request resulted in an error

        Note:
            This method ALWAYS sleeps, regardless of usage count.
            This ensures rate limit compliance.
        """
        # Record usage to persistent tracker
        self.tracker.record_request(api_key, error=error)

        # Get current status for logging
        usage_today = self.tracker.get_usage_today(api_key)
        remaining = self.tracker.get_remaining_today(api_key)

        # Only log last 4 characters of API key for security
        key_suffix = api_key[-4:] if len(api_key) >= 4 else "****"
        self.logger.info(
            f"API call recorded for key ...{key_suffix} "
            f"(usage today: {usage_today}/{self.limits.DAILY_LIMIT_PER_KEY}, "
            f"remaining: {remaining})"
        )

        # Warn if near limit
        if self.tracker.is_near_limit(api_key):
            self.logger.warning(
                f"Key ...{key_suffix} is approaching daily limit! "
                f"Only {remaining} requests remaining."
            )

        # MANDATORY sleep after every request
        if self.sleep_after_request > 0:
            self.logger.debug(f"Sleeping for {self.sleep_after_request} seconds...")
            time.sleep(self.sleep_after_request)

    def can_make_request(self, api_key: str) -> bool:
        """
        Check if a key can make another request today.

        Args:
            api_key: The API key to check

        Returns:
            True if under daily limit, False otherwise
        """
        return self.tracker.can_make_request(api_key)

    def get_usage_today(self, api_key: str) -> int:
        """
        Get usage count for a key today.

        Args:
            api_key: The API key to check

        Returns:
            Number of requests made today
        """
        return self.tracker.get_usage_today(api_key)

    def get_remaining_today(self, api_key: str) -> int:
        """
        Get remaining requests for a key today.

        Args:
            api_key: The API key to check

        Returns:
            Number of requests remaining today
        """
        return self.tracker.get_remaining_today(api_key)

    def wait_for_reset(self) -> int:
        """
        Calculate seconds until midnight PST (Google's rate limit reset time).

        Returns:
            Seconds until midnight Pacific Time

        Note:
            Google rate limits reset at midnight PST/PDT.
            This is useful for waiting when all keys are exhausted.
        """
        try:
            import pytz
            pst = pytz.timezone(self.limits.RESET_TIMEZONE)
            now_pst = datetime.now(pst)

            # Calculate next midnight PST (always tomorrow since we're past midnight)
            midnight_pst = (now_pst + timedelta(days=1)).replace(
                hour=0, minute=0, second=1, microsecond=0
            )

            wait_seconds = int((midnight_pst - now_pst).total_seconds())
            return max(0, wait_seconds)  # Ensure non-negative

        except ImportError:
            self.logger.warning(
                "pytz not installed. Using local timezone instead. "
                "Install pytz for accurate PST reset timing."
            )
            # Fallback to local timezone
            now = datetime.now()
            midnight = (now + timedelta(days=1)).replace(
                hour=0, minute=0, second=1, microsecond=0
            )
            return max(0, int((midnight - now).total_seconds()))

    def get_stats(self) -> Dict[str, Any]:
        """
        Get rate limiting statistics.

        Returns:
            Dictionary with rate limiter configuration and status
        """
        return {
            'sleep_after_request': self.sleep_after_request,
            'daily_limit_per_key': self.limits.DAILY_LIMIT_PER_KEY,
            'requests_per_minute': self.limits.REQUESTS_PER_MINUTE,
            'warning_threshold': self.limits.WARNING_THRESHOLD,
            'reset_timezone': self.limits.RESET_TIMEZONE,
        }

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"RateLimiter(sleep={self.sleep_after_request}s, "
            f"limit={self.limits.DAILY_LIMIT_PER_KEY}/key/day)"
        )

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Rate limiting for API requests with mandatory sleep periods.

Enforces Google Gemini API rate limits:
- Maximum 500 requests per day per key
- 65-second sleep after each request
"""

import time
from typing import Dict
from datetime import datetime, timedelta
from fintel.core import get_logger


class RateLimiter:
    """
    Rate limiter with mandatory sleep after each API request.

    Based on legacy pattern from contrarian_evidence_based.py (SimpleAPITracker).
    Enforces 65-second sleep AFTER every API call to avoid rate limits.

    Example:
        limiter = RateLimiter(sleep_after_request=65, max_requests_per_day=500)

        # After making an API call:
        limiter.record_and_sleep(api_key)  # Records usage and sleeps 65 seconds
    """

    def __init__(
        self,
        sleep_after_request: int = 65,
        max_requests_per_day: int = 500
    ):
        """
        Initialize the rate limiter.

        Args:
            sleep_after_request: Seconds to sleep after each request (default: 65)
            max_requests_per_day: Maximum requests per day per key (default: 500)
        """
        self.sleep_after_request = sleep_after_request
        self.max_requests_per_day = max_requests_per_day

        # Track usage per key: {key: {date: count}}
        self.usage: Dict[str, Dict[str, int]] = {}

        self.logger = get_logger(f"{__name__}.RateLimiter")
        self.logger.info(
            f"Initialized rate limiter "
            f"(sleep={sleep_after_request}s, limit={max_requests_per_day}/day)"
        )

    def record_and_sleep(self, api_key: str):
        """
        Record API usage and sleep for the configured duration.

        This is the MANDATORY pattern after every API call:
        1. Record the usage
        2. Sleep for configured seconds (default 65)

        Args:
            api_key: The API key that was just used

        Note:
            This method ALWAYS sleeps, regardless of usage count.
            This matches the legacy pattern to ensure rate limit compliance.
        """
        # Initialize tracking for this key if needed
        if api_key not in self.usage:
            self.usage[api_key] = {}

        today = datetime.now().strftime('%Y-%m-%d')

        if today not in self.usage[api_key]:
            self.usage[api_key][today] = 0

        self.usage[api_key][today] += 1

        usage_today = self.usage[api_key][today]
        remaining = self.max_requests_per_day - usage_today

        self.logger.info(
            f"API call recorded for key {api_key[:10]}... "
            f"(usage today: {usage_today}/{self.max_requests_per_day}, "
            f"remaining: {remaining})"
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
        if api_key not in self.usage:
            return True

        today = datetime.now().strftime('%Y-%m-%d')
        usage_today = self.usage.get(api_key, {}).get(today, 0)

        return usage_today < self.max_requests_per_day

    def get_usage_today(self, api_key: str) -> int:
        """
        Get usage count for a key today.

        Args:
            api_key: The API key to check

        Returns:
            Number of requests made today
        """
        today = datetime.now().strftime('%Y-%m-%d')
        return self.usage.get(api_key, {}).get(today, 0)

    def get_remaining_today(self, api_key: str) -> int:
        """
        Get remaining requests for a key today.

        Args:
            api_key: The API key to check

        Returns:
            Number of requests remaining today
        """
        usage_today = self.get_usage_today(api_key)
        return max(0, self.max_requests_per_day - usage_today)

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
            pst = pytz.timezone('America/Los_Angeles')
            now_pst = datetime.now(pst)

            # Calculate next midnight PST
            midnight_pst = now_pst.replace(
                hour=0, minute=0, second=1, microsecond=0
            )

            # If we're past midnight today, use tomorrow's midnight
            if now_pst.hour > 0 or now_pst.minute > 0:
                midnight_pst = midnight_pst + timedelta(days=1)

            wait_seconds = int((midnight_pst - now_pst).total_seconds())
            return wait_seconds

        except ImportError:
            self.logger.warning(
                "pytz not installed. Using local timezone instead. "
                "Install pytz for accurate PST reset timing."
            )
            # Fallback to local timezone
            now = datetime.now()
            midnight = now.replace(hour=0, minute=0, second=1, microsecond=0)
            if now.hour > 0 or now.minute > 0:
                midnight = midnight + timedelta(days=1)
            return int((midnight - now).total_seconds())

    def reset_usage(self, api_key: str = None):
        """
        Reset usage tracking (mainly for testing).

        Args:
            api_key: Specific key to reset, or None to reset all
        """
        if api_key:
            if api_key in self.usage:
                self.usage[api_key] = {}
                self.logger.info(f"Reset usage for key {api_key[:10]}...")
        else:
            self.usage = {}
            self.logger.info("Reset usage for all keys")

    def get_stats(self) -> Dict[str, int]:
        """
        Get rate limiting statistics.

        Returns:
            Dictionary with sleep duration and max requests
        """
        return {
            'sleep_after_request': self.sleep_after_request,
            'max_requests_per_day': self.max_requests_per_day,
            'total_keys_tracked': len(self.usage)
        }

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"RateLimiter(sleep={self.sleep_after_request}s, "
            f"limit={self.max_requests_per_day}/day)"
        )

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
API key management with round-robin rotation and usage tracking.
"""

from typing import List, Dict, Optional
from datetime import datetime

from fintel.core import get_logger, ConfigurationError


class APIKeyManager:
    """
    Manages multiple API keys with round-robin rotation and usage tracking.

    Example:
        manager = APIKeyManager(["key1", "key2", "key3"])

        # Get next available key
        key = manager.get_next_key()

        # Record usage
        manager.record_usage(key)

        # Check usage
        stats = manager.get_usage_stats()
    """

    def __init__(
        self,
        api_keys: List[str],
        max_requests_per_day: int = 500
    ):
        """
        Initialize the API key manager.

        Args:
            api_keys: List of API keys to manage
            max_requests_per_day: Maximum requests per day per key

        Raises:
            ConfigurationError: If no API keys provided
        """
        if not api_keys:
            raise ConfigurationError("No API keys provided")

        self.api_keys = list(api_keys)  # Make a copy
        self.max_requests_per_day = max_requests_per_day
        self.current_index = 0

        # Track usage per key: {key: {date: count}}
        self.usage: Dict[str, Dict[str, int]] = {
            key: {} for key in self.api_keys
        }

        self.logger = get_logger(f"{__name__}.APIKeyManager")
        self.logger.info(f"Initialized with {len(self.api_keys)} API keys")

    def get_next_key(self) -> str:
        """
        Get the next API key using round-robin rotation.

        Returns:
            API key string

        Note:
            This uses simple round-robin. For more sophisticated
            load balancing, consider usage-based selection.
        """
        key = self.api_keys[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.api_keys)
        return key

    def get_least_used_key(self) -> str:
        """
        Get the API key with the least usage today.

        Returns:
            API key string with lowest usage

        Note:
            More sophisticated than round-robin for better
            load distribution.
        """
        today = datetime.now().strftime('%Y-%m-%d')

        # Find key with minimum usage today
        min_usage = float('inf')
        best_key = self.api_keys[0]

        for key in self.api_keys:
            usage_today = self.usage[key].get(today, 0)
            if usage_today < min_usage:
                min_usage = usage_today
                best_key = key

        return best_key

    def record_usage(self, api_key: str, count: int = 1):
        """
        Record API usage for a key.

        Args:
            api_key: The API key that was used
            count: Number of requests made (default: 1)
        """
        if api_key not in self.usage:
            self.logger.warning(f"Unknown API key: {api_key[:10]}...")
            return

        today = datetime.now().strftime('%Y-%m-%d')

        if today not in self.usage[api_key]:
            self.usage[api_key][today] = 0

        self.usage[api_key][today] += count

        self.logger.debug(
            f"Recorded {count} request(s) for key {api_key[:10]}... "
            f"(total today: {self.usage[api_key][today]})"
        )

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

    def can_make_request(self, api_key: str) -> bool:
        """
        Check if a key can make another request today.

        Args:
            api_key: The API key to check

        Returns:
            True if under daily limit, False otherwise
        """
        usage_today = self.get_usage_today(api_key)
        return usage_today < self.max_requests_per_day

    def get_available_keys(self) -> List[str]:
        """
        Get list of keys that haven't hit daily limit.

        Returns:
            List of available API keys
        """
        return [
            key for key in self.api_keys
            if self.can_make_request(key)
        ]

    def get_usage_stats(self) -> Dict[str, Dict[str, int]]:
        """
        Get usage statistics for all keys.

        Returns:
            Dictionary with usage stats per key
        """
        today = datetime.now().strftime('%Y-%m-%d')
        stats = {}

        for key in self.api_keys:
            key_short = f"{key[:10]}..."
            usage_today = self.get_usage_today(key)
            remaining = self.max_requests_per_day - usage_today

            stats[key_short] = {
                'used_today': usage_today,
                'remaining': remaining,
                'limit': self.max_requests_per_day,
                'percentage_used': round(
                    (usage_today / self.max_requests_per_day) * 100, 1
                )
            }

        return stats

    def reset_usage(self, api_key: Optional[str] = None):
        """
        Reset usage tracking.

        Args:
            api_key: Specific key to reset, or None to reset all
        """
        if api_key:
            self.usage[api_key] = {}
            self.logger.info(f"Reset usage for key {api_key[:10]}...")
        else:
            self.usage = {key: {} for key in self.api_keys}
            self.logger.info("Reset usage for all keys")

    @property
    def total_keys(self) -> int:
        """Total number of API keys."""
        return len(self.api_keys)

    @property
    def available_keys_count(self) -> int:
        """Number of keys still available today."""
        return len(self.get_available_keys())

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"APIKeyManager(keys={self.total_keys}, "
            f"available={self.available_keys_count})"
        )

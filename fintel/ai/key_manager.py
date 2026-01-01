#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
API key management with intelligent key selection and persistent usage tracking.

Uses the APIUsageTracker for persistent, thread-safe usage tracking across
multiple processes and sessions.
"""

from typing import List, Dict, Optional, Any
from datetime import datetime

from fintel.core import get_logger, ConfigurationError
from .api_config import get_api_limits
from .usage_tracker import get_usage_tracker, APIUsageTracker


class APIKeyManager:
    """
    Manages multiple API keys with intelligent selection and persistent usage tracking.

    Features:
    - Persistent usage tracking via JSON files (survives restarts)
    - Thread-safe for parallel execution
    - Intelligent key selection (least-used strategy)
    - Configurable daily limits via api_config.py

    Example:
        manager = APIKeyManager(["key1", "key2", "key3"])

        # Get best available key (least used)
        key = manager.get_least_used_key()

        # Record usage (automatically done by RateLimiter)
        manager.record_usage(key)

        # Check usage
        stats = manager.get_usage_stats()
    """

    def __init__(
        self,
        api_keys: List[str],
        tracker: Optional[APIUsageTracker] = None
    ):
        """
        Initialize the API key manager.

        Args:
            api_keys: List of API keys to manage
            tracker: Optional custom usage tracker (uses global singleton if not provided)

        Raises:
            ConfigurationError: If no API keys provided
        """
        if not api_keys:
            raise ConfigurationError("No API keys provided")

        # Filter out empty keys
        self.api_keys = [k for k in api_keys if k and k.strip()]

        if not self.api_keys:
            raise ConfigurationError("All provided API keys are empty")

        self.limits = get_api_limits()
        self.tracker = tracker or get_usage_tracker()
        self.current_index = 0

        self.logger = get_logger(f"{__name__}.APIKeyManager")
        self.logger.info(
            f"Initialized with {len(self.api_keys)} API keys "
            f"(daily limit: {self.limits.DAILY_LIMIT_PER_KEY}/key)"
        )

        # Log initial status
        available = len(self.get_available_keys())
        self.logger.info(f"Keys available today: {available}/{len(self.api_keys)}")

    def get_next_key(self) -> str:
        """
        Get the next API key using round-robin rotation.

        Returns:
            API key string

        Note:
            For better load balancing, use get_least_used_key() instead.
        """
        key = self.api_keys[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.api_keys)
        return key

    def get_least_used_key(self) -> Optional[str]:
        """
        Get the API key with the least usage today.

        Returns:
            API key string with lowest usage, or None if all exhausted

        Note:
            For parallel/batch operations, use reserve_key() instead
            to prevent race conditions where multiple threads get the same key.
        """
        key = self.tracker.get_least_used_key(self.api_keys)

        if key is None:
            self.logger.error(
                f"All {len(self.api_keys)} API keys have reached their daily limit "
                f"of {self.limits.DAILY_LIMIT_PER_KEY} requests!"
            )
            # Try to return any key as last resort (let the API return the error)
            return self.api_keys[0] if self.api_keys else None

        return key

    def reserve_key(self) -> Optional[str]:
        """
        Atomically reserve and return the best available API key.

        This is the RECOMMENDED method for parallel/batch operations.
        It ensures each thread gets a unique key by using atomic reservation.

        Returns:
            Reserved API key, or None if no keys available

        Note:
            MUST call release_key() after the request is complete!
        """
        key = self.tracker.reserve_and_get_key(self.api_keys)

        if key is None:
            self.logger.error(
                f"No API keys available! All {len(self.api_keys)} keys are either "
                f"reserved by other threads or have reached their daily limit."
            )

        return key

    def release_key(self, api_key: str):
        """
        Release a previously reserved API key.

        Must be called after reserve_key() when the request is complete.

        Args:
            api_key: The API key to release
        """
        self.tracker.release_key(api_key)

    def record_usage(self, api_key: str, error: bool = False):
        """
        Record API usage for a key.

        Args:
            api_key: The API key that was used
            error: Whether the request resulted in an error
        """
        if api_key not in self.api_keys:
            key_id = api_key[-4:] if len(api_key) >= 4 else "****"
            self.logger.warning(f"Unknown API key: ...{key_id}")
            return

        self.tracker.record_request(api_key, error=error)

        # Log warning if near limit
        if self.tracker.is_near_limit(api_key):
            key_id = api_key[-4:] if len(api_key) >= 4 else "****"
            remaining = self.tracker.get_remaining_today(api_key)
            self.logger.warning(
                f"Key ...{key_id} is near daily limit! "
                f"Remaining: {remaining}/{self.limits.DAILY_LIMIT_PER_KEY}"
            )

    def get_usage_today(self, api_key: str) -> int:
        """Get usage count for a key today."""
        return self.tracker.get_usage_today(api_key)

    def can_make_request(self, api_key: str) -> bool:
        """Check if a key can make another request today."""
        return self.tracker.can_make_request(api_key)

    def get_available_keys(self) -> List[str]:
        """Get list of keys that haven't hit daily limit."""
        return self.tracker.get_available_keys(self.api_keys)

    def get_usage_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        Get comprehensive usage statistics for all keys.

        Returns:
            Dictionary with usage stats per key
        """
        return self.tracker.get_all_usage_stats(self.api_keys)

    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of current API key status.

        Returns:
            Dictionary with summary statistics
        """
        stats = self.get_usage_stats()
        total_keys = len(self.api_keys)
        available_keys = len(self.get_available_keys())
        exhausted_keys = total_keys - available_keys

        total_used = sum(s['used_today'] for s in stats.values())
        total_capacity = total_keys * self.limits.DAILY_LIMIT_PER_KEY
        total_remaining = total_capacity - total_used

        return {
            'total_keys': total_keys,
            'available_keys': available_keys,
            'exhausted_keys': exhausted_keys,
            'daily_limit_per_key': self.limits.DAILY_LIMIT_PER_KEY,
            'total_capacity': total_capacity,
            'total_used_today': total_used,
            'total_remaining_today': total_remaining,
            'utilization_percent': round((total_used / total_capacity) * 100, 1) if total_capacity > 0 else 0,
            'keys_near_limit': sum(1 for s in stats.values() if s['near_limit']),
        }

    def reset_usage(self, api_key: Optional[str] = None):
        """
        Reset usage tracking.

        Args:
            api_key: Specific key to reset, or None to reset all
        """
        if api_key:
            self.tracker.reset_key_usage(api_key)
        else:
            self.tracker.reset_all_usage()

    @property
    def total_keys(self) -> int:
        """Total number of API keys."""
        return len(self.api_keys)

    @property
    def available_keys_count(self) -> int:
        """Number of keys still available today."""
        return len(self.get_available_keys())

    @property
    def daily_limit(self) -> int:
        """Daily limit per key."""
        return self.limits.DAILY_LIMIT_PER_KEY

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"APIKeyManager(keys={self.total_keys}, "
            f"available={self.available_keys_count}, "
            f"limit={self.daily_limit}/key/day)"
        )

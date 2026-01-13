#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Persistent API usage tracker with file locking for parallel execution safety.

Each API key has its own JSON file to track usage, avoiding conflicts
when multiple processes/threads access the same key.
"""

import json
import os
import fcntl
import hashlib
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field, asdict

from fintel.core import get_logger, get_config
from .api_config import get_api_limits, API_LIMITS


@dataclass
class DailyUsage:
    """Usage data for a single day."""
    date: str
    request_count: int = 0
    timestamps: List[str] = field(default_factory=list)  # ISO timestamps of each request
    errors: int = 0
    last_request_at: Optional[str] = None


@dataclass
class KeyUsageData:
    """Complete usage data for a single API key."""
    key_id: str  # Masked key identifier (last 4 chars)
    key_hash: str  # SHA256 hash for unique identification
    created_at: str
    daily_usage: Dict[str, DailyUsage] = field(default_factory=dict)
    total_requests: int = 0
    total_errors: int = 0
    last_used_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'key_id': self.key_id,
            'key_hash': self.key_hash,
            'created_at': self.created_at,
            'daily_usage': {
                date: asdict(usage) for date, usage in self.daily_usage.items()
            },
            'total_requests': self.total_requests,
            'total_errors': self.total_errors,
            'last_used_at': self.last_used_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'KeyUsageData':
        """Create from dictionary."""
        daily_usage = {}
        for date, usage_data in data.get('daily_usage', {}).items():
            daily_usage[date] = DailyUsage(
                date=usage_data['date'],
                request_count=usage_data.get('request_count', 0),
                timestamps=usage_data.get('timestamps', []),
                errors=usage_data.get('errors', 0),
                last_request_at=usage_data.get('last_request_at'),
            )

        return cls(
            key_id=data['key_id'],
            key_hash=data['key_hash'],
            created_at=data['created_at'],
            daily_usage=daily_usage,
            total_requests=data.get('total_requests', 0),
            total_errors=data.get('total_errors', 0),
            last_used_at=data.get('last_used_at'),
        )


class APIUsageTracker:
    """
    Thread-safe, persistent API usage tracker with key reservation.

    Each API key's usage is stored in a separate JSON file with file locking
    to ensure safe concurrent access from multiple processes/threads.

    IMPORTANT: For parallel/batch operations, use reserve_and_get_key() instead
    of get_least_used_key() to prevent multiple threads from getting the same key.

    Usage:
        tracker = APIUsageTracker()

        # For single operations:
        if tracker.can_make_request(api_key):
            tracker.record_request(api_key)

        # For parallel batch operations (RECOMMENDED):
        key = tracker.reserve_and_get_key(api_keys)
        if key:
            try:
                # make the request
                tracker.record_request(key)
            finally:
                tracker.release_key(key)

        # Get least used key (NOT for parallel use - use reserve_and_get_key instead)
        best_key = tracker.get_least_used_key(api_keys)
    """

    def __init__(self, usage_dir: Optional[Path] = None):
        """
        Initialize the usage tracker.

        Args:
            usage_dir: Directory to store usage files. Defaults to data/api_usage/
        """
        self.logger = get_logger(f"{__name__}.APIUsageTracker")
        self.limits = get_api_limits()

        # Thread-safe key reservation tracking
        self._reservation_lock = threading.Lock()
        self._reserved_keys: Set[str] = set()  # Keys currently in use by threads
        self._key_usage_counts: Dict[str, int] = {}  # In-flight request counts per key

        # Determine usage directory
        if usage_dir:
            self.usage_dir = Path(usage_dir)
        else:
            config = get_config()
            self.usage_dir = config.data_dir / "api_usage"

        # Create usage directory
        self.usage_dir.mkdir(parents=True, exist_ok=True)

        self.logger.info(
            f"APIUsageTracker initialized "
            f"(dir={self.usage_dir}, daily_limit={self.limits.DAILY_LIMIT_PER_KEY})"
        )

    def _get_key_id(self, api_key: str) -> str:
        """Get masked key identifier (last 4 characters)."""
        return api_key[-4:] if len(api_key) >= 4 else "****"

    def _get_key_hash(self, api_key: str) -> str:
        """Get SHA256 hash of the key for unique file naming."""
        return hashlib.sha256(api_key.encode()).hexdigest()[:16]

    def _get_usage_file(self, api_key: str) -> Path:
        """Get the usage file path for an API key."""
        key_hash = self._get_key_hash(api_key)
        return self.usage_dir / f"usage_{key_hash}.json"

    def _load_usage_data(self, api_key: str) -> KeyUsageData:
        """
        Load usage data for a key from its JSON file.

        Uses file locking for safe concurrent access.
        """
        usage_file = self._get_usage_file(api_key)
        key_id = self._get_key_id(api_key)
        key_hash = self._get_key_hash(api_key)

        if not usage_file.exists():
            # Create new usage data
            return KeyUsageData(
                key_id=key_id,
                key_hash=key_hash,
                created_at=datetime.now().isoformat(),
            )

        try:
            with open(usage_file, 'r') as f:
                # Acquire shared lock for reading
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                try:
                    data = json.load(f)
                    return KeyUsageData.from_dict(data)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except (json.JSONDecodeError, KeyError) as e:
            self.logger.warning(f"Corrupted usage file for key ...{key_id}, resetting: {e}")
            return KeyUsageData(
                key_id=key_id,
                key_hash=key_hash,
                created_at=datetime.now().isoformat(),
            )

    def _save_usage_data(self, api_key: str, data: KeyUsageData):
        """
        Save usage data to the JSON file.

        Uses exclusive file locking for safe concurrent writes.
        """
        usage_file = self._get_usage_file(api_key)

        # Write to temp file first, then rename (atomic operation)
        temp_file = usage_file.with_suffix('.tmp')

        try:
            with open(temp_file, 'w') as f:
                # Acquire exclusive lock for writing
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    json.dump(data.to_dict(), f, indent=2)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)

            # Atomic rename
            temp_file.rename(usage_file)

        except Exception as e:
            self.logger.error(f"Failed to save usage data: {e}")
            if temp_file.exists():
                temp_file.unlink()
            raise

    def _get_today(self) -> str:
        """Get today's date string in YYYY-MM-DD format."""
        return datetime.now().strftime('%Y-%m-%d')

    def record_request(self, api_key: str, error: bool = False) -> bool:
        """
        Record an API request for a key.

        Args:
            api_key: The API key that was used
            error: Whether the request resulted in an error

        Returns:
            True if recorded successfully
        """
        usage_file = self._get_usage_file(api_key)
        key_id = self._get_key_id(api_key)
        today = self._get_today()
        now = datetime.now().isoformat()

        try:
            # Use exclusive lock for the entire read-modify-write operation
            with open(usage_file, 'a+') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    # Read existing data
                    f.seek(0)
                    content = f.read()

                    if content:
                        data = KeyUsageData.from_dict(json.loads(content))
                    else:
                        data = KeyUsageData(
                            key_id=key_id,
                            key_hash=self._get_key_hash(api_key),
                            created_at=now,
                        )

                    # Update daily usage
                    if today not in data.daily_usage:
                        data.daily_usage[today] = DailyUsage(date=today)

                    daily = data.daily_usage[today]
                    daily.request_count += 1
                    daily.timestamps.append(now)
                    daily.last_request_at = now

                    if error:
                        daily.errors += 1
                        data.total_errors += 1

                    # Update totals
                    data.total_requests += 1
                    data.last_used_at = now

                    # Write back
                    f.seek(0)
                    f.truncate()
                    json.dump(data.to_dict(), f, indent=2)

                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)

            self.logger.debug(
                f"Recorded request for key ...{key_id} "
                f"(today: {data.daily_usage[today].request_count}/{self.limits.DAILY_LIMIT_PER_KEY})"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to record request: {e}")
            return False

    def get_usage_today(self, api_key: str) -> int:
        """Get today's request count for a key."""
        data = self._load_usage_data(api_key)
        today = self._get_today()

        if today in data.daily_usage:
            return data.daily_usage[today].request_count
        return 0

    def get_remaining_today(self, api_key: str) -> int:
        """Get remaining requests for a key today."""
        used = self.get_usage_today(api_key)
        return max(0, self.limits.DAILY_LIMIT_PER_KEY - used)

    def can_make_request(self, api_key: str) -> bool:
        """Check if a key can make another request today."""
        return self.get_remaining_today(api_key) > 0

    def is_near_limit(self, api_key: str) -> bool:
        """Check if a key is near its daily limit (past warning threshold)."""
        used = self.get_usage_today(api_key)
        threshold = self.limits.DAILY_LIMIT_PER_KEY * self.limits.WARNING_THRESHOLD
        return used >= threshold

    def get_least_used_key(self, api_keys: List[str]) -> Optional[str]:
        """
        Get the API key with the least usage today.

        Args:
            api_keys: List of API keys to choose from

        Returns:
            The key with lowest usage, or None if all exhausted
        """
        if not api_keys:
            return None

        best_key = None
        min_usage = float('inf')

        for key in api_keys:
            usage = self.get_usage_today(key)

            # Skip exhausted keys
            if usage >= self.limits.DAILY_LIMIT_PER_KEY:
                continue

            if usage < min_usage:
                min_usage = usage
                best_key = key

        if best_key:
            key_id = self._get_key_id(best_key)
            self.logger.debug(
                f"Selected key ...{key_id} with {min_usage} requests today"
            )

        return best_key

    def reserve_and_get_key(self, api_keys: List[str]) -> Optional[str]:
        """
        Atomically reserve and return the best available API key.

        This is the RECOMMENDED method for parallel/batch operations.
        It ensures each thread gets a different key by:
        1. Locking the reservation mutex
        2. Finding the least-used key that isn't currently reserved
        3. Reserving it before releasing the lock

        Args:
            api_keys: List of API keys to choose from

        Returns:
            Reserved API key, or None if no keys available

        Note:
            MUST call release_key() after the request is complete!
        """
        with self._reservation_lock:
            if not api_keys:
                return None

            best_key = None
            min_usage = float('inf')

            for key in api_keys:
                # Skip keys already reserved by other threads
                if key in self._reserved_keys:
                    continue

                usage = self.get_usage_today(key)

                # Also consider in-flight requests not yet recorded
                in_flight = self._key_usage_counts.get(key, 0)
                effective_usage = usage + in_flight

                # Skip exhausted keys
                if effective_usage >= self.limits.DAILY_LIMIT_PER_KEY:
                    continue

                if effective_usage < min_usage:
                    min_usage = effective_usage
                    best_key = key

            if best_key:
                # Reserve the key
                self._reserved_keys.add(best_key)
                self._key_usage_counts[best_key] = self._key_usage_counts.get(best_key, 0) + 1

                key_id = self._get_key_id(best_key)
                self.logger.info(
                    f"Reserved key ...{key_id} "
                    f"(effective usage: {min_usage}, reserved keys: {len(self._reserved_keys)})"
                )
            else:
                self.logger.warning(
                    f"No available keys! All {len(api_keys)} keys are either reserved or exhausted."
                )

            return best_key

    def release_key(self, api_key: str):
        """
        Release a previously reserved API key.

        Must be called after reserve_and_get_key() when the request is complete.

        Args:
            api_key: The API key to release
        """
        with self._reservation_lock:
            if api_key in self._reserved_keys:
                self._reserved_keys.discard(api_key)

                # Decrement in-flight count
                if api_key in self._key_usage_counts:
                    self._key_usage_counts[api_key] -= 1
                    if self._key_usage_counts[api_key] <= 0:
                        del self._key_usage_counts[api_key]

                key_id = self._get_key_id(api_key)
                self.logger.debug(
                    f"Released key ...{key_id} "
                    f"(remaining reserved: {len(self._reserved_keys)})"
                )

    def get_reserved_count(self) -> int:
        """Get the number of currently reserved keys."""
        with self._reservation_lock:
            return len(self._reserved_keys)

    def get_available_keys(self, api_keys: List[str]) -> List[str]:
        """Get list of keys that haven't hit daily limit."""
        return [
            key for key in api_keys
            if self.can_make_request(key)
        ]

    def get_all_usage_stats(self, api_keys: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Get comprehensive usage statistics for all keys.

        Returns:
            Dictionary with usage stats per key (keyed by masked key_id)
        """
        stats = {}
        today = self._get_today()

        for key in api_keys:
            data = self._load_usage_data(key)
            key_id = self._get_key_id(key)

            today_usage = data.daily_usage.get(today, DailyUsage(date=today))

            stats[f"...{key_id}"] = {
                'key_id': key_id,
                'used_today': today_usage.request_count,
                'remaining_today': max(0, self.limits.DAILY_LIMIT_PER_KEY - today_usage.request_count),
                'daily_limit': self.limits.DAILY_LIMIT_PER_KEY,
                'percentage_used': round(
                    (today_usage.request_count / self.limits.DAILY_LIMIT_PER_KEY) * 100, 1
                ),
                'errors_today': today_usage.errors,
                'total_requests': data.total_requests,
                'total_errors': data.total_errors,
                'last_used': data.last_used_at,
                'created': data.created_at,
                'can_make_request': today_usage.request_count < self.limits.DAILY_LIMIT_PER_KEY,
                'near_limit': today_usage.request_count >= (self.limits.DAILY_LIMIT_PER_KEY * self.limits.WARNING_THRESHOLD),
            }

        return stats

    def get_usage_history(self, api_key: str, days: int = 30) -> List[Dict[str, Any]]:
        """
        Get usage history for a key.

        Args:
            api_key: The API key
            days: Number of days to look back

        Returns:
            List of daily usage records
        """
        data = self._load_usage_data(api_key)
        history = []

        # Get date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        current = start_date
        while current <= end_date:
            date_str = current.strftime('%Y-%m-%d')
            if date_str in data.daily_usage:
                daily = data.daily_usage[date_str]
                history.append({
                    'date': date_str,
                    'request_count': daily.request_count,
                    'errors': daily.errors,
                })
            else:
                history.append({
                    'date': date_str,
                    'request_count': 0,
                    'errors': 0,
                })
            current += timedelta(days=1)

        return history

    def get_total_usage_today(self, api_keys: List[str]) -> int:
        """Get total API calls today across all keys."""
        return sum(self.get_usage_today(key) for key in api_keys)

    def get_total_remaining_today(self, api_keys: List[str]) -> int:
        """Get total remaining requests today across all keys."""
        return sum(self.get_remaining_today(key) for key in api_keys)

    def cleanup_old_data(self, days_to_keep: int = 90):
        """
        Clean up usage data older than specified days.

        Args:
            days_to_keep: Number of days of history to retain
        """
        cutoff = (datetime.now() - timedelta(days=days_to_keep)).strftime('%Y-%m-%d')

        for usage_file in self.usage_dir.glob("usage_*.json"):
            try:
                with open(usage_file, 'r+') as f:
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                    try:
                        data = KeyUsageData.from_dict(json.load(f))

                        # Remove old daily usage entries
                        dates_to_remove = [
                            date for date in data.daily_usage.keys()
                            if date < cutoff
                        ]

                        for date in dates_to_remove:
                            del data.daily_usage[date]

                        # Write back
                        f.seek(0)
                        f.truncate()
                        json.dump(data.to_dict(), f, indent=2)

                    finally:
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)

                self.logger.debug(f"Cleaned up old data from {usage_file}")

            except Exception as e:
                self.logger.warning(f"Failed to clean up {usage_file}: {e}")

    def reset_key_usage(self, api_key: str):
        """Reset all usage data for a specific key."""
        usage_file = self._get_usage_file(api_key)
        if usage_file.exists():
            usage_file.unlink()
            self.logger.info(f"Reset usage for key ...{self._get_key_id(api_key)}")

    def reset_all_usage(self):
        """Reset all usage data (delete all usage files)."""
        for usage_file in self.usage_dir.glob("usage_*.json"):
            usage_file.unlink()
        self.logger.info("Reset all API usage data")


# Singleton instance with thread-safe initialization
_tracker_instance: Optional[APIUsageTracker] = None
_tracker_lock = threading.Lock()


def get_usage_tracker() -> APIUsageTracker:
    """
    Get or create the global usage tracker instance.

    Thread-safe singleton pattern using double-checked locking.
    """
    global _tracker_instance
    # First check without lock (fast path)
    if _tracker_instance is None:
        with _tracker_lock:
            # Second check with lock (thread-safe)
            if _tracker_instance is None:
                _tracker_instance = APIUsageTracker()
    return _tracker_instance


def reset_tracker():
    """Reset the global tracker instance (mainly for testing)."""
    global _tracker_instance
    with _tracker_lock:
        _tracker_instance = None

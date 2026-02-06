#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Global SEC API rate limiter for cross-process coordination.

Ensures compliance with SEC EDGAR rate limits (10 requests/second)
across multiple parallel workers by using file-based locking.
"""

import time
import threading
import portalocker
from pathlib import Path
from datetime import datetime
from typing import Optional

from fintel.core import get_logger, get_config


class SECRateLimiter:
    """
    Global rate limiter for SEC EDGAR API requests.

    SEC EDGAR has a rate limit of 10 requests per second. With 25 parallel
    workers, we need global coordination to avoid hitting this limit.

    Uses file-based locking for cross-process safety, similar to the
    Gemini request queue approach.

    Features:
    - Configurable requests per second (default: 8, leaving buffer)
    - File-based locking for cross-process coordination
    - Thread-safe within a process
    - Automatic request spacing

    Usage:
        limiter = SECRateLimiter()

        # Before making SEC request:
        limiter.acquire()  # Blocks until request is allowed
        try:
            # Make SEC request
            response = requests.get(sec_url)
        finally:
            limiter.release()  # Record request completion

        # Or use context manager:
        with limiter:
            response = requests.get(sec_url)
    """

    # SEC allows 10 req/sec, we use 8 to leave buffer
    DEFAULT_REQUESTS_PER_SECOND = 8
    MIN_INTERVAL_SECONDS = 1.0 / DEFAULT_REQUESTS_PER_SECOND  # 0.125 seconds

    def __init__(
        self,
        requests_per_second: int = DEFAULT_REQUESTS_PER_SECOND,
        lock_dir: Optional[Path] = None
    ):
        """
        Initialize SEC rate limiter.

        Args:
            requests_per_second: Maximum requests per second (default: 8)
            lock_dir: Directory for lock file (default: data/api_usage/)
        """
        self.logger = get_logger(f"{__name__}.SECRateLimiter")
        self.requests_per_second = requests_per_second
        self.min_interval = 1.0 / requests_per_second

        # Determine lock directory
        if lock_dir:
            self._lock_dir = Path(lock_dir)
        else:
            config = get_config()
            self._lock_dir = config.data_dir / "api_usage"

        self._lock_dir.mkdir(parents=True, exist_ok=True)
        self._lock_file = self._lock_dir / "sec_request.lock"
        self._timestamp_file = self._lock_dir / "sec_last_request.txt"

        # Thread lock for within-process coordination
        self._thread_lock = threading.Lock()

        # Ensure lock file exists
        self._lock_file.touch(exist_ok=True)

        self.logger.info(
            f"SECRateLimiter initialized "
            f"(max {requests_per_second} req/sec, interval {self.min_interval:.3f}s)"
        )

    def acquire(self, timeout: float = 30.0) -> bool:
        """
        Acquire permission to make a SEC request.

        Blocks until it's safe to make a request according to rate limits.
        Uses both thread-local lock and file-based lock for coordination.

        Args:
            timeout: Maximum seconds to wait (default: 30)

        Returns:
            True if acquired, False if timeout
        """
        start_time = time.time()

        while True:
            # Check timeout
            elapsed = time.time() - start_time
            if elapsed >= timeout:
                self.logger.warning(f"SEC rate limiter timeout after {timeout}s")
                return False

            try:
                with open(self._lock_file, 'r+') as f:
                    # Acquire exclusive lock
                    portalocker.lock(f, portalocker.LOCK_EX | portalocker.LOCK_NB)

                    try:
                        # Check last request time
                        last_request = self._read_last_request_time()
                        now = time.time()

                        if last_request:
                            time_since_last = now - last_request
                            if time_since_last < self.min_interval:
                                # Need to wait
                                wait_time = self.min_interval - time_since_last
                                portalocker.unlock(f)
                                time.sleep(wait_time)
                                continue

                        # Update last request time
                        self._write_last_request_time(now)
                        return True

                    finally:
                        portalocker.unlock(f)

            except portalocker.LockException:
                # Lock held by another process, wait briefly
                time.sleep(0.01)
                continue

            except Exception as e:
                self.logger.error(f"SEC rate limiter error: {e}")
                # Fall through and allow request to avoid blocking
                return True

    def release(self):
        """
        Release the rate limiter (no-op for this implementation).

        The timing is handled in acquire(), so release is a no-op.
        Kept for API consistency with context manager usage.
        """
        pass

    def __enter__(self):
        """Context manager entry."""
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.release()
        return False

    def _read_last_request_time(self) -> Optional[float]:
        """Read last request timestamp from file."""
        try:
            if self._timestamp_file.exists():
                content = self._timestamp_file.read_text().strip()
                if content:
                    return float(content)
        except (ValueError, IOError):
            pass
        return None

    def _write_last_request_time(self, timestamp: float):
        """Write last request timestamp to file."""
        try:
            self._timestamp_file.write_text(str(timestamp))
        except IOError as e:
            self.logger.warning(f"Failed to write SEC timestamp: {e}")

    def wait_if_needed(self):
        """
        Wait if needed to comply with rate limit.

        Convenience method that acquires and immediately releases.
        Use this before making SEC requests.
        """
        self.acquire()
        self.release()


# Singleton instance
_sec_limiter_instance: Optional[SECRateLimiter] = None
_sec_limiter_lock = threading.Lock()


def get_sec_rate_limiter() -> SECRateLimiter:
    """
    Get or create the global SEC rate limiter instance.

    Thread-safe singleton pattern.
    """
    global _sec_limiter_instance
    if _sec_limiter_instance is None:
        with _sec_limiter_lock:
            if _sec_limiter_instance is None:
                _sec_limiter_instance = SECRateLimiter()
    return _sec_limiter_instance


def reset_sec_limiter():
    """Reset the global limiter instance (mainly for testing)."""
    global _sec_limiter_instance
    with _sec_limiter_lock:
        _sec_limiter_instance = None

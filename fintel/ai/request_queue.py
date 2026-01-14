#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Request queue for Gemini API calls with per-key parallelization.

This module manages API request concurrency using:
1. Per-key file locks - Ensures same key isn't used concurrently
2. Global semaphore - Limits total concurrent requests across all keys

This allows multiple API keys to make requests in parallel while:
- Preventing the same key from concurrent use (rate limit protection)
- Limiting overall concurrency to avoid overwhelming the API
- Maintaining mandatory sleep between requests on each key

Uses file-based locking (fcntl) for process-safe coordination across:
- Single-threaded CLI
- Multi-threaded UI
- Multi-process batch processing
- Mixed CLI + UI execution
"""

import fcntl
import hashlib
import time
import threading
from pathlib import Path
from typing import Optional, Callable, Any, Dict

from fintel.core import get_logger
from fintel.ai.api_config import get_api_limits


class GeminiRequestQueue:
    """
    Manages Gemini API request concurrency with per-key locking.

    Uses two levels of concurrency control:
    1. Global semaphore - Limits total concurrent requests (MAX_CONCURRENT_REQUESTS)
    2. Per-key file locks - Prevents same key from concurrent use

    This allows N keys to run N parallel requests (up to semaphore limit),
    while ensuring each individual key respects rate limits.

    File-based locking works across:
    - Multiple threads in same process
    - Multiple processes (CLI batch mode)
    - Different Python scripts running simultaneously

    Lock files are created in data/api_usage/gemini_request_{key_hash}.lock

    Usage:
        queue = get_gemini_request_queue()
        result = queue.execute_with_lock(
            request_func=api_call,
            api_key="key_xyz",
            *args,
            **kwargs
        )
    """

    def __init__(
        self,
        lock_dir: Optional[Path] = None,
        sleep_duration: Optional[int] = None,
        max_concurrent: Optional[int] = None
    ):
        """
        Initialize the request queue with per-key locking.

        Args:
            lock_dir: Directory for lock files (default: data/api_usage/)
            sleep_duration: Seconds to sleep after each request (default from config)
            max_concurrent: Max concurrent requests (default from config)
        """
        limits = get_api_limits()

        if lock_dir is None:
            lock_dir = Path(limits.USAGE_DATA_DIR)

        self.lock_dir = lock_dir
        self._sleep_duration = sleep_duration or limits.SLEEP_AFTER_REQUEST
        self._max_concurrent = max_concurrent or limits.MAX_CONCURRENT_REQUESTS

        # Global semaphore to limit total concurrent requests
        self._semaphore = threading.BoundedSemaphore(self._max_concurrent)

        # Track per-key statistics
        self._key_stats: Dict[str, Dict[str, Any]] = {}
        self._stats_lock = threading.Lock()

        # Overall statistics
        self._total_requests = 0
        self._total_wait_time = 0.0

        # Ensure lock directory exists
        self.lock_dir.mkdir(parents=True, exist_ok=True)

        self.logger = get_logger(f"{__name__}.GeminiRequestQueue")
        self.logger.info(
            f"Initialized GeminiRequestQueue with per-key locking in {lock_dir}"
        )
        self.logger.info(f"Max concurrent requests: {self._max_concurrent}")
        self.logger.info(f"Sleep between requests (per key): {self._sleep_duration}s")

    def _get_key_hash(self, api_key: str) -> str:
        """Get a hash of the API key for lock file naming."""
        return hashlib.sha256(api_key[:16].encode()).hexdigest()[:16]

    def _get_lock_file_path(self, api_key: str) -> Path:
        """Get the lock file path for a specific API key."""
        key_hash = self._get_key_hash(api_key)
        return self.lock_dir / f"gemini_request_{key_hash}.lock"

    def execute_with_lock(
        self,
        request_func: Callable,
        api_key: str,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute an API request with per-key locking and global concurrency limit.

        This method:
        1. Acquires a slot from the global semaphore (limits total concurrency)
        2. Opens/creates the per-key lock file
        3. Acquires exclusive lock for this key (blocks if key in use)
        4. Executes the request function
        5. Records metrics
        6. Sleeps for mandatory duration (per-key, doesn't block other keys)
        7. Releases the per-key lock
        8. Releases the semaphore slot

        Process-safe: Works across separate Python processes
        Thread-safe: Works across threads in same process

        Args:
            request_func: The function to call (the actual Gemini API call)
            api_key: The API key being used
            *args: Positional arguments to pass to request_func
            **kwargs: Keyword arguments to pass to request_func

        Returns:
            The return value from request_func

        Raises:
            Any exception raised by request_func (after mandatory sleep)
        """
        key_suffix = api_key[-4:] if len(api_key) >= 4 else "****"
        key_hash = self._get_key_hash(api_key)
        lock_file_path = self._get_lock_file_path(api_key)

        # Ensure lock file exists
        lock_file_path.touch(exist_ok=True)

        wait_start = time.time()

        self.logger.debug(
            f"Acquiring semaphore slot for key ...{key_suffix} "
            f"(max concurrent: {self._max_concurrent})"
        )

        # Step 1: Acquire semaphore slot (limits total concurrency)
        self._semaphore.acquire()
        semaphore_acquired = True

        try:
            semaphore_wait = time.time() - wait_start
            self.logger.debug(
                f"Semaphore acquired for key ...{key_suffix} "
                f"(waited {semaphore_wait:.2f}s)"
            )

            # Step 2: Acquire per-key lock
            self.logger.debug(f"Acquiring per-key lock for ...{key_suffix}")

            with open(lock_file_path, 'a+') as lock_file:
                try:
                    # Acquire exclusive lock for this specific key
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)

                    lock_wait = time.time() - wait_start
                    self.logger.debug(
                        f"Per-key lock acquired for ...{key_suffix} "
                        f"(total wait {lock_wait:.2f}s)"
                    )

                    try:
                        # Execute the actual API request
                        request_start = time.time()
                        result = request_func(*args, **kwargs)
                        request_duration = time.time() - request_start

                        # Update statistics
                        self._update_stats(key_hash, key_suffix, request_duration, False)

                        self.logger.debug(
                            f"Request complete for key ...{key_suffix} "
                            f"({request_duration:.2f}s), sleeping {self._sleep_duration}s"
                        )

                        # Sleep per-key (doesn't block other keys)
                        time.sleep(self._sleep_duration)

                        return result

                    except Exception as e:
                        # Update statistics for failed request
                        self._update_stats(key_hash, key_suffix, 0, True)

                        self.logger.warning(
                            f"Request failed for key ...{key_suffix}: {e}, "
                            f"still sleeping {self._sleep_duration}s"
                        )

                        # Still sleep to avoid hammering API on errors
                        time.sleep(self._sleep_duration)
                        raise

                finally:
                    # Release per-key lock
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                    self.logger.debug(f"Released per-key lock for ...{key_suffix}")

        finally:
            # Always release semaphore
            if semaphore_acquired:
                self._semaphore.release()
                self.logger.debug(f"Released semaphore slot for key ...{key_suffix}")

    def _update_stats(
        self,
        key_hash: str,
        key_suffix: str,
        duration: float,
        is_error: bool
    ):
        """Update per-key and global statistics."""
        with self._stats_lock:
            self._total_requests += 1

            if key_hash not in self._key_stats:
                self._key_stats[key_hash] = {
                    'key_suffix': key_suffix,
                    'request_count': 0,
                    'error_count': 0,
                    'total_duration': 0.0,
                    'last_request_time': None
                }

            stats = self._key_stats[key_hash]
            stats['request_count'] += 1
            stats['total_duration'] += duration
            stats['last_request_time'] = time.time()

            if is_error:
                stats['error_count'] += 1

    def set_sleep_duration(self, seconds: int):
        """
        Update the mandatory sleep duration between requests.

        Args:
            seconds: Seconds to sleep between requests
        """
        self._sleep_duration = seconds
        self.logger.info(f"Updated sleep duration to {seconds}s")

    def set_max_concurrent(self, max_concurrent: int):
        """
        Update the maximum concurrent requests.

        Note: This creates a new semaphore, existing requests continue
        with the old limit until they complete.

        Args:
            max_concurrent: Maximum concurrent requests allowed
        """
        self._max_concurrent = max_concurrent
        self._semaphore = threading.BoundedSemaphore(max_concurrent)
        self.logger.info(f"Updated max concurrent requests to {max_concurrent}")

    def get_stats(self) -> dict:
        """
        Get queue statistics.

        Returns:
            Dictionary with queue statistics including per-key breakdown
        """
        with self._stats_lock:
            return {
                'total_requests': self._total_requests,
                'sleep_duration': self._sleep_duration,
                'max_concurrent': self._max_concurrent,
                'lock_dir': str(self.lock_dir),
                'per_key_stats': dict(self._key_stats),
            }


# Global singleton instance with thread-safe initialization
_global_queue: Optional[GeminiRequestQueue] = None
_queue_creation_lock = threading.Lock()


def get_gemini_request_queue() -> GeminiRequestQueue:
    """
    Get the global Gemini request queue singleton.

    Thread-safe singleton pattern using double-checked locking.
    Returns the same instance regardless of how many processes/threads call this.

    Returns:
        The global GeminiRequestQueue instance
    """
    global _global_queue

    # First check without lock (fast path)
    if _global_queue is None:
        with _queue_creation_lock:
            # Second check with lock (thread-safe)
            if _global_queue is None:
                _global_queue = GeminiRequestQueue()

    return _global_queue


def reset_gemini_request_queue():
    """
    Reset the global request queue (mainly for testing).

    Use with caution - this creates a new queue instance and resets metrics.
    """
    global _global_queue
    with _queue_creation_lock:
        _global_queue = None

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SEC EDGAR request queue with cross-process rate limiting.

Uses file-based locking (portalocker) for process-safe coordination across:
- Single-threaded CLI
- Multi-threaded UI
- Multi-process batch processing
- Mixed CLI + UI execution

SEC's fair access policy recommends no more than 10 requests per second.
This module provides configurable delays and concurrency limits to prevent
overwhelming SEC servers during batch processing with multiple workers.

Cross-platform compatible (Windows, macOS, Linux).
"""

import portalocker
import time
import threading
from pathlib import Path
from typing import Optional, Callable, Any

from fintel.core import get_logger
from fintel.ai.api_config import get_sec_limits


class SECRequestQueue:
    """
    Manages SEC EDGAR request rate limiting with cross-process safety.

    Uses two levels of concurrency control:
    1. Global semaphore - Limits total concurrent SEC requests
    2. Single file lock - Ensures sequential access to SEC API

    Unlike the Gemini queue (which uses per-key locks), SEC uses a single
    global lock since it's a public API without API keys. This ensures
    all workers across all processes respect the configured delay.

    File-based locking works across:
    - Multiple threads in same process
    - Multiple processes (CLI batch mode)
    - Different Python scripts running simultaneously

    Lock file is created at: data/api_usage/sec_edgar_request.lock

    Usage:
        queue = get_sec_request_queue()
        result = queue.execute_with_lock(
            request_func=download_func,
            *args,
            **kwargs
        )
    """

    def __init__(
        self,
        lock_dir: Optional[Path] = None,
        request_delay: Optional[float] = None,
        max_concurrent: Optional[int] = None
    ):
        """
        Initialize SEC request queue with rate limiting.

        Args:
            lock_dir: Directory for lock files (default: data/api_usage/)
            request_delay: Seconds to wait after each request (default from config)
            max_concurrent: Max concurrent requests (default from config)
        """
        limits = get_sec_limits()

        if lock_dir is None:
            lock_dir = Path(limits.LOCK_DIR)

        self.lock_dir = lock_dir
        self._request_delay = request_delay if request_delay is not None else limits.REQUEST_DELAY
        self._max_concurrent = max_concurrent if max_concurrent is not None else limits.MAX_CONCURRENT_REQUESTS

        # Global semaphore for concurrency control
        self._semaphore = threading.BoundedSemaphore(self._max_concurrent)

        # Single lock file for all SEC requests (simpler than per-key like Gemini)
        self._lock_file_path = self.lock_dir / "sec_edgar_request.lock"

        # Statistics tracking
        self._stats_lock = threading.Lock()
        self._total_requests = 0
        self._total_errors = 0
        self._total_wait_time = 0.0
        self._last_request_time = 0.0

        # Ensure lock directory exists
        self.lock_dir.mkdir(parents=True, exist_ok=True)

        self.logger = get_logger(f"{__name__}.SECRequestQueue")
        self.logger.info(
            f"Initialized SECRequestQueue: max_concurrent={self._max_concurrent}, "
            f"request_delay={self._request_delay}s, lock_dir={self.lock_dir}"
        )

    def execute_with_lock(
        self,
        request_func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute a SEC request with rate limiting and concurrency control.

        This method:
        1. Acquires a slot from the global semaphore (limits total concurrency)
        2. Acquires the cross-process file lock (ensures sequential SEC access)
        3. Executes the request function
        4. Records timing and updates stats
        5. Sleeps for configured delay (mandatory)
        6. Releases locks

        Process-safe: Works across separate Python processes
        Thread-safe: Works across threads in same process

        Args:
            request_func: The function to call (SEC API request)
            *args: Positional arguments for request_func
            **kwargs: Keyword arguments for request_func

        Returns:
            The return value from request_func

        Raises:
            Any exception raised by request_func (after mandatory delay)
        """
        wait_start = time.time()

        self.logger.debug(
            f"Acquiring semaphore slot (max concurrent: {self._max_concurrent})"
        )

        # Step 1: Acquire semaphore slot
        self._semaphore.acquire()
        semaphore_acquired = True

        try:
            semaphore_wait = time.time() - wait_start
            self.logger.debug(f"Semaphore acquired (waited {semaphore_wait:.2f}s)")

            # Ensure lock file exists
            self._lock_file_path.touch(exist_ok=True)

            # Step 2: Acquire file lock for cross-process coordination
            self.logger.debug("Acquiring SEC global file lock")

            with open(self._lock_file_path, 'a+') as lock_file:
                try:
                    # Acquire exclusive lock (blocks if another process holds it) - cross-platform
                    portalocker.lock(lock_file, portalocker.LOCK_EX)

                    lock_wait = time.time() - wait_start
                    self.logger.debug(f"File lock acquired (total wait {lock_wait:.2f}s)")

                    try:
                        # Step 3: Execute the request
                        request_start = time.time()
                        result = request_func(*args, **kwargs)
                        request_duration = time.time() - request_start

                        # Update statistics
                        self._update_stats(request_duration, is_error=False)

                        self.logger.debug(
                            f"SEC request complete ({request_duration:.2f}s), "
                            f"sleeping {self._request_delay}s"
                        )

                        # Step 4: Mandatory delay after request
                        time.sleep(self._request_delay)

                        return result

                    except Exception as e:
                        # Update stats for failed request
                        self._update_stats(0, is_error=True)

                        self.logger.warning(
                            f"SEC request failed: {e}, still sleeping {self._request_delay}s"
                        )

                        # Still sleep to avoid hammering SEC on errors
                        time.sleep(self._request_delay)
                        raise

                finally:
                    # Release file lock (cross-platform)
                    portalocker.unlock(lock_file)
                    self.logger.debug("Released SEC file lock")

        finally:
            # Always release semaphore
            if semaphore_acquired:
                self._semaphore.release()
                self.logger.debug("Released semaphore slot")

    def _update_stats(self, duration: float, is_error: bool):
        """Update request statistics."""
        with self._stats_lock:
            self._total_requests += 1
            self._last_request_time = time.time()
            if is_error:
                self._total_errors += 1

    def set_request_delay(self, seconds: float):
        """
        Update the delay between SEC requests.

        Args:
            seconds: Seconds to wait after each request
        """
        self._request_delay = seconds
        self.logger.info(f"Updated SEC request delay to {seconds}s")

    def set_max_concurrent(self, max_concurrent: int):
        """
        Update maximum concurrent SEC requests.

        Note: Creates a new semaphore. Existing requests continue
        with the old limit until they complete.

        Args:
            max_concurrent: Maximum concurrent requests allowed
        """
        self._max_concurrent = max_concurrent
        self._semaphore = threading.BoundedSemaphore(max_concurrent)
        self.logger.info(f"Updated SEC max concurrent to {max_concurrent}")

    def get_stats(self) -> dict:
        """
        Get queue statistics.

        Returns:
            Dictionary with queue statistics
        """
        with self._stats_lock:
            return {
                'total_requests': self._total_requests,
                'total_errors': self._total_errors,
                'request_delay': self._request_delay,
                'max_concurrent': self._max_concurrent,
                'lock_dir': str(self.lock_dir),
                'last_request_time': self._last_request_time,
            }


# Global singleton with thread-safe initialization
_global_queue: Optional[SECRequestQueue] = None
_queue_creation_lock = threading.Lock()


def get_sec_request_queue() -> SECRequestQueue:
    """
    Get the global SEC request queue singleton.

    Thread-safe singleton pattern using double-checked locking.

    Returns:
        The global SECRequestQueue instance
    """
    global _global_queue

    # First check without lock (fast path)
    if _global_queue is None:
        with _queue_creation_lock:
            # Second check with lock (thread-safe)
            if _global_queue is None:
                _global_queue = SECRequestQueue()

    return _global_queue


def reset_sec_request_queue():
    """
    Reset the global SEC queue (mainly for testing).

    Use with caution - creates a new queue instance and resets metrics.
    """
    global _global_queue
    with _queue_creation_lock:
        _global_queue = None

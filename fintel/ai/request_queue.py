#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Global request queue for serializing Gemini API calls.

This module ensures that only one API request to Gemini is in-flight at a time,
preventing concurrent requests from exceeding rate limits when running multiple
analyses in parallel.

Uses file-based locking (fcntl) to serialize requests across ALL execution modes:
- Single-threaded CLI
- Multi-threaded UI
- Multi-process batch processing
- Mixed CLI + UI execution

This works across processes (unlike threading.Lock) because it uses the filesystem.
"""

import fcntl
import time
import threading
from pathlib import Path
from typing import Optional, Callable, Any

from fintel.core import get_logger


class GeminiRequestQueue:
    """
    Serializes all Gemini API requests globally using file-based locking.

    Ensures that parallel analyses don't overwhelm the Gemini API by forcing all
    requests through a single lock with mandatory sleep between requests.

    File-based locking works across:
    - Multiple threads in same process
    - Multiple processes (CLI batch mode)
    - Different Python scripts running simultaneously

    The lock file is created in data/api_usage/gemini_request.lock and is shared
    by all instances of this queue across all processes/threads.

    Usage:
        queue = get_gemini_request_queue()
        result = queue.execute_with_lock(
            request_func=api_call,
            api_key="key_xyz",
            *args,
            **kwargs
        )
    """

    def __init__(self, lock_file_path: Optional[Path] = None, sleep_duration: int = 65):
        """
        Initialize the global request queue.

        Args:
            lock_file_path: Path to the lock file (default: data/api_usage/gemini_request.lock)
            sleep_duration: Seconds to sleep between requests (default: 65)
        """
        if lock_file_path is None:
            # Use same directory as usage tracker for consistency
            lock_file_path = Path("data/api_usage/gemini_request.lock")

        self.lock_file_path = lock_file_path
        self._sleep_duration = sleep_duration
        self._request_count = 0
        self._last_request_time = None

        # Ensure lock file directory exists
        self.lock_file_path.parent.mkdir(parents=True, exist_ok=True)

        # Create lock file if it doesn't exist
        self.lock_file_path.touch(exist_ok=True)

        self.logger = get_logger(f"{__name__}.GeminiRequestQueue")
        self.logger.info(
            f"Initialized GeminiRequestQueue with file-based lock at {lock_file_path}"
        )
        self.logger.info(f"Mandatory sleep between requests: {sleep_duration}s")

    def execute_with_lock(
        self,
        request_func: Callable,
        api_key: str,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute an API request with global serialization lock (file-based).

        This method:
        1. Opens the lock file
        2. Acquires exclusive lock (fcntl.LOCK_EX) - blocks until available
        3. Executes the request function
        4. Records request time and metrics
        5. Sleeps for mandatory duration
        6. Releases the lock
        7. Closes the file

        Process-safe: Works across separate Python processes (CLI batch mode)
        Thread-safe: Works across threads in same process (UI batch mode)

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

        self.logger.debug(f"Waiting for file-based lock (key ...{key_suffix})")

        # Open lock file for exclusive locking
        with open(self.lock_file_path, 'a+') as lock_file:
            try:
                # Acquire exclusive lock
                # This blocks until the lock is available, works across processes
                self.logger.debug(f"Acquiring exclusive lock for key ...{key_suffix}")
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
                self.logger.debug(f"Lock acquired, executing request with key ...{key_suffix}")

                try:
                    # Execute the actual Gemini API request
                    result = request_func(*args, **kwargs)

                    # Record metrics
                    self._request_count += 1
                    self._last_request_time = time.time()

                    # Sleep after successful request
                    self.logger.debug(
                        f"Request #{self._request_count} complete, "
                        f"sleeping {self._sleep_duration}s before next request"
                    )
                    time.sleep(self._sleep_duration)

                    return result

                except Exception as e:
                    # Record metrics even for failed requests
                    self._request_count += 1
                    self._last_request_time = time.time()

                    self.logger.warning(
                        f"Request #{self._request_count} failed: {e}, "
                        f"still sleeping {self._sleep_duration}s to avoid hammering API"
                    )

                    # Still sleep after failed requests to avoid API exhaustion
                    time.sleep(self._sleep_duration)
                    raise

            finally:
                # Release lock explicitly (also happens when context manager exits)
                self.logger.debug(f"Releasing lock for key ...{key_suffix}")
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    def set_sleep_duration(self, seconds: int):
        """
        Update the mandatory sleep duration between requests.

        Args:
            seconds: Seconds to sleep between requests
        """
        self._sleep_duration = seconds
        self.logger.info(f"Updated sleep duration to {seconds}s")

    def get_stats(self) -> dict:
        """
        Get queue statistics.

        Returns:
            Dictionary with queue statistics
        """
        return {
            'total_requests': self._request_count,
            'sleep_duration': self._sleep_duration,
            'last_request_time': self._last_request_time,
            'lock_file_path': str(self.lock_file_path),
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

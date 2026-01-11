#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Cancellation token system for graceful analysis termination.

Provides thread-safe cancellation mechanism for long-running analyses
with support for cooperative cancellation checks.
"""

import threading
from typing import Dict, Set, Optional
from datetime import datetime

from fintel.core import get_logger


class AnalysisCancelledException(Exception):
    """Raised when an analysis is cancelled by user request."""

    def __init__(self, run_id: str):
        self.run_id = run_id
        super().__init__(f"Analysis {run_id} was cancelled by user")


class CancellationToken:
    """
    Thread-safe cancellation token for a single analysis run.

    Usage:
        token = CancellationToken(run_id)

        # In the analysis loop:
        for item in items:
            token.raise_if_cancelled()  # Raises AnalysisCancelledException
            # ... process item ...

        # To cancel from another thread:
        token.cancel()
    """

    def __init__(self, run_id: str):
        self.run_id = run_id
        self._cancelled = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.created_at = datetime.utcnow()

    def cancel(self):
        """Signal cancellation. Thread-safe."""
        self._cancelled.set()

    def is_cancelled(self) -> bool:
        """Check if cancellation was requested. Thread-safe."""
        return self._cancelled.is_set()

    def raise_if_cancelled(self):
        """
        Raise AnalysisCancelledException if cancelled.

        Call this periodically in long-running loops to enable
        cooperative cancellation.
        """
        if self.is_cancelled():
            raise AnalysisCancelledException(self.run_id)

    def set_thread(self, thread: threading.Thread):
        """Associate a thread with this token."""
        self._thread = thread

    def get_thread(self) -> Optional[threading.Thread]:
        """Get the associated thread."""
        return self._thread


class CancellationRegistry:
    """
    Global registry for managing cancellation tokens across all runs.

    This is a thread-safe singleton that tracks all active analysis runs
    and provides the ability to cancel them.

    Usage:
        registry = get_cancellation_registry()

        # When starting an analysis:
        token = registry.create_token(run_id)
        token.set_thread(threading.current_thread())

        # When cancelling:
        success = registry.cancel_run(run_id, timeout=30.0)

        # When analysis completes:
        registry.cleanup_token(run_id)
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._tokens: Dict[str, CancellationToken] = {}
                    cls._instance._registry_lock = threading.Lock()
                    cls._instance.logger = get_logger(f"{__name__}.CancellationRegistry")
        return cls._instance

    def create_token(self, run_id: str) -> CancellationToken:
        """
        Create and register a new cancellation token.

        Args:
            run_id: Unique identifier for the analysis run

        Returns:
            CancellationToken for the run
        """
        with self._registry_lock:
            token = CancellationToken(run_id)
            self._tokens[run_id] = token
            self.logger.info(f"Created cancellation token for run {run_id}")
            return token

    def get_token(self, run_id: str) -> Optional[CancellationToken]:
        """
        Get token for a run.

        Args:
            run_id: Run identifier

        Returns:
            CancellationToken if exists, None otherwise
        """
        with self._registry_lock:
            return self._tokens.get(run_id)

    def cancel_run(self, run_id: str, timeout: float = 30.0) -> bool:
        """
        Cancel a running analysis.

        This method:
        1. Signals the cancellation token
        2. Waits for the associated thread to finish (with timeout)
        3. Returns success status

        Args:
            run_id: The run to cancel
            timeout: Seconds to wait for graceful termination

        Returns:
            True if the run was cancelled and thread terminated,
            False if token not found or thread didn't terminate in time
        """
        with self._registry_lock:
            token = self._tokens.get(run_id)

        if not token:
            self.logger.warning(f"No cancellation token found for run {run_id}")
            return False

        # Signal cancellation
        token.cancel()
        self.logger.info(f"Cancellation signaled for run {run_id}")

        # Wait for thread to finish
        thread = token.get_thread()
        if thread and thread.is_alive():
            self.logger.info(f"Waiting up to {timeout}s for thread to terminate...")
            thread.join(timeout=timeout)

            if thread.is_alive():
                self.logger.warning(
                    f"Thread for {run_id} did not terminate within {timeout}s. "
                    "The analysis may still be running but will stop at the next "
                    "cancellation check point."
                )
                return False

        self.logger.info(f"Run {run_id} cancelled successfully")
        return True

    def cleanup_token(self, run_id: str):
        """
        Remove token from registry.

        Call this when an analysis completes (successfully, failed, or cancelled)
        to free up resources.

        Args:
            run_id: Run identifier to cleanup
        """
        with self._registry_lock:
            if run_id in self._tokens:
                del self._tokens[run_id]
                self.logger.debug(f"Cleaned up cancellation token for run {run_id}")

    def get_active_runs(self) -> Set[str]:
        """
        Get set of run_ids with active cancellation tokens.

        Returns:
            Set of run_id strings
        """
        with self._registry_lock:
            return set(self._tokens.keys())

    def is_run_active(self, run_id: str) -> bool:
        """
        Check if a run has an active cancellation token.

        Args:
            run_id: Run identifier

        Returns:
            True if token exists
        """
        with self._registry_lock:
            return run_id in self._tokens


# Global instance
_registry: Optional[CancellationRegistry] = None


def get_cancellation_registry() -> CancellationRegistry:
    """
    Get the global cancellation registry.

    Returns:
        The singleton CancellationRegistry instance
    """
    global _registry
    if _registry is None:
        _registry = CancellationRegistry()
    return _registry

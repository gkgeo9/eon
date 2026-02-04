#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Progress tracking and resumption for batch processing.

Tracks which companies/filings have been processed and allows
resumption of interrupted batch jobs.

Thread-safe implementation using file locking for concurrent access.

Extracted patterns from 10K_automator/contrarian_evidence_based.py
"""

import json
import threading
import portalocker
from pathlib import Path
from typing import List, Set, Optional
from datetime import datetime

from fintel.core import get_logger


class ProgressTracker:
    """
    Tracks progress of batch processing with file-based persistence.

    Allows resumption of interrupted batch jobs by tracking completed items.

    Example:
        tracker = ProgressTracker(session_id="batch_2024_12_05")

        # Check if already processed
        if not tracker.is_completed("AAPL"):
            # Process...
            tracker.mark_completed("AAPL")

        # Get remaining items
        remaining = tracker.get_remaining(all_tickers)
    """

    def __init__(
        self,
        session_id: str,
        progress_dir: Path = None
    ):
        """
        Initialize progress tracker.

        Thread-safe implementation using file locking for concurrent access.

        Args:
            session_id: Unique identifier for this batch session
            progress_dir: Directory to store progress files (default: ./progress)
        """
        self.session_id = session_id
        self.progress_dir = progress_dir or Path("./progress")
        self.progress_dir.mkdir(parents=True, exist_ok=True)

        self.progress_file = self.progress_dir / f"progress_{session_id}.json"
        self.lock_file = self.progress_dir / f"progress_{session_id}.lock"

        # Thread lock for in-memory operations
        self._lock = threading.Lock()

        # In-memory cache of completed items
        self.completed: Set[str] = set()

        # Load existing progress
        self._load_progress()

        self.logger = get_logger(f"{__name__}.ProgressTracker")
        self.logger.info(
            f"Initialized progress tracker for session: {session_id} "
            f"({len(self.completed)} items already completed)"
        )

    def is_completed(self, item: str) -> bool:
        """
        Check if an item has been completed.

        Thread-safe check using in-memory lock.

        Args:
            item: Item identifier (e.g., ticker symbol)

        Returns:
            True if item was already processed
        """
        with self._lock:
            return item.upper() in self.completed

    def mark_completed(self, item: str):
        """
        Mark an item as completed.

        Thread-safe and process-safe using both in-memory lock and file lock.
        Uses atomic read-modify-write pattern to prevent race conditions.

        Args:
            item: Item identifier (e.g., ticker symbol)
        """
        item_upper = item.upper()

        # First check with in-memory lock (fast path)
        with self._lock:
            if item_upper in self.completed:
                return

        # Use file lock for cross-process safety
        self._atomic_mark_completed(item_upper)

    def _atomic_mark_completed(self, item_upper: str, max_retries: int = 5):
        """
        Atomically mark an item as completed using file locking.

        Args:
            item_upper: Uppercased item identifier
            max_retries: Maximum retry attempts for lock acquisition
        """
        # Ensure lock file exists
        self.lock_file.touch(exist_ok=True)

        for attempt in range(max_retries):
            try:
                with open(self.lock_file, 'r+') as lock_handle:
                    # Acquire exclusive lock
                    portalocker.lock(lock_handle, portalocker.LOCK_EX)

                    try:
                        # Re-read progress from file (another process may have updated it)
                        self._load_progress_unlocked()

                        # Check again if already completed
                        if item_upper in self.completed:
                            return

                        # Add to completed set
                        with self._lock:
                            self.completed.add(item_upper)

                        # Save progress while holding lock
                        self._save_progress_unlocked()

                        self.logger.debug(f"Marked {item_upper} as completed")
                        return

                    finally:
                        # Release lock
                        portalocker.unlock(lock_handle)

            except portalocker.LockException as e:
                if attempt < max_retries - 1:
                    import time
                    import random
                    wait_time = 0.1 * (2 ** attempt) * random.uniform(0.5, 1.5)
                    self.logger.warning(
                        f"Lock acquisition failed, retry {attempt + 1}/{max_retries} "
                        f"in {wait_time:.2f}s: {e}"
                    )
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"Failed to acquire lock after {max_retries} attempts")
                    # Fall back to non-atomic update
                    with self._lock:
                        self.completed.add(item_upper)
                    self._save_progress()
                    self.logger.warning(f"Marked {item_upper} with fallback (non-atomic)")

    def mark_failed(self, item: str, error: str = None):
        """
        Mark an item as failed (for logging/debugging).

        Args:
            item: Item identifier
            error: Optional error message
        """
        # For now, just log the failure
        # Future: Could track failed items separately
        error_msg = f": {error}" if error else ""
        self.logger.warning(f"Item {item.upper()} failed{error_msg}")

    def get_completed_count(self) -> int:
        """
        Get count of completed items.

        Thread-safe.

        Returns:
            Number of items completed
        """
        with self._lock:
            return len(self.completed)

    def get_remaining(self, all_items: List[str]) -> List[str]:
        """
        Get list of items that still need processing.

        Thread-safe.

        Args:
            all_items: Complete list of items to process

        Returns:
            List of items not yet completed
        """
        with self._lock:
            return [
                item for item in all_items
                if item.upper() not in self.completed
            ]

    def get_completed_list(self) -> List[str]:
        """
        Get list of completed items.

        Thread-safe.

        Returns:
            List of completed item identifiers
        """
        with self._lock:
            return sorted(list(self.completed))

    def reset(self):
        """Reset progress (clear all completed items). Thread-safe."""
        with self._lock:
            self.completed.clear()
        self._save_progress()
        self.logger.info(f"Reset progress for session {self.session_id}")

    def _load_progress(self):
        """Load progress from file. Thread-safe wrapper."""
        with self._lock:
            self._load_progress_unlocked()

    def _load_progress_unlocked(self):
        """Load progress from file. Not thread-safe - caller must hold lock."""
        if self.progress_file.exists():
            try:
                with open(self.progress_file, 'r') as f:
                    data = json.load(f)

                self.completed = set(data.get('completed', []))
                self.logger.debug(
                    f"Loaded {len(self.completed)} completed items from file"
                )

            except Exception as e:
                self.logger.warning(f"Failed to load progress file: {e}")
                self.completed = set()
        else:
            self.logger.debug("No existing progress file found")
            self.completed = set()

    def _save_progress(self):
        """Save progress to file. Thread-safe wrapper."""
        with self._lock:
            self._save_progress_unlocked()

    def _save_progress_unlocked(self):
        """Save progress to file. Not thread-safe - caller must hold lock."""
        try:
            data = {
                'session_id': self.session_id,
                'completed': sorted(list(self.completed)),
                'count': len(self.completed),
                'last_updated': datetime.now().isoformat()
            }

            # Write to temp file first, then rename for atomicity
            temp_file = self.progress_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(data, f, indent=2)

            # Atomic rename
            temp_file.replace(self.progress_file)

        except Exception as e:
            self.logger.error(f"Failed to save progress: {e}")

    def get_stats(self) -> dict:
        """
        Get progress statistics.

        Thread-safe.

        Returns:
            Dictionary with progress stats
        """
        with self._lock:
            return {
                'session_id': self.session_id,
                'completed_count': len(self.completed),
                'progress_file': str(self.progress_file),
                'lock_file': str(self.lock_file),
                'last_loaded': datetime.now().isoformat()
            }

    def __repr__(self) -> str:
        """String representation."""
        with self._lock:
            count = len(self.completed)
        return (
            f"ProgressTracker(session={self.session_id}, "
            f"completed={count})"
        )

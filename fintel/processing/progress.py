#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Progress tracking and resumption for batch processing.

Tracks which companies/filings have been processed and allows
resumption of interrupted batch jobs.

Extracted patterns from 10K_automator/contrarian_evidence_based.py
"""

import json
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

        Args:
            session_id: Unique identifier for this batch session
            progress_dir: Directory to store progress files (default: ./progress)
        """
        self.session_id = session_id
        self.progress_dir = progress_dir or Path("./progress")
        self.progress_dir.mkdir(parents=True, exist_ok=True)

        self.progress_file = self.progress_dir / f"progress_{session_id}.json"

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

        Args:
            item: Item identifier (e.g., ticker symbol)

        Returns:
            True if item was already processed
        """
        return item.upper() in self.completed

    def mark_completed(self, item: str):
        """
        Mark an item as completed.

        Args:
            item: Item identifier (e.g., ticker symbol)
        """
        item_upper = item.upper()
        if item_upper not in self.completed:
            self.completed.add(item_upper)
            self._save_progress()
            self.logger.debug(f"Marked {item_upper} as completed")

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

        Returns:
            Number of items completed
        """
        return len(self.completed)

    def get_remaining(self, all_items: List[str]) -> List[str]:
        """
        Get list of items that still need processing.

        Args:
            all_items: Complete list of items to process

        Returns:
            List of items not yet completed
        """
        return [
            item for item in all_items
            if item.upper() not in self.completed
        ]

    def get_completed_list(self) -> List[str]:
        """
        Get list of completed items.

        Returns:
            List of completed item identifiers
        """
        return sorted(list(self.completed))

    def reset(self):
        """Reset progress (clear all completed items)."""
        self.completed.clear()
        self._save_progress()
        self.logger.info(f"Reset progress for session {self.session_id}")

    def _load_progress(self):
        """Load progress from file."""
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
        """Save progress to file."""
        try:
            data = {
                'session_id': self.session_id,
                'completed': sorted(list(self.completed)),
                'count': len(self.completed),
                'last_updated': datetime.now().isoformat()
            }

            with open(self.progress_file, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            self.logger.error(f"Failed to save progress: {e}")

    def get_stats(self) -> dict:
        """
        Get progress statistics.

        Returns:
            Dictionary with progress stats
        """
        return {
            'session_id': self.session_id,
            'completed_count': len(self.completed),
            'progress_file': str(self.progress_file),
            'last_loaded': datetime.now().isoformat()
        }

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"ProgressTracker(session={self.session_id}, "
            f"completed={len(self.completed)})"
        )

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Batch queue system for large-scale multi-day analysis.

Handles:
- Distributing work across API keys
- Waiting for midnight PST rate limit reset
- Persistent progress tracking that survives crashes
- Auto-resume after rate limit reset
"""

import uuid
import json
import threading
import time
import os
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field

from fintel.core import get_logger, get_config
from fintel.ai import APIKeyManager, RateLimiter
from fintel.ui.database import DatabaseRepository
from fintel.ui.services.cancellation import AnalysisCancelledException


@dataclass
class BatchJobConfig:
    """Configuration for a batch job."""
    name: str
    tickers: List[str]
    analysis_type: str
    filing_type: str = "10-K"
    num_years: int = 5
    company_names: Optional[Dict[str, str]] = None
    custom_prompt: Optional[str] = None
    max_retries: int = 2
    priority: int = 0
    enable_synthesis: bool = False  # If True, create synthesis analysis after all tickers complete


class BatchQueueService:
    """
    Manages large batch analysis jobs that span multiple days.

    Features:
    - Creates batch jobs with progress tracking
    - Distributes work across available API keys
    - Automatically pauses when rate limits exhausted
    - Resumes at midnight PST when limits reset
    - Survives crashes with persistent state
    """

    def __init__(self, db: DatabaseRepository):
        self.db = db
        self.config = get_config()
        self.logger = get_logger(f"{__name__}.BatchQueueService")

        # Initialize components
        self.api_key_manager = APIKeyManager(self.config.google_api_keys)
        self.rate_limiter = RateLimiter()

        # Worker thread control
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()

        # Fix #4: Cleanup stale worker state from crashed processes
        self._cleanup_stale_worker()

        self.logger.info("BatchQueueService initialized")

    def _cleanup_stale_worker(self):
        """
        Detect and cleanup stale worker state from crashed processes.

        This prevents confusion when a previous worker crashed without proper cleanup.
        Checks if the recorded worker_pid is still running and cleans up if not.
        """
        try:
            query = """
                SELECT worker_pid, current_batch_id
                FROM queue_state
                WHERE id = 1 AND is_running = 1
            """
            row = self.db._execute_with_retry(query, fetch_one=True)

            if row and row['worker_pid']:
                old_pid = row['worker_pid']
                batch_id = row['current_batch_id']

                if not self._is_process_alive(old_pid):
                    self.logger.warning(
                        f"Detected stale worker PID {old_pid} from crashed process. Cleaning up..."
                    )

                    # Clear queue state
                    self._cleanup_worker(batch_id)

                    # Reset any 'running' items back to 'pending' for the stale batch
                    if batch_id:
                        query = """
                            UPDATE batch_items
                            SET status = 'pending'
                            WHERE batch_id = ? AND status = 'running'
                        """
                        self.db._execute_with_retry(query, (batch_id,))
                        self.logger.info(f"Reset running items to pending for batch {batch_id}")

                        # Mark batch as stopped if it was running
                        query = """
                            UPDATE batch_jobs
                            SET status = 'stopped', error_message = 'Worker process crashed - restart to continue'
                            WHERE batch_id = ? AND status IN ('running', 'waiting_reset')
                        """
                        self.db._execute_with_retry(query, (batch_id,))
        except Exception as e:
            self.logger.error(f"Error during stale worker cleanup: {e}")

    def _is_process_alive(self, pid: int) -> bool:
        """
        Check if a process with the given PID is still running.

        Args:
            pid: Process ID to check

        Returns:
            True if process is running, False otherwise
        """
        try:
            os.kill(pid, 0)  # Signal 0 just checks existence
            return True
        except OSError:
            return False

    def _reset_item_to_pending(self, item_id: int):
        """
        Reset a batch item back to pending status.

        Used when an item couldn't be processed (e.g., no API key available).
        """
        query = """
            UPDATE batch_items
            SET status = 'pending', started_at = NULL
            WHERE id = ?
        """
        self.db._execute_with_retry(query, (item_id,))

    def create_batch_job(self, config: BatchJobConfig) -> str:
        """
        Create a new batch job.

        Args:
            config: Batch job configuration

        Returns:
            batch_id for tracking
        """
        batch_id = str(uuid.uuid4())

        # Create batch job record
        query = """
            INSERT INTO batch_jobs
            (batch_id, name, total_tickers, analysis_type, filing_type, num_years, config_json, priority)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        self.db._execute_with_retry(query, (
            batch_id,
            config.name,
            len(config.tickers),
            config.analysis_type,
            config.filing_type,
            config.num_years,
            json.dumps({
                'custom_prompt': config.custom_prompt,
                'max_retries': config.max_retries
            }),
            config.priority
        ))

        # Create batch items
        for ticker in config.tickers:
            company_name = config.company_names.get(ticker) if config.company_names else None
            query = """
                INSERT INTO batch_items (batch_id, ticker, company_name)
                VALUES (?, ?, ?)
            """
            self.db._execute_with_retry(query, (batch_id, ticker.upper(), company_name))

        self.logger.info(f"Created batch job {batch_id} with {len(config.tickers)} tickers")
        return batch_id

    def start_batch_job(self, batch_id: str) -> bool:
        """
        Start processing a batch job.

        Args:
            batch_id: The batch to start

        Returns:
            True if started successfully
        """
        # Check if already running
        if self._worker_thread and self._worker_thread.is_alive():
            self.logger.warning("Worker thread already running")
            return False

        # Update job status
        query = """
            UPDATE batch_jobs
            SET status = 'running', started_at = ?, last_activity_at = ?
            WHERE batch_id = ?
        """
        now = datetime.utcnow().isoformat()
        self.db._execute_with_retry(query, (now, now, batch_id))

        # Update queue state
        query = """
            UPDATE queue_state
            SET is_running = 1, current_batch_id = ?, worker_pid = ?, updated_at = ?
            WHERE id = 1
        """
        self.db._execute_with_retry(query, (batch_id, os.getpid(), now))

        # Start worker thread
        self._stop_event.clear()
        self._pause_event.clear()
        self._worker_thread = threading.Thread(
            target=self._batch_worker,
            args=(batch_id,),
            daemon=True,
            name=f"BatchWorker-{batch_id[:8]}"
        )
        self._worker_thread.start()

        self.logger.info(f"Started batch job {batch_id}")
        return True

    def _batch_worker(self, batch_id: str):
        """
        Main worker loop for processing batch items IN PARALLEL.

        Uses a thread pool to process multiple items concurrently, with one
        thread per available API key. This provides up to Nx speedup where
        N = number of API keys.

        Fix #1: Pre-reserves API keys BEFORE spawning threads to prevent
        race conditions where threads fail to get keys.

        Handles:
        - Pre-reserving API keys before thread spawn (Fix #1)
        - Processing items in parallel (up to number of reserved keys)
        - Sleeping until midnight when all keys exhausted
        - Graceful stop/pause
        """
        # Import here to avoid circular imports
        from fintel.ui.services.analysis_service import AnalysisService

        try:
            while not self._stop_event.is_set():
                # Check for pause
                if self._pause_event.is_set():
                    self.logger.info("Batch worker paused")
                    time.sleep(5)
                    continue

                # Get available keys count for thread pool sizing
                available_keys = self.api_key_manager.get_available_keys()
                if not available_keys:
                    # All keys exhausted - wait for midnight reset
                    self._wait_for_reset(batch_id)
                    continue

                # Get batch of pending items (up to number of available keys)
                max_parallel = len(available_keys)
                pending_items = self._get_pending_items(batch_id, limit=max_parallel)

                if not pending_items:
                    # No more items - batch complete
                    self._complete_batch(batch_id)
                    break

                # Fix #1: PRE-RESERVE API keys before spawning threads
                # This prevents race conditions where threads fail to get keys
                items_with_keys = []
                reserved_keys = []

                for item in pending_items:
                    key = self.api_key_manager.reserve_key()
                    if key is None:
                        # No more keys available - reset this item to pending
                        self._reset_item_to_pending(item['id'])
                        self.logger.warning(
                            f"No API key available for {item['ticker']}, resetting to pending"
                        )
                        continue
                    reserved_keys.append(key)
                    items_with_keys.append((item, key))

                if not items_with_keys:
                    # All keys exhausted during reservation - wait for reset
                    self.logger.info("All API keys exhausted during reservation")
                    self._wait_for_reset(batch_id)
                    continue

                self.logger.info(
                    f"Processing {len(items_with_keys)} items in parallel "
                    f"(reserved {len(reserved_keys)} API keys)"
                )

                # Track which keys have been released by workers
                released_keys = set()
                released_keys_lock = threading.Lock()

                def mark_key_released(key: str):
                    with released_keys_lock:
                        released_keys.add(key)

                try:
                    # Process items in parallel using thread pool
                    with ThreadPoolExecutor(max_workers=len(items_with_keys)) as executor:
                        # Submit all items with their pre-reserved keys
                        futures: Dict[Future, tuple] = {}
                        for item, api_key in items_with_keys:
                            future = executor.submit(
                                self._process_item_with_key,
                                item,
                                batch_id,
                                api_key,
                                mark_key_released
                            )
                            futures[future] = (item, api_key)

                        # Wait for all to complete (or stop event)
                        for future in as_completed(futures):
                            if self._stop_event.is_set():
                                self.logger.info("Stop event received, cancelling remaining items")
                                executor.shutdown(wait=False, cancel_futures=True)
                                break

                            item, api_key = futures[future]
                            try:
                                future.result()  # Raises if the thread raised
                            except AnalysisCancelledException:
                                self.logger.info(f"Batch job {batch_id} cancelled")
                                self._mark_batch_stopped(batch_id, "Cancelled by user")
                                executor.shutdown(wait=False, cancel_futures=True)
                                return
                            except Exception as e:
                                self._handle_item_error(item, str(e), batch_id)

                finally:
                    # Release any keys that weren't released by workers
                    with released_keys_lock:
                        for key in reserved_keys:
                            if key not in released_keys:
                                self.api_key_manager.release_key(key)
                                self.logger.debug(f"Released unreleased key in finally block")

                # Update batch progress after each parallel batch completes
                self._update_batch_progress(batch_id)

                # Small delay between parallel batches
                time.sleep(1)

        except Exception as e:
            self.logger.error(f"Batch worker error: {e}", exc_info=True)
            self._mark_batch_failed(batch_id, str(e))
        finally:
            self._cleanup_worker(batch_id)

    def _get_next_pending_item(self, batch_id: str) -> Optional[Dict]:
        """Get next pending item from batch."""
        query = """
            SELECT id, ticker, company_name, attempts
            FROM batch_items
            WHERE batch_id = ? AND status = 'pending'
            ORDER BY id
            LIMIT 1
        """
        row = self.db._execute_with_retry(query, (batch_id,), fetch_one=True)

        if row:
            return {
                'id': row['id'],
                'ticker': row['ticker'],
                'company_name': row['company_name'],
                'attempts': row['attempts']
            }
        return None

    def _get_pending_items(self, batch_id: str, limit: int = 10) -> List[Dict]:
        """
        Get multiple pending items from batch for parallel processing.

        Fix #6: Uses a single atomic transaction for both SELECT and UPDATE
        to prevent race conditions and improve performance.

        Fix #3: Does NOT increment attempts here - that happens on error
        to ensure max_retries means "number of retries after initial attempt".

        Args:
            batch_id: Batch to get items from
            limit: Maximum number of items to return

        Returns:
            List of item dictionaries
        """
        import sqlite3

        # Fix #6 & #8: Use single atomic transaction for better concurrency
        try:
            with sqlite3.connect(self.db.db_path, timeout=30.0) as conn:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Start immediate transaction to lock for write
                cursor.execute("BEGIN IMMEDIATE")

                # SELECT pending items
                cursor.execute("""
                    SELECT id, ticker, company_name, attempts
                    FROM batch_items
                    WHERE batch_id = ? AND status = 'pending'
                    ORDER BY id
                    LIMIT ?
                """, (batch_id, limit))
                rows = cursor.fetchall()

                if not rows:
                    conn.commit()
                    return []

                items = []
                item_ids = []

                for row in rows:
                    items.append({
                        'id': row['id'],
                        'ticker': row['ticker'],
                        'company_name': row['company_name'],
                        'attempts': row['attempts']
                    })
                    item_ids.append(row['id'])

                # Fix #6: Single batched UPDATE for all items
                # Fix #3: Don't increment attempts here - do it on error
                placeholders = ','.join('?' * len(item_ids))
                now = datetime.utcnow().isoformat()
                cursor.execute(f"""
                    UPDATE batch_items
                    SET status = 'running', started_at = ?
                    WHERE id IN ({placeholders})
                    AND status = 'pending'
                """, [now] + item_ids)

                # Verify we updated the expected number of rows
                if cursor.rowcount != len(item_ids):
                    self.logger.warning(
                        f"Expected to update {len(item_ids)} items but updated {cursor.rowcount}. "
                        "Some items may have been grabbed by another worker."
                    )

                conn.commit()
                return items

        except sqlite3.Error as e:
            self.logger.error(f"Database error in _get_pending_items: {e}")
            return []

    def _process_item_parallel(self, item: Dict, batch_id: str):
        """
        Process a single batch item in a parallel worker thread.

        This method is thread-safe and creates its own AnalysisService
        instance for isolation. It uses reserve_key() to atomically
        get an API key, ensuring no conflicts with other parallel workers.

        Args:
            item: Item dictionary with id, ticker, company_name, attempts
            batch_id: Parent batch ID
        """
        # Import here to avoid circular imports
        from fintel.ui.services.analysis_service import AnalysisService

        item_id = item['id']
        ticker = item['ticker']

        # Create thread-local analysis service
        # This ensures each thread has its own DB connection and browser
        analysis_service = AnalysisService(self.db)

        self.logger.info(f"[Parallel] Processing batch item: {ticker}")

        # Update batch last activity
        query = """
            UPDATE batch_jobs SET last_activity_at = ? WHERE batch_id = ?
        """
        self.db._execute_with_retry(query, (datetime.utcnow().isoformat(), batch_id))

        # Get batch config
        batch_config = self._get_batch_config(batch_id)

        # Run analysis
        try:
            run_id = analysis_service.run_analysis(
                ticker=ticker,
                analysis_type=batch_config['analysis_type'],
                filing_type=batch_config['filing_type'],
                num_years=batch_config['num_years'],
                company_name=item.get('company_name'),
                custom_prompt=batch_config.get('custom_prompt')
            )

            # Mark as completed
            query = """
                UPDATE batch_items
                SET status = 'completed', run_id = ?, completed_at = ?
                WHERE id = ?
            """
            self.db._execute_with_retry(query, (run_id, datetime.utcnow().isoformat(), item_id))

            self.logger.info(f"[Parallel] Completed batch item: {ticker} (run_id: {run_id})")

        except Exception as e:
            self.logger.error(f"[Parallel] Failed batch item {ticker}: {e}")
            raise  # Let the caller handle error tracking

    def _process_item_with_key(
        self,
        item: Dict,
        batch_id: str,
        api_key: str,
        release_callback
    ):
        """
        Process a batch item with a pre-reserved API key (Fix #1).

        This method is called by the batch worker with an already-reserved API key,
        preventing the race condition where threads compete for keys.

        Args:
            item: Item dictionary with id, ticker, company_name, attempts
            batch_id: Parent batch ID
            api_key: Pre-reserved API key to use for this analysis
            release_callback: Callback function to mark key as released
        """
        # Import here to avoid circular imports
        from fintel.ui.services.analysis_service import AnalysisService

        item_id = item['id']
        ticker = item['ticker']

        try:
            # Create thread-local analysis service
            analysis_service = AnalysisService(self.db)

            self.logger.info(f"[Parallel] Processing {ticker} with pre-reserved API key")

            # Update batch last activity
            query = """
                UPDATE batch_jobs SET last_activity_at = ? WHERE batch_id = ?
            """
            self.db._execute_with_retry(query, (datetime.utcnow().isoformat(), batch_id))

            # Get batch config
            batch_config = self._get_batch_config(batch_id)

            # Run analysis with the pre-reserved key
            run_id = analysis_service.run_analysis(
                ticker=ticker,
                analysis_type=batch_config['analysis_type'],
                filing_type=batch_config['filing_type'],
                num_years=batch_config['num_years'],
                company_name=item.get('company_name'),
                custom_prompt=batch_config.get('custom_prompt'),
                api_key=api_key  # Pass pre-reserved key
            )

            # Mark as completed
            query = """
                UPDATE batch_items
                SET status = 'completed', run_id = ?, completed_at = ?
                WHERE id = ?
            """
            self.db._execute_with_retry(query, (run_id, datetime.utcnow().isoformat(), item_id))

            self.logger.info(f"[Parallel] Completed {ticker} (run_id: {run_id})")

        except Exception as e:
            self.logger.error(f"[Parallel] Failed {ticker}: {e}")
            raise  # Let the caller handle error tracking

        finally:
            # Always release the key and notify
            self.api_key_manager.release_key(api_key)
            release_callback(api_key)

    def _process_item(self, item: Dict, service, batch_id: str):
        """Process a single batch item."""
        item_id = item['id']
        ticker = item['ticker']

        self.logger.info(f"Processing batch item: {ticker}")

        # Mark as running
        query = """
            UPDATE batch_items
            SET status = 'running', started_at = ?, attempts = attempts + 1
            WHERE id = ?
        """
        self.db._execute_with_retry(query, (datetime.utcnow().isoformat(), item_id))

        # Update batch last activity
        query = """
            UPDATE batch_jobs SET last_activity_at = ? WHERE batch_id = ?
        """
        self.db._execute_with_retry(query, (datetime.utcnow().isoformat(), batch_id))

        # Get batch config
        batch_config = self._get_batch_config(batch_id)

        # Run analysis
        try:
            run_id = service.run_analysis(
                ticker=ticker,
                analysis_type=batch_config['analysis_type'],
                filing_type=batch_config['filing_type'],
                num_years=batch_config['num_years'],
                company_name=item.get('company_name'),
                custom_prompt=batch_config.get('custom_prompt')
            )

            # Mark as completed
            query = """
                UPDATE batch_items
                SET status = 'completed', run_id = ?, completed_at = ?
                WHERE id = ?
            """
            self.db._execute_with_retry(query, (run_id, datetime.utcnow().isoformat(), item_id))

            self.logger.info(f"Completed batch item: {ticker} (run_id: {run_id})")

        except Exception as e:
            raise  # Let caller handle

    def _wait_for_reset(self, batch_id: str):
        """
        Wait until midnight PST for rate limit reset.

        Fix #5: Verifies that API keys are actually available after the
        calculated reset time, handling potential clock drift or timezone issues.
        """
        wait_seconds = self.rate_limiter.wait_for_reset()

        # Calculate resume time
        resume_time = datetime.utcnow() + timedelta(seconds=wait_seconds)

        self.logger.info(
            f"All API keys exhausted. Waiting {wait_seconds/3600:.1f} hours "
            f"until midnight PST reset."
        )

        # Update queue state
        query = """
            UPDATE queue_state
            SET next_run_at = ?, updated_at = ?
            WHERE id = 1
        """
        self.db._execute_with_retry(query, (resume_time.isoformat(), datetime.utcnow().isoformat()))

        # Update batch status
        query = """
            UPDATE batch_jobs
            SET status = 'waiting_reset', last_activity_at = ?
            WHERE batch_id = ?
        """
        self.db._execute_with_retry(query, (datetime.utcnow().isoformat(), batch_id))

        # Sleep in chunks to allow for stop signals
        chunk_size = 60  # 1 minute
        while wait_seconds > 0 and not self._stop_event.is_set():
            sleep_time = min(chunk_size, wait_seconds)
            time.sleep(sleep_time)
            wait_seconds -= sleep_time

        if not self._stop_event.is_set():
            # Fix #5: VERIFY reset actually occurred before resuming
            available_keys = self.api_key_manager.get_available_keys()

            if not available_keys:
                self.logger.warning(
                    "Reset time reached but no API keys available! "
                    "Possible timezone issue or API limit change. Rechecking..."
                )
                # Check if we need to wait more
                additional_wait = self.rate_limiter.wait_for_reset()
                if additional_wait > 60:  # More than a minute to wait
                    self.logger.info(f"Need to wait additional {additional_wait}s")
                    # Recursive call with updated wait time
                    self._wait_for_reset(batch_id)
                    return
                else:
                    # Wait a bit and retry
                    time.sleep(60)
                    available_keys = self.api_key_manager.get_available_keys()

            if available_keys:
                self.logger.info(
                    f"Rate limit reset confirmed - {len(available_keys)} keys available. "
                    "Resuming batch."
                )
                query = """
                    UPDATE batch_jobs
                    SET status = 'running', last_activity_at = ?
                    WHERE batch_id = ?
                """
                self.db._execute_with_retry(query, (datetime.utcnow().isoformat(), batch_id))
            else:
                self.logger.error(
                    "No API keys available after reset verification. "
                    "Manual intervention may be required."
                )

    def _update_batch_progress(self, batch_id: str):
        """Update batch progress statistics."""
        query = """
            SELECT
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                SUM(CASE WHEN status = 'skipped' THEN 1 ELSE 0 END) as skipped
            FROM batch_items
            WHERE batch_id = ?
        """
        row = self.db._execute_with_retry(query, (batch_id,), fetch_one=True)

        completed = row['completed'] or 0 if row else 0
        failed = row['failed'] or 0 if row else 0
        skipped = row['skipped'] or 0 if row else 0

        # Estimate completion time
        estimate = self._estimate_completion(batch_id, completed)

        query = """
            UPDATE batch_jobs
            SET completed_tickers = ?, failed_tickers = ?, skipped_tickers = ?,
                estimated_completion = ?, last_activity_at = ?
            WHERE batch_id = ?
        """
        self.db._execute_with_retry(query, (
            completed, failed, skipped, estimate, datetime.utcnow().isoformat(), batch_id
        ))

    def _estimate_completion(self, batch_id: str, completed: int) -> Optional[str]:
        """Estimate when batch will complete."""
        batch = self.get_batch_status(batch_id)
        if not batch or completed == 0:
            return None

        total = batch['total_tickers']
        remaining = total - completed - batch['failed_tickers'] - batch.get('skipped_tickers', 0)

        if remaining <= 0:
            return datetime.utcnow().isoformat()

        # Calculate based on API limits
        keys_count = len(self.config.google_api_keys)
        requests_per_day = keys_count * 20  # DAILY_LIMIT_PER_KEY
        days_remaining = remaining / max(requests_per_day, 1)

        estimate = datetime.utcnow() + timedelta(days=days_remaining)
        return estimate.isoformat()

    def pause_batch(self, batch_id: str):
        """Pause batch processing."""
        self._pause_event.set()
        query = """
            UPDATE batch_jobs
            SET status = 'paused', last_activity_at = ?
            WHERE batch_id = ?
        """
        self.db._execute_with_retry(query, (datetime.utcnow().isoformat(), batch_id))
        self.logger.info(f"Paused batch {batch_id}")

    def resume_batch(self, batch_id: str) -> bool:
        """Resume paused batch."""
        # Check if worker is still running
        if self._worker_thread and self._worker_thread.is_alive():
            self._pause_event.clear()
            query = """
                UPDATE batch_jobs
                SET status = 'running', last_activity_at = ?
                WHERE batch_id = ?
            """
            self.db._execute_with_retry(query, (datetime.utcnow().isoformat(), batch_id))
            self.logger.info(f"Resumed batch {batch_id}")
            return True
        else:
            # Worker died, restart it
            return self.start_batch_job(batch_id)

    def stop_batch(self, batch_id: str):
        """Stop batch processing entirely."""
        self._stop_event.set()
        if self._worker_thread:
            self._worker_thread.join(timeout=10)
        self._mark_batch_stopped(batch_id, "Stopped by user")
        self.logger.info(f"Stopped batch {batch_id}")

    def get_batch_status(self, batch_id: str) -> Optional[Dict]:
        """Get detailed batch status."""
        query = """
            SELECT
                batch_id, name, total_tickers, completed_tickers, failed_tickers, skipped_tickers,
                status, analysis_type, filing_type, num_years,
                created_at, started_at, completed_at, last_activity_at,
                estimated_completion, error_message
            FROM batch_jobs
            WHERE batch_id = ?
        """
        row = self.db._execute_with_retry(query, (batch_id,), fetch_one=True)

        if not row:
            return None

        return {
            'batch_id': row['batch_id'],
            'name': row['name'],
            'total_tickers': row['total_tickers'],
            'completed_tickers': row['completed_tickers'],
            'failed_tickers': row['failed_tickers'],
            'skipped_tickers': row['skipped_tickers'] or 0,
            'status': row['status'],
            'analysis_type': row['analysis_type'],
            'filing_type': row['filing_type'],
            'num_years': row['num_years'],
            'created_at': row['created_at'],
            'started_at': row['started_at'],
            'completed_at': row['completed_at'],
            'last_activity_at': row['last_activity_at'],
            'estimated_completion': row['estimated_completion'],
            'error_message': row['error_message'],
            'pending_tickers': row['total_tickers'] - row['completed_tickers'] - row['failed_tickers'] - (row['skipped_tickers'] or 0),
            'progress_percent': round((row['completed_tickers'] / row['total_tickers']) * 100, 1) if row['total_tickers'] > 0 else 0
        }

    def get_batch_items(self, batch_id: str, status: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """Get items in a batch."""
        if status:
            query = """
                SELECT id, ticker, company_name, status, run_id, attempts, error_message,
                       created_at, started_at, completed_at
                FROM batch_items
                WHERE batch_id = ? AND status = ?
                ORDER BY id
                LIMIT ?
            """
            rows = self.db._execute_with_retry(query, (batch_id, status, limit), fetch_all=True)
        else:
            query = """
                SELECT id, ticker, company_name, status, run_id, attempts, error_message,
                       created_at, started_at, completed_at
                FROM batch_items
                WHERE batch_id = ?
                ORDER BY id
                LIMIT ?
            """
            rows = self.db._execute_with_retry(query, (batch_id, limit), fetch_all=True)

        items = []
        for row in rows:
            items.append({
                'id': row['id'],
                'ticker': row['ticker'],
                'company_name': row['company_name'],
                'status': row['status'],
                'run_id': row['run_id'],
                'attempts': row['attempts'],
                'error_message': row['error_message'],
                'created_at': row['created_at'],
                'started_at': row['started_at'],
                'completed_at': row['completed_at']
            })
        return items

    def get_all_batches(self, limit: int = 50) -> List[Dict]:
        """Get all batch jobs."""
        query = """
            SELECT batch_id, name, total_tickers, completed_tickers, failed_tickers,
                   status, analysis_type, created_at, estimated_completion
            FROM batch_jobs
            ORDER BY created_at DESC
            LIMIT ?
        """
        rows = self.db._execute_with_retry(query, (limit,), fetch_all=True)

        batches = []
        for row in rows:
            batches.append({
                'batch_id': row['batch_id'],
                'name': row['name'],
                'total_tickers': row['total_tickers'],
                'completed_tickers': row['completed_tickers'],
                'failed_tickers': row['failed_tickers'],
                'status': row['status'],
                'analysis_type': row['analysis_type'],
                'created_at': row['created_at'],
                'estimated_completion': row['estimated_completion'],
                'progress_percent': round((row['completed_tickers'] / row['total_tickers']) * 100, 1) if row['total_tickers'] > 0 else 0
            })
        return batches

    def get_queue_state(self) -> Dict:
        """Get current queue state."""
        query = """
            SELECT is_running, current_batch_id, next_run_at, daily_requests_made,
                   last_reset_date, worker_pid, updated_at
            FROM queue_state
            WHERE id = 1
        """
        row = self.db._execute_with_retry(query, fetch_one=True)

        if row:
            return {
                'is_running': bool(row['is_running']),
                'current_batch_id': row['current_batch_id'],
                'next_run_at': row['next_run_at'],
                'daily_requests_made': row['daily_requests_made'],
                'last_reset_date': row['last_reset_date'],
                'worker_pid': row['worker_pid'],
                'updated_at': row['updated_at']
            }
        return {'is_running': False}

    def delete_batch(self, batch_id: str) -> bool:
        """Delete a batch job and its items."""
        # Check if running
        batch = self.get_batch_status(batch_id)
        if batch and batch['status'] in ['running', 'waiting_reset']:
            self.stop_batch(batch_id)

        query = "DELETE FROM batch_items WHERE batch_id = ?"
        self.db._execute_with_retry(query, (batch_id,))

        query = "DELETE FROM batch_jobs WHERE batch_id = ?"
        self.db._execute_with_retry(query, (batch_id,))

        self.logger.info(f"Deleted batch {batch_id}")
        return True

    def _get_batch_config(self, batch_id: str) -> Dict:
        """Get batch configuration."""
        query = """
            SELECT analysis_type, filing_type, num_years, config_json
            FROM batch_jobs
            WHERE batch_id = ?
        """
        row = self.db._execute_with_retry(query, (batch_id,), fetch_one=True)

        config = json.loads(row['config_json']) if row and row['config_json'] else {}
        if row:
            config['analysis_type'] = row['analysis_type']
            config['filing_type'] = row['filing_type']
            config['num_years'] = row['num_years']
        return config

    def _complete_batch(self, batch_id: str):
        """Mark batch as complete."""
        query = """
            UPDATE batch_jobs
            SET status = 'completed', completed_at = ?, last_activity_at = ?
            WHERE batch_id = ?
        """
        now = datetime.utcnow().isoformat()
        self.db._execute_with_retry(query, (now, now, batch_id))
        self.logger.info(f"Batch {batch_id} completed")

    def _mark_batch_failed(self, batch_id: str, error: str):
        """Mark batch as failed."""
        query = """
            UPDATE batch_jobs
            SET status = 'failed', error_message = ?, last_activity_at = ?
            WHERE batch_id = ?
        """
        self.db._execute_with_retry(query, (error, datetime.utcnow().isoformat(), batch_id))

    def _mark_batch_stopped(self, batch_id: str, reason: str):
        """Mark batch as stopped."""
        query = """
            UPDATE batch_jobs
            SET status = 'stopped', error_message = ?, last_activity_at = ?
            WHERE batch_id = ?
        """
        self.db._execute_with_retry(query, (reason, datetime.utcnow().isoformat(), batch_id))

    def _handle_item_error(self, item: Dict, error: str, batch_id: str):
        """
        Handle error processing an item.

        Fix #3: Corrected retry semantics:
        - Increments attempts AFTER failure (not when starting)
        - max_retries=2 means 2 retries after initial = 3 total attempts
        - Uses > comparison so max_retries attempts are allowed after initial

        With max_retries=2:
        - attempts=0 -> initial attempt fails -> increment to 1 -> 1 > 2? No -> retry
        - attempts=1 -> retry 1 fails -> increment to 2 -> 2 > 2? No -> retry
        - attempts=2 -> retry 2 fails -> increment to 3 -> 3 > 2? Yes -> mark failed
        """
        item_id = item['id']
        max_retries = self._get_batch_config(batch_id).get('max_retries', 2)

        # Fix #3: Increment attempts on ERROR, not when starting
        query = """
            UPDATE batch_items
            SET attempts = attempts + 1
            WHERE id = ?
        """
        self.db._execute_with_retry(query, (item_id,))

        # Get updated attempts count
        query = "SELECT attempts FROM batch_items WHERE id = ?"
        row = self.db._execute_with_retry(query, (item_id,), fetch_one=True)
        current_attempts = row['attempts'] if row else 1

        # Fix #3: Use > instead of >= so max_retries retries are allowed
        if current_attempts > max_retries:
            # Mark as failed - we've exhausted all retries
            query = """
                UPDATE batch_items
                SET status = 'failed', error_message = ?
                WHERE id = ?
            """
            self.db._execute_with_retry(query, (error, item_id))
            self.logger.warning(
                f"Item {item['ticker']} failed after {current_attempts} attempts "
                f"(max_retries={max_retries}): {error}"
            )
        else:
            # Reset to pending for retry
            query = """
                UPDATE batch_items
                SET status = 'pending'
                WHERE id = ?
            """
            self.db._execute_with_retry(query, (item_id,))
            self.logger.info(
                f"Item {item['ticker']} will be retried "
                f"(attempt {current_attempts}/{max_retries + 1})"
            )

    def _cleanup_worker(self, batch_id: str):
        """Cleanup worker state."""
        query = """
            UPDATE queue_state
            SET is_running = 0, current_batch_id = NULL, worker_pid = NULL, updated_at = ?
            WHERE id = 1
        """
        self.db._execute_with_retry(query, (datetime.utcnow().isoformat(),))

    # =========================================================================
    # Synthesis/Combination Analysis
    # =========================================================================

    def get_batch_results_for_synthesis(self, batch_id: str) -> List[Dict]:
        """
        Get all completed analysis results from a batch for synthesis.

        This retrieves the full analysis results for each completed item
        in the batch, which can then be fed into a synthesis analysis.

        Args:
            batch_id: Batch ID to get results from

        Returns:
            List of dictionaries with ticker, run_id, and result data
        """
        # Get completed items with their run_ids
        completed_items = self.get_batch_items(batch_id, status='completed', limit=1000)

        results = []
        for item in completed_items:
            if item.get('run_id'):
                # Get the analysis results for this run
                run_results = self.db.get_analysis_results(item['run_id'])
                if run_results:
                    results.append({
                        'ticker': item['ticker'],
                        'company_name': item.get('company_name'),
                        'run_id': item['run_id'],
                        'results': run_results
                    })

        return results

    def create_synthesis_analysis(
        self,
        batch_id: str,
        synthesis_prompt: Optional[str] = None
    ) -> Optional[str]:
        """
        Create a synthesis analysis that combines all results from a batch.

        This takes all completed analyses from a batch and runs a new AI
        analysis that synthesizes them into comprehensive insights.

        Args:
            batch_id: Batch to synthesize results from
            synthesis_prompt: Optional custom prompt for synthesis

        Returns:
            run_id of the synthesis analysis, or None if failed
        """
        from fintel.ai.providers.gemini import GeminiProvider

        # Get batch info
        batch = self.get_batch_status(batch_id)
        if not batch:
            self.logger.error(f"Batch {batch_id} not found")
            return None

        if batch['status'] != 'completed':
            self.logger.warning(f"Batch {batch_id} is not completed (status: {batch['status']})")

        # Get all results
        batch_results = self.get_batch_results_for_synthesis(batch_id)
        if not batch_results:
            self.logger.error(f"No results found for batch {batch_id}")
            return None

        self.logger.info(f"Creating synthesis for batch {batch_id} with {len(batch_results)} analyses")

        # Create synthesis run record
        run_id = str(uuid.uuid4())
        self.db.create_analysis_run(
            run_id=run_id,
            ticker=f"BATCH:{batch['name']}",
            analysis_type='synthesis',
            filing_type=batch['filing_type'],
            years=[],
            config={
                'batch_id': batch_id,
                'source_count': len(batch_results),
                'tickers': [r['ticker'] for r in batch_results]
            },
            company_name=f"Synthesis of {len(batch_results)} companies"
        )

        try:
            self.db.update_run_status(run_id, 'running')
            self.db.update_run_progress(
                run_id,
                progress_message=f"Synthesizing {len(batch_results)} analyses...",
                progress_percent=10
            )

            # Build synthesis prompt
            default_synthesis_prompt = """
You are analyzing a collection of company analyses to identify patterns, trends, and insights.

For each company below, you have the full analysis results. Your task is to:

1. **Executive Summary**: Provide a high-level overview of the batch
2. **Common Themes**: Identify patterns that appear across multiple companies
3. **Outliers**: Highlight companies that stand out (positively or negatively)
4. **Sector/Industry Trends**: Note any industry-wide observations
5. **Investment Insights**: Key takeaways for investment decisions
6. **Risk Patterns**: Common risks identified across the batch
7. **Rankings**: Rank the companies by key metrics if applicable

Be concise but comprehensive. Focus on actionable insights.
"""
            prompt = synthesis_prompt or default_synthesis_prompt

            # Build the full context with all analyses
            context_parts = [prompt, "\n\n=== INDIVIDUAL COMPANY ANALYSES ===\n"]

            for item in batch_results:
                ticker = item['ticker']
                company = item.get('company_name', ticker)
                results = item['results']

                context_parts.append(f"\n--- {ticker}: {company} ---\n")

                # Include the analysis results (may have multiple years)
                for result in results:
                    year = result.get('year', 'N/A')
                    data = result.get('data', {})

                    context_parts.append(f"\nYear {year}:\n")

                    # Format the result data nicely
                    if isinstance(data, dict):
                        for key, value in data.items():
                            if isinstance(value, (list, dict)):
                                context_parts.append(f"  {key}: {json.dumps(value, indent=2)}\n")
                            else:
                                context_parts.append(f"  {key}: {value}\n")
                    else:
                        context_parts.append(f"  {data}\n")

            full_prompt = "".join(context_parts)

            self.db.update_run_progress(
                run_id,
                progress_message="Running AI synthesis...",
                progress_percent=50
            )

            # Reserve API key
            api_key = self.api_key_manager.reserve_key()
            if not api_key:
                raise Exception("No API keys available for synthesis")

            try:
                provider = GeminiProvider(
                    api_key=api_key,
                    model=self.config.default_model,
                    thinking_budget=self.config.thinking_budget,
                    rate_limiter=self.rate_limiter
                )

                # Use a flexible schema for synthesis
                from pydantic import BaseModel, Field
                from typing import List as TypeList

                class CompanyRanking(BaseModel):
                    ticker: str
                    rank: int
                    reason: str

                class SynthesisResult(BaseModel):
                    executive_summary: str = Field(description="High-level overview")
                    common_themes: TypeList[str] = Field(description="Patterns across companies")
                    outliers: TypeList[str] = Field(description="Standout companies")
                    sector_trends: TypeList[str] = Field(description="Industry observations")
                    investment_insights: TypeList[str] = Field(description="Key takeaways")
                    risk_patterns: TypeList[str] = Field(description="Common risks")
                    top_companies: TypeList[CompanyRanking] = Field(description="Top ranked companies")
                    bottom_companies: TypeList[CompanyRanking] = Field(description="Bottom ranked companies")
                    recommendations: TypeList[str] = Field(description="Action recommendations")

                result = provider.generate_with_retry(
                    prompt=full_prompt,
                    schema=SynthesisResult,
                    max_retries=3,
                    retry_delay=10
                )

                self.api_key_manager.record_usage(api_key)

                if result:
                    # Store synthesis result
                    self.db.store_result(
                        run_id=run_id,
                        ticker=f"BATCH:{batch['name']}",
                        fiscal_year=0,  # Special year for synthesis
                        filing_type=batch['filing_type'],
                        result_type='SynthesisResult',
                        result_data=result.model_dump()
                    )

                    self.db.update_run_status(run_id, 'completed')
                    self.logger.info(f"Synthesis completed: {run_id}")
                    return run_id
                else:
                    raise Exception("AI returned no result")

            finally:
                self.api_key_manager.release_key(api_key)

        except Exception as e:
            error_msg = f"Synthesis failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            self.db.update_run_status(run_id, 'failed', error_msg)
            return None

    def export_batch_to_csv(self, batch_id: str) -> str:
        """
        Export batch results to CSV format.

        Args:
            batch_id: Batch to export

        Returns:
            CSV string content
        """
        import csv
        from io import StringIO

        # Get batch info
        batch = self.get_batch_status(batch_id)
        if not batch:
            return ""

        # Get all items with results
        items = self.get_batch_items(batch_id, limit=10000)

        output = StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow([
            'Ticker', 'Company Name', 'Status', 'Run ID',
            'Started At', 'Completed At', 'Error Message'
        ])

        for item in items:
            writer.writerow([
                item['ticker'],
                item.get('company_name', ''),
                item['status'],
                item.get('run_id', ''),
                item.get('started_at', ''),
                item.get('completed_at', ''),
                item.get('error_message', '')
            ])

        return output.getvalue()

    def export_batch_results_to_json(self, batch_id: str) -> str:
        """
        Export batch results with full analysis data to JSON.

        Args:
            batch_id: Batch to export

        Returns:
            JSON string content
        """
        batch = self.get_batch_status(batch_id)
        if not batch:
            return "{}"

        # Get all results
        batch_results = self.get_batch_results_for_synthesis(batch_id)

        export_data = {
            'batch_id': batch_id,
            'batch_name': batch['name'],
            'analysis_type': batch['analysis_type'],
            'filing_type': batch['filing_type'],
            'total_tickers': batch['total_tickers'],
            'completed_tickers': batch['completed_tickers'],
            'failed_tickers': batch['failed_tickers'],
            'status': batch['status'],
            'created_at': batch['created_at'],
            'completed_at': batch.get('completed_at'),
            'results': batch_results
        }

        return json.dumps(export_data, indent=2, default=str)

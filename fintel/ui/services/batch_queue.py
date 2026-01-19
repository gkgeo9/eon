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

from fintel.core import get_logger, get_config, IKeyManager, IRateLimiter, FintelConfig
from fintel.ai import APIKeyManager, RateLimiter
from fintel.ai.api_config import get_sec_limits
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

    Supports dependency injection for testability. All dependencies are optional
    and will be created with sensible defaults if not provided.
    """

    def __init__(
        self,
        db: DatabaseRepository,
        config: Optional[FintelConfig] = None,
        key_manager: Optional[IKeyManager] = None,
        rate_limiter: Optional[IRateLimiter] = None,
    ):
        """
        Initialize the batch queue service.

        Args:
            db: Database repository (required)
            config: Configuration (optional, uses get_config() if not provided)
            key_manager: API key manager (optional, creates default if not provided)
            rate_limiter: Rate limiter (optional, creates default if not provided)
        """
        self.db = db
        self.config = config or get_config()
        self.logger = get_logger(f"{__name__}.BatchQueueService")

        # Initialize components - use injected or create defaults
        self.api_key_manager = key_manager or APIKeyManager(self.config.google_api_keys)
        self.rate_limiter = rate_limiter or RateLimiter()

        # SEC rate limiting configuration for staggered worker starts
        sec_limits = get_sec_limits()
        self._worker_stagger_delay = sec_limits.WORKER_STAGGER_DELAY

        # Worker thread control
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()

        # Fix #4: Cleanup stale worker state from crashed processes
        self._cleanup_stale_worker()

        self.logger.info(
            f"BatchQueueService initialized (worker_stagger_delay={self._worker_stagger_delay}s)"
        )

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

        # Reset any items stuck in 'running' status back to 'pending'
        # This handles the case where a previous run crashed mid-process
        reset_query = """
            UPDATE batch_items
            SET status = 'pending', started_at = NULL
            WHERE batch_id = ? AND status = 'running'
        """
        result = self.db._execute_with_retry(reset_query, (batch_id,))
        if result and result > 0:
            self.logger.info(f"Reset {result} stale 'running' items to 'pending' for batch {batch_id}")

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
                # Use wait_timeout=0 for quick reservation - batch queue handles
                # key exhaustion with _wait_for_reset() instead
                items_with_keys = []
                reserved_keys = []

                for item in pending_items:
                    key = self.api_key_manager.reserve_key(wait_timeout=0)
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
                        # NOTE: When stagger delay > 0, workers will release their key
                        # during the stagger wait and re-acquire after, so they don't
                        # hold keys while waiting.
                        futures: Dict[Future, tuple] = {}
                        for worker_idx, (item, api_key) in enumerate(items_with_keys):
                            stagger_delay = worker_idx * self._worker_stagger_delay
                            future = executor.submit(
                                self._process_item_with_staggered_start,
                                item,
                                batch_id,
                                api_key,
                                mark_key_released,
                                stagger_delay,
                                worker_idx  # Pass index for logging
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
                                # Update batch progress immediately after each item completes
                                # This ensures the UI shows real-time progress
                                self._update_batch_progress(batch_id)
                            except AnalysisCancelledException:
                                self.logger.info(f"Batch job {batch_id} cancelled")
                                self._mark_batch_stopped(batch_id, "Cancelled by user")
                                executor.shutdown(wait=False, cancel_futures=True)
                                return
                            except Exception as e:
                                self._handle_item_error(item, str(e), batch_id)
                                # Also update progress after errors so failed count updates
                                self._update_batch_progress(batch_id)

                finally:
                    # Release any keys that weren't released by workers
                    with released_keys_lock:
                        for key in reserved_keys:
                            if key not in released_keys:
                                self.api_key_manager.release_key(key)
                                self.logger.debug(f"Released unreleased key in finally block")

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

    def _process_item_with_staggered_start(
        self,
        item: Dict,
        batch_id: str,
        api_key: str,
        release_callback,
        stagger_delay: float,
        worker_idx: int = 0
    ):
        """
        Process a batch item with staggered start for SEC rate limiting.

        This wrapper adds a delay before starting the actual processing to prevent
        all workers from hitting the SEC EDGAR API simultaneously (thundering herd).

        IMPORTANT: To avoid holding API keys during the stagger wait (which would
        exhaust all keys immediately), workers with stagger_delay > 0 will:
        1. Release their pre-reserved key immediately
        2. Wait for the stagger delay
        3. Re-acquire a key after the delay
        4. Then proceed with processing

        With 25 workers and a 30-second stagger:
        - Worker 0: starts immediately (keeps pre-reserved key)
        - Worker 1: releases key, waits 30s, re-acquires key, starts
        - Worker 2: releases key, waits 60s, re-acquires key, starts
        - ...
        - Worker 24: releases key, waits 720s, re-acquires key, starts

        Args:
            item: Item dictionary with id, ticker, company_name, attempts
            batch_id: Parent batch ID
            api_key: Pre-reserved API key to use for this analysis
            release_callback: Callback function to mark key as released
            stagger_delay: Seconds to wait before starting (based on worker index)
            worker_idx: Worker index for logging
        """
        if stagger_delay > 0:
            # Release the pre-reserved key during the wait so other workers can use it
            self.logger.info(
                f"Worker {worker_idx} for {item['ticker']}: releasing key, "
                f"waiting {stagger_delay}s (staggered start)"
            )
            self.api_key_manager.release_key(api_key)
            release_callback(api_key)

            # Sleep in chunks to allow stop event to interrupt
            remaining = stagger_delay
            chunk_size = 5.0  # Check stop event every 5 seconds
            while remaining > 0 and not self._stop_event.is_set():
                sleep_time = min(chunk_size, remaining)
                time.sleep(sleep_time)
                remaining -= sleep_time

            if self._stop_event.is_set():
                self.logger.info(f"Stop event received during stagger wait for {item['ticker']}")
                # Reset item to pending since we didn't process it
                self._reset_item_to_pending(item['id'])
                return

            # Re-acquire a key after the stagger delay
            self.logger.info(f"Worker {worker_idx} for {item['ticker']}: stagger complete, acquiring key")
            new_api_key = self.api_key_manager.reserve_key()

            if new_api_key is None:
                self.logger.warning(
                    f"Worker {worker_idx} for {item['ticker']}: no key available after stagger, "
                    "resetting to pending"
                )
                self._reset_item_to_pending(item['id'])
                return

            # Use a no-op callback since we're managing the key ourselves
            def noop_callback(key: str):
                pass

            # Process with the newly acquired key
            return self._process_item_with_key(item, batch_id, new_api_key, noop_callback)
        else:
            # Worker 0: start immediately with pre-reserved key
            return self._process_item_with_key(item, batch_id, api_key, release_callback)

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
        # Explicitly cleanup worker state to ensure is_running is set to False
        self._cleanup_worker(batch_id)
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
                   status, analysis_type, filing_type, num_years,
                   created_at, estimated_completion, last_activity_at
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
                'filing_type': row['filing_type'],
                'num_years': row['num_years'],
                'created_at': row['created_at'],
                'estimated_completion': row['estimated_completion'],
                'last_activity_at': row['last_activity_at'],
                'progress_percent': round((row['completed_tickers'] / row['total_tickers']) * 100, 1) if row['total_tickers'] > 0 else 0
            })
        return batches

    def get_stale_running_batches(self, stale_minutes: int = 5) -> List[Dict]:
        """
        Get batches that appear stuck in 'running' status with no recent activity.

        Args:
            stale_minutes: Consider batch stale if no activity for this many minutes

        Returns:
            List of stale batch dictionaries
        """
        query = """
            SELECT batch_id, name, total_tickers, completed_tickers, failed_tickers,
                   status, analysis_type, created_at, last_activity_at
            FROM batch_jobs
            WHERE status = 'running'
            AND (
                last_activity_at IS NULL
                OR (julianday('now') - julianday(last_activity_at)) * 24 * 60 > ?
            )
            ORDER BY created_at DESC
        """
        rows = self.db._execute_with_retry(query, (stale_minutes,), fetch_all=True)

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
                'last_activity_at': row['last_activity_at'],
                'progress_percent': round((row['completed_tickers'] / row['total_tickers']) * 100, 1) if row['total_tickers'] > 0 else 0
            })
        return batches

    def mark_batch_as_crashed(self, batch_id: str) -> None:
        """
        Mark a stale running batch as stopped due to crash.

        Args:
            batch_id: Batch to mark as crashed
        """
        now = datetime.utcnow().isoformat()

        # Reset running items to pending
        reset_query = """
            UPDATE batch_items
            SET status = 'pending', started_at = NULL
            WHERE batch_id = ? AND status = 'running'
        """
        self.db._execute_with_retry(reset_query, (batch_id,))

        # Update batch status
        query = """
            UPDATE batch_jobs
            SET status = 'stopped', error_message = 'Worker process crashed - click Resume to continue', last_activity_at = ?
            WHERE batch_id = ?
        """
        self.db._execute_with_retry(query, (now, batch_id))

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

    def create_per_company_synthesis(
        self,
        batch_id: str,
        synthesis_prompt: Optional[str] = None,
        resume: bool = True
    ) -> List[str]:
        """
        Create per-company multi-year synthesis with checkpoint support.

        Features:
        - Saves checkpoint after each company is synthesized
        - Can resume from last checkpoint on crash/restart
        - Tracks which companies have been synthesized

        For batches with multiple years per company, this creates a separate
        synthesis document for each company that analyzes their longitudinal
        trends across all analyzed years.

        Args:
            batch_id: Batch to create syntheses for
            synthesis_prompt: Optional custom prompt for synthesis
            resume: If True, attempt to resume incomplete synthesis job

        Returns:
            List of synthesis run_ids (one per company with 2+ years)
        """
        from fintel.ui.services.analysis_service import AnalysisService

        # Check for existing incomplete synthesis job
        synthesis_job_id = None
        pending_items = []

        if resume:
            incomplete_jobs = self.db.get_incomplete_synthesis_jobs(batch_id)
            if incomplete_jobs:
                job = incomplete_jobs[0]
                synthesis_job_id = job['synthesis_job_id']
                pending_items = self.db.get_pending_synthesis_items(synthesis_job_id)

                if pending_items:
                    self.logger.info(
                        f"Resuming synthesis job {synthesis_job_id} with "
                        f"{len(pending_items)} remaining companies"
                    )
                    self.db.update_synthesis_job_status(synthesis_job_id, 'running')
                else:
                    # All items done, mark complete
                    self.db.update_synthesis_job_status(synthesis_job_id, 'completed')
                    synthesis_job_id = None

        # If not resuming, create new synthesis job
        if not synthesis_job_id:
            synthesis_job_id = str(uuid.uuid4())

            # Get batch info
            batch = self.get_batch_status(batch_id)
            if not batch:
                self.logger.error(f"Batch {batch_id} not found")
                return []

            if batch['status'] != 'completed':
                self.logger.warning(f"Batch {batch_id} is not completed (status: {batch['status']})")

            # Get all completed items grouped by ticker
            completed_items = self.get_batch_items(batch_id, status='completed', limit=1000)

            if not completed_items:
                self.logger.error(f"No completed items found for batch {batch_id}")
                return []

            # Group by ticker and prepare synthesis items
            ticker_results = self._group_batch_items_by_ticker(completed_items)

            # Filter to companies with 2+ years
            eligible_tickers = {
                ticker: data for ticker, data in ticker_results.items()
                if data['num_years'] >= 2
            }

            if not eligible_tickers:
                self.logger.info("No companies with 2+ years for synthesis")
                return []

            # Create synthesis job
            self.db.create_synthesis_job(
                synthesis_job_id=synthesis_job_id,
                batch_id=batch_id,
                total_companies=len(eligible_tickers),
                synthesis_prompt=synthesis_prompt
            )

            # Link to batch
            self.db.link_synthesis_to_batch(batch_id, synthesis_job_id)

            # Create synthesis items for each company
            items_to_create = [
                {
                    'ticker': ticker,
                    'company_name': data['company_name'],
                    'run_id': data['run_id'],
                    'num_years': data['num_years']
                }
                for ticker, data in eligible_tickers.items()
            ]
            self.db.create_synthesis_items(synthesis_job_id, items_to_create)

            # Get pending items for processing
            pending_items = self.db.get_pending_synthesis_items(synthesis_job_id)

            self.db.update_synthesis_job_status(synthesis_job_id, 'running')

            self.logger.info(
                f"Created synthesis job {synthesis_job_id} with "
                f"{len(pending_items)} companies"
            )

        # Process each pending company with checkpointing
        synthesis_run_ids = []
        analysis_service = AnalysisService(self.db)

        total_items = len(pending_items)
        for idx, item in enumerate(pending_items, 1):
            ticker = item['ticker']
            source_run_id = item['source_run_id']

            # Update progress
            progress_pct = int((idx / total_items) * 100)
            self.logger.info(
                f"Synthesizing {ticker} ({idx}/{total_items}) - {progress_pct}%"
            )

            # Mark item as running (checkpoint)
            self.db.update_synthesis_item_status(
                synthesis_job_id, ticker, 'running'
            )

            try:
                synthesis_run_id = analysis_service.create_multi_year_synthesis(
                    run_id=source_run_id,
                    synthesis_prompt=synthesis_prompt
                )

                if synthesis_run_id:
                    # SUCCESS CHECKPOINT
                    self.db.update_synthesis_item_status(
                        synthesis_job_id, ticker, 'completed',
                        synthesis_run_id=synthesis_run_id
                    )
                    synthesis_run_ids.append(synthesis_run_id)
                    self.logger.info(f"Checkpoint: {ticker} synthesis completed")
                else:
                    # Failed but not exception
                    self.db.update_synthesis_item_status(
                        synthesis_job_id, ticker, 'failed',
                        error_message="Synthesis returned None"
                    )
                    self.logger.warning(f"Checkpoint: {ticker} synthesis returned None")

            except Exception as e:
                # FAILURE CHECKPOINT
                error_msg = str(e)
                self.db.update_synthesis_item_status(
                    synthesis_job_id, ticker, 'failed',
                    error_message=error_msg
                )
                self.logger.error(
                    f"Checkpoint: {ticker} synthesis failed: {error_msg}",
                    exc_info=True
                )

        # Mark job complete
        progress = self.db.get_synthesis_progress(synthesis_job_id)
        if progress.get('pending_companies', 0) == 0:
            self.db.update_synthesis_job_status(synthesis_job_id, 'completed')

        self.logger.info(
            f"Synthesis job {synthesis_job_id} finished: "
            f"{len(synthesis_run_ids)} completed, "
            f"{progress.get('failed_companies', 0)} failed"
        )

        return synthesis_run_ids

    def _group_batch_items_by_ticker(
        self,
        completed_items: List[Dict]
    ) -> Dict[str, Dict]:
        """Group completed batch items by ticker with metadata."""
        ticker_results: Dict[str, Dict] = {}

        for item in completed_items:
            ticker = item['ticker']
            run_id = item.get('run_id')

            if not run_id:
                continue

            run_results = self.db.get_analysis_results(run_id)

            if run_results:
                if ticker not in ticker_results:
                    ticker_results[ticker] = {
                        'company_name': item.get('company_name', ticker),
                        'run_id': run_id,
                        'num_years': len(run_results)
                    }
                elif len(run_results) > ticker_results[ticker]['num_years']:
                    ticker_results[ticker]['run_id'] = run_id
                    ticker_results[ticker]['num_years'] = len(run_results)

        return ticker_results

    def get_synthesis_job_status(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of the most recent synthesis job for a batch.

        Args:
            batch_id: Batch ID

        Returns:
            Synthesis job status dict with progress, or None
        """
        incomplete = self.db.get_incomplete_synthesis_jobs(batch_id)
        if incomplete:
            job = incomplete[0]
            progress = self.db.get_synthesis_progress(job['synthesis_job_id'])
            return {**job, **progress}
        return None

    def resume_synthesis(self, batch_id: str, synthesis_prompt: Optional[str] = None) -> List[str]:
        """
        Resume an interrupted synthesis job.

        This is a convenience method that calls create_per_company_synthesis
        with resume=True.

        Args:
            batch_id: Batch ID
            synthesis_prompt: Optional synthesis prompt

        Returns:
            List of synthesis run_ids
        """
        return self.create_per_company_synthesis(batch_id, synthesis_prompt=synthesis_prompt, resume=True)

    def get_batch_num_years(self, batch_id: str) -> int:
        """
        Get the num_years setting for a batch.

        Args:
            batch_id: Batch ID

        Returns:
            Number of years configured for the batch, or 1 if not found
        """
        batch = self.get_batch_status(batch_id)
        if batch:
            return batch.get('num_years', 1)
        return 1

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


def create_batch_queue_service(
    db: DatabaseRepository,
    config: Optional[FintelConfig] = None
) -> BatchQueueService:
    """
    Factory function to create a BatchQueueService with default dependencies.

    This is the recommended way to create a BatchQueueService for production use.
    For testing, use the BatchQueueService constructor directly with mock dependencies.

    Args:
        db: Database repository (required)
        config: Optional configuration (uses get_config() if not provided)

    Returns:
        Configured BatchQueueService instance
    """
    config = config or get_config()
    return BatchQueueService(
        db=db,
        config=config,
        key_manager=APIKeyManager(config.google_api_keys),
        rate_limiter=RateLimiter(),
    )

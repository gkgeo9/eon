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

        self.logger.info("BatchQueueService initialized")

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
        Main worker loop for processing batch items.

        Handles:
        - Processing items one at a time
        - Checking rate limits before each item
        - Sleeping until midnight when exhausted
        - Graceful stop/pause
        """
        # Import here to avoid circular imports
        from fintel.ui.services.analysis_service import AnalysisService
        analysis_service = AnalysisService(self.db)

        try:
            while not self._stop_event.is_set():
                # Check for pause
                if self._pause_event.is_set():
                    self.logger.info("Batch worker paused")
                    time.sleep(5)
                    continue

                # Get next pending item
                item = self._get_next_pending_item(batch_id)
                if not item:
                    # No more items - batch complete
                    self._complete_batch(batch_id)
                    break

                # Check API availability
                available_key = self.api_key_manager.get_available_key()
                if not available_key:
                    # All keys exhausted - wait for midnight reset
                    self._wait_for_reset(batch_id)
                    continue

                # Release key immediately - analysis_service will acquire its own
                self.api_key_manager.release_key(available_key)

                # Process item
                try:
                    self._process_item(item, analysis_service, batch_id)
                except AnalysisCancelledException:
                    self.logger.info(f"Batch job {batch_id} cancelled")
                    self._mark_batch_stopped(batch_id, "Cancelled by user")
                    break
                except Exception as e:
                    self._handle_item_error(item, str(e), batch_id)

                # Update batch progress
                self._update_batch_progress(batch_id)

                # Small delay between items
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
        cursor = self.db._execute_with_retry(query, (batch_id,))
        row = cursor.fetchone()

        if row:
            return {
                'id': row[0],
                'ticker': row[1],
                'company_name': row[2],
                'attempts': row[3]
            }
        return None

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
        """Wait until midnight PST for rate limit reset."""
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
            # Reset complete - update status
            self.logger.info("Rate limit reset detected - resuming batch")
            query = """
                UPDATE batch_jobs
                SET status = 'running', last_activity_at = ?
                WHERE batch_id = ?
            """
            self.db._execute_with_retry(query, (datetime.utcnow().isoformat(), batch_id))

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
        cursor = self.db._execute_with_retry(query, (batch_id,))
        row = cursor.fetchone()

        completed = row[0] or 0
        failed = row[1] or 0
        skipped = row[2] or 0

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
        cursor = self.db._execute_with_retry(query, (batch_id,))
        row = cursor.fetchone()

        if not row:
            return None

        return {
            'batch_id': row[0],
            'name': row[1],
            'total_tickers': row[2],
            'completed_tickers': row[3],
            'failed_tickers': row[4],
            'skipped_tickers': row[5] or 0,
            'status': row[6],
            'analysis_type': row[7],
            'filing_type': row[8],
            'num_years': row[9],
            'created_at': row[10],
            'started_at': row[11],
            'completed_at': row[12],
            'last_activity_at': row[13],
            'estimated_completion': row[14],
            'error_message': row[15],
            'pending_tickers': row[2] - row[3] - row[4] - (row[5] or 0),
            'progress_percent': round((row[3] / row[2]) * 100, 1) if row[2] > 0 else 0
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
            cursor = self.db._execute_with_retry(query, (batch_id, status, limit))
        else:
            query = """
                SELECT id, ticker, company_name, status, run_id, attempts, error_message,
                       created_at, started_at, completed_at
                FROM batch_items
                WHERE batch_id = ?
                ORDER BY id
                LIMIT ?
            """
            cursor = self.db._execute_with_retry(query, (batch_id, limit))

        items = []
        for row in cursor.fetchall():
            items.append({
                'id': row[0],
                'ticker': row[1],
                'company_name': row[2],
                'status': row[3],
                'run_id': row[4],
                'attempts': row[5],
                'error_message': row[6],
                'created_at': row[7],
                'started_at': row[8],
                'completed_at': row[9]
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
        cursor = self.db._execute_with_retry(query, (limit,))

        batches = []
        for row in cursor.fetchall():
            batches.append({
                'batch_id': row[0],
                'name': row[1],
                'total_tickers': row[2],
                'completed_tickers': row[3],
                'failed_tickers': row[4],
                'status': row[5],
                'analysis_type': row[6],
                'created_at': row[7],
                'estimated_completion': row[8],
                'progress_percent': round((row[3] / row[2]) * 100, 1) if row[2] > 0 else 0
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
        cursor = self.db._execute_with_retry(query)
        row = cursor.fetchone()

        if row:
            return {
                'is_running': bool(row[0]),
                'current_batch_id': row[1],
                'next_run_at': row[2],
                'daily_requests_made': row[3],
                'last_reset_date': row[4],
                'worker_pid': row[5],
                'updated_at': row[6]
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
        cursor = self.db._execute_with_retry(query, (batch_id,))
        row = cursor.fetchone()

        config = json.loads(row[3]) if row[3] else {}
        config['analysis_type'] = row[0]
        config['filing_type'] = row[1]
        config['num_years'] = row[2]
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
        """Handle error processing an item."""
        item_id = item['id']
        attempts = item['attempts'] + 1
        max_retries = self._get_batch_config(batch_id).get('max_retries', 2)

        if attempts >= max_retries:
            # Mark as failed
            query = """
                UPDATE batch_items
                SET status = 'failed', error_message = ?
                WHERE id = ?
            """
            self.db._execute_with_retry(query, (error, item_id))
            self.logger.warning(f"Item {item['ticker']} failed after {attempts} attempts: {error}")
        else:
            # Reset to pending for retry
            query = """
                UPDATE batch_items
                SET status = 'pending'
                WHERE id = ?
            """
            self.db._execute_with_retry(query, (item_id,))
            self.logger.info(f"Item {item['ticker']} will be retried (attempt {attempts}/{max_retries})")

    def _cleanup_worker(self, batch_id: str):
        """Cleanup worker state."""
        query = """
            UPDATE queue_state
            SET is_running = 0, current_batch_id = NULL, worker_pid = NULL, updated_at = ?
            WHERE id = 1
        """
        self.db._execute_with_retry(query, (datetime.utcnow().isoformat(),))

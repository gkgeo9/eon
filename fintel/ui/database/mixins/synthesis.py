#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Synthesis checkpoints database operations mixin.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any


class SynthesisMixin:
    """Mixin for synthesis job checkpoint operations."""

    def create_synthesis_job(
        self,
        synthesis_job_id: str,
        batch_id: str,
        total_companies: int,
        synthesis_type: str = 'per_company',
        synthesis_prompt: Optional[str] = None
    ) -> None:
        """
        Create a new synthesis job for checkpoint tracking.

        Args:
            synthesis_job_id: Unique ID for this synthesis job
            batch_id: Source batch ID
            total_companies: Total number of companies to synthesize
            synthesis_type: 'per_company' or 'batch_aggregate'
            synthesis_prompt: Optional custom synthesis prompt
        """
        query = """
            INSERT INTO synthesis_jobs
            (synthesis_job_id, batch_id, synthesis_type, total_companies,
             synthesis_prompt, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        self._execute_with_retry(query, (
            synthesis_job_id,
            batch_id,
            synthesis_type,
            total_companies,
            synthesis_prompt,
            datetime.utcnow().isoformat()
        ))

    def create_synthesis_items(
        self,
        synthesis_job_id: str,
        items: List[Dict[str, Any]]
    ) -> None:
        """
        Batch create synthesis items for all companies.

        Args:
            synthesis_job_id: Synthesis job ID
            items: List of dicts with ticker, company_name, run_id, num_years
        """
        query = """
            INSERT INTO synthesis_items
            (synthesis_job_id, ticker, company_name, source_run_id, num_years)
            VALUES (?, ?, ?, ?, ?)
        """
        for item in items:
            self._execute_with_retry(query, (
                synthesis_job_id,
                item['ticker'],
                item.get('company_name'),
                item.get('run_id'),
                item.get('num_years', 0)
            ))

    def update_synthesis_job_status(
        self,
        synthesis_job_id: str,
        status: str,
        error_message: Optional[str] = None
    ) -> None:
        """
        Update synthesis job status.

        Args:
            synthesis_job_id: Synthesis job ID
            status: New status (pending, running, paused, completed, failed)
            error_message: Optional error message
        """
        now = datetime.utcnow().isoformat()

        if status == 'running':
            query = """
                UPDATE synthesis_jobs
                SET status = ?, started_at = ?, last_checkpoint_at = ?
                WHERE synthesis_job_id = ?
            """
            self._execute_with_retry(query, (status, now, now, synthesis_job_id))
        elif status == 'completed':
            query = """
                UPDATE synthesis_jobs
                SET status = ?, completed_at = ?, last_checkpoint_at = ?, error_message = ?
                WHERE synthesis_job_id = ?
            """
            self._execute_with_retry(query, (status, now, now, error_message, synthesis_job_id))
        else:
            query = """
                UPDATE synthesis_jobs
                SET status = ?, error_message = ?, last_checkpoint_at = ?
                WHERE synthesis_job_id = ?
            """
            self._execute_with_retry(query, (status, error_message, now, synthesis_job_id))

    def update_synthesis_item_status(
        self,
        synthesis_job_id: str,
        ticker: str,
        status: str,
        synthesis_run_id: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> None:
        """
        Update individual company synthesis status (checkpoint).

        Args:
            synthesis_job_id: Synthesis job ID
            ticker: Company ticker
            status: New status (pending, running, completed, failed, skipped)
            synthesis_run_id: Generated synthesis run ID (if completed)
            error_message: Error message (if failed)
        """
        now = datetime.utcnow().isoformat()

        if status == 'running':
            query = """
                UPDATE synthesis_items
                SET status = ?, started_at = ?
                WHERE synthesis_job_id = ? AND ticker = ?
            """
            self._execute_with_retry(query, (status, now, synthesis_job_id, ticker))
        elif status == 'completed':
            query = """
                UPDATE synthesis_items
                SET status = ?, synthesis_run_id = ?, completed_at = ?
                WHERE synthesis_job_id = ? AND ticker = ?
            """
            self._execute_with_retry(query, (status, synthesis_run_id, now, synthesis_job_id, ticker))
            self._increment_synthesis_progress(synthesis_job_id, 'completed')
        elif status == 'failed':
            query = """
                UPDATE synthesis_items
                SET status = ?, error_message = ?, completed_at = ?
                WHERE synthesis_job_id = ? AND ticker = ?
            """
            self._execute_with_retry(query, (status, error_message, now, synthesis_job_id, ticker))
            self._increment_synthesis_progress(synthesis_job_id, 'failed')
        elif status == 'skipped':
            query = """
                UPDATE synthesis_items
                SET status = ?, error_message = ?, completed_at = ?
                WHERE synthesis_job_id = ? AND ticker = ?
            """
            self._execute_with_retry(query, (status, error_message, now, synthesis_job_id, ticker))
            self._increment_synthesis_progress(synthesis_job_id, 'skipped')

    def _increment_synthesis_progress(self, synthesis_job_id: str, count_type: str) -> None:
        """Increment completed, failed, or skipped count for synthesis job."""
        column_map = {
            'completed': 'completed_companies',
            'failed': 'failed_companies',
            'skipped': 'skipped_companies'
        }
        column = column_map.get(count_type, 'completed_companies')
        query = f"""
            UPDATE synthesis_jobs
            SET {column} = {column} + 1, last_checkpoint_at = ?
            WHERE synthesis_job_id = ?
        """
        self._execute_with_retry(query, (datetime.utcnow().isoformat(), synthesis_job_id))

    def get_synthesis_job(self, synthesis_job_id: str) -> Optional[Dict[str, Any]]:
        """Get synthesis job details."""
        query = "SELECT * FROM synthesis_jobs WHERE synthesis_job_id = ?"
        return self._execute_with_retry(query, (synthesis_job_id,), fetch_one=True)

    def get_incomplete_synthesis_jobs(self, batch_id: str) -> List[Dict[str, Any]]:
        """
        Get incomplete synthesis jobs for a batch (for resume detection).

        Args:
            batch_id: Batch ID to check

        Returns:
            List of incomplete synthesis job dicts
        """
        query = """
            SELECT * FROM synthesis_jobs
            WHERE batch_id = ? AND status IN ('running', 'paused', 'failed')
            ORDER BY created_at DESC
        """
        return self._execute_with_retry(query, (batch_id,), fetch_all=True) or []

    def get_pending_synthesis_items(self, synthesis_job_id: str) -> List[Dict[str, Any]]:
        """
        Get items that haven't been synthesized yet (for resume).

        Args:
            synthesis_job_id: Synthesis job ID

        Returns:
            List of pending synthesis item dicts
        """
        query = """
            SELECT * FROM synthesis_items
            WHERE synthesis_job_id = ? AND status IN ('pending', 'running')
            ORDER BY id
        """
        return self._execute_with_retry(query, (synthesis_job_id,), fetch_all=True) or []

    def get_synthesis_progress(self, synthesis_job_id: str) -> Dict[str, Any]:
        """
        Get synthesis progress summary.

        Args:
            synthesis_job_id: Synthesis job ID

        Returns:
            Progress dict with counts and status
        """
        query = """
            SELECT
                total_companies,
                completed_companies,
                failed_companies,
                skipped_companies,
                (total_companies - completed_companies - failed_companies - skipped_companies) as pending_companies,
                status,
                last_checkpoint_at
            FROM synthesis_jobs
            WHERE synthesis_job_id = ?
        """
        return self._execute_with_retry(query, (synthesis_job_id,), fetch_one=True) or {}

    def get_synthesis_items(self, synthesis_job_id: str) -> List[Dict[str, Any]]:
        """
        Get all synthesis items for a job.

        Args:
            synthesis_job_id: Synthesis job ID

        Returns:
            List of all synthesis item dicts
        """
        query = """
            SELECT * FROM synthesis_items
            WHERE synthesis_job_id = ?
            ORDER BY id
        """
        return self._execute_with_retry(query, (synthesis_job_id,), fetch_all=True) or []

    def link_synthesis_to_batch(self, batch_id: str, synthesis_job_id: str) -> None:
        """Link a synthesis job to a batch."""
        query = """
            UPDATE batch_jobs
            SET last_synthesis_job_id = ?
            WHERE batch_id = ?
        """
        self._execute_with_retry(query, (synthesis_job_id, batch_id))

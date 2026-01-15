#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Resume functionality database operations mixin.
"""

import json
import logging
import sqlite3
from datetime import datetime
from typing import List, Dict, Any


logger = logging.getLogger(__name__)


class ResumeMixin:
    """Mixin for run resumption and interruption handling."""

    def update_last_activity(self, run_id: str) -> None:
        """Update the last activity timestamp for a run."""
        query = """
            UPDATE analysis_runs
            SET last_activity_at = ?
            WHERE run_id = ?
        """
        self._execute_with_retry(query, (datetime.utcnow().isoformat(), run_id))

    def mark_year_completed(self, run_id: str, year: int) -> None:
        """
        Mark a year as completed within a multi-year analysis run.

        Args:
            run_id: Run UUID
            year: The year that was completed
        """
        # Get current completed years
        query = "SELECT completed_years FROM analysis_runs WHERE run_id = ?"
        row = self._execute_with_retry(query, (run_id,), fetch_one=True)

        if row:
            completed = json.loads(row['completed_years']) if row['completed_years'] else []
            if year not in completed:
                completed.append(year)
                completed.sort(reverse=True)

            # Update with new list
            update_query = """
                UPDATE analysis_runs
                SET completed_years = ?, last_activity_at = ?
                WHERE run_id = ?
            """
            self._execute_with_retry(update_query, (
                json.dumps(completed),
                datetime.utcnow().isoformat(),
                run_id
            ))

    def get_completed_years(self, run_id: str) -> List[int]:
        """Get list of years already completed for a run."""
        query = "SELECT completed_years FROM analysis_runs WHERE run_id = ?"
        row = self._execute_with_retry(query, (run_id,), fetch_one=True)

        if row and row['completed_years']:
            return json.loads(row['completed_years'])
        return []

    def get_interrupted_runs(self, stale_minutes: int = 10) -> List[Dict[str, Any]]:
        """
        Get runs that appear to be interrupted (running but no recent activity).

        Args:
            stale_minutes: Consider run stale if no activity for this many minutes

        Returns:
            List of interrupted run details
        """
        query = """
            SELECT
                run_id,
                ticker,
                company_name,
                analysis_type,
                filing_type,
                years_analyzed,
                completed_years,
                started_at,
                last_activity_at,
                progress_message,
                progress_percent,
                current_step,
                total_steps
            FROM analysis_runs
            WHERE status = 'running'
            AND (
                last_activity_at IS NULL
                OR (julianday('now') - julianday(last_activity_at)) * 24 * 60 > ?
            )
            ORDER BY started_at DESC
        """

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(query, (stale_minutes,))

                runs = []
                for row in cursor.fetchall():
                    years_analyzed = json.loads(row['years_analyzed']) if row['years_analyzed'] else []
                    completed_years = json.loads(row['completed_years']) if row['completed_years'] else []
                    remaining_years = [y for y in years_analyzed if y not in completed_years]

                    runs.append({
                        'run_id': row['run_id'],
                        'ticker': row['ticker'],
                        'company_name': row['company_name'],
                        'analysis_type': row['analysis_type'],
                        'filing_type': row['filing_type'],
                        'years_analyzed': years_analyzed,
                        'completed_years': completed_years,
                        'remaining_years': remaining_years,
                        'started_at': row['started_at'],
                        'last_activity_at': row['last_activity_at'],
                        'progress_message': row['progress_message'],
                        'progress_percent': row['progress_percent'] or 0,
                        'current_step': row['current_step'],
                        'total_steps': row['total_steps'] or 0,
                    })

                return runs

        except Exception as e:
            logger.warning(f"Error getting interrupted runs: {e}")
            return []

    def mark_run_as_interrupted(self, run_id: str) -> None:
        """Mark a running run as interrupted (for manual cleanup)."""
        query = """
            UPDATE analysis_runs
            SET status = 'interrupted', error_message = 'Analysis was interrupted and can be resumed'
            WHERE run_id = ? AND status = 'running'
        """
        self._execute_with_retry(query, (run_id,))

    def prepare_for_resume(self, run_id: str) -> bool:
        """
        Prepare a run for resumption by resetting its status.

        Args:
            run_id: Run UUID

        Returns:
            True if run can be resumed, False otherwise
        """
        # Check if run exists and has remaining work
        query = """
            SELECT status, years_analyzed, completed_years
            FROM analysis_runs
            WHERE run_id = ?
        """
        row = self._execute_with_retry(query, (run_id,), fetch_one=True)

        if not row:
            return False

        status = row['status']
        years = json.loads(row['years_analyzed']) if row['years_analyzed'] else []
        completed = json.loads(row['completed_years']) if row['completed_years'] else []

        # Only resume if there's remaining work
        remaining = [y for y in years if y not in completed]
        if not remaining:
            return False

        # Reset status to running
        if status in ('interrupted', 'failed', 'running'):
            update_query = """
                UPDATE analysis_runs
                SET status = 'running',
                    error_message = NULL,
                    last_activity_at = ?
                WHERE run_id = ?
            """
            self._execute_with_retry(update_query, (datetime.utcnow().isoformat(), run_id))
            return True

        return False

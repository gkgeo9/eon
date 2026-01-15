#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Analysis runs database operations mixin.
"""

import json
from datetime import datetime, date
from typing import Optional, List, Dict, Any

import pandas as pd


class AnalysisRunsMixin:
    """Mixin for analysis runs CRUD operations."""

    def create_analysis_run(
        self,
        run_id: str,
        ticker: str,
        analysis_type: str,
        filing_type: str,
        years: List[int],
        config: Dict[str, Any],
        company_name: Optional[str] = None
    ) -> None:
        """
        Create new analysis run record.

        Args:
            run_id: Unique UUID for this run
            ticker: Company ticker symbol
            analysis_type: Type of analysis (fundamental, buffett, etc.)
            filing_type: Filing type (10-K, 10-Q, etc.)
            years: List of years to analyze
            config: Analysis configuration as dict
            company_name: Optional company name
        """
        query = """
            INSERT INTO analysis_runs
            (run_id, ticker, company_name, analysis_type, filing_type, years_analyzed, config_json, started_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        self._execute_with_retry(query, (
            run_id,
            ticker.upper(),
            company_name,
            analysis_type,
            filing_type,
            json.dumps(years),
            json.dumps(config),
            datetime.utcnow().isoformat()
        ))

    def update_run_status(
        self,
        run_id: str,
        status: str,
        error_message: Optional[str] = None
    ) -> None:
        """
        Update analysis run status.

        Args:
            run_id: Run UUID
            status: New status (pending, running, completed, failed)
            error_message: Optional error message if failed
        """
        now = datetime.utcnow().isoformat()
        if status == 'completed':
            query = """
                UPDATE analysis_runs
                SET status = ?, completed_at = ?, error_message = ?, last_activity_at = ?
                WHERE run_id = ?
            """
            self._execute_with_retry(query, (status, now, error_message, now, run_id))
        elif status == 'running':
            query = """
                UPDATE analysis_runs
                SET status = ?, error_message = ?, last_activity_at = ?
                WHERE run_id = ?
            """
            self._execute_with_retry(query, (status, error_message, now, run_id))
        else:
            query = """
                UPDATE analysis_runs
                SET status = ?, error_message = ?
                WHERE run_id = ?
            """
            self._execute_with_retry(query, (status, error_message, run_id))

    def update_run_progress(
        self,
        run_id: str,
        progress_message: str,
        progress_percent: Optional[int] = None,
        current_step: Optional[str] = None,
        total_steps: Optional[int] = None
    ) -> None:
        """
        Update progress tracking for an analysis run.

        Args:
            run_id: Run UUID
            progress_message: Human-readable progress message
            progress_percent: Optional progress percentage (0-100)
            current_step: Optional current step description
            total_steps: Optional total number of steps
        """
        query = """
            UPDATE analysis_runs
            SET progress_message = ?,
                progress_percent = ?,
                current_step = ?,
                total_steps = ?,
                last_activity_at = ?
            WHERE run_id = ?
        """
        self._execute_with_retry(query, (
            progress_message,
            progress_percent,
            current_step,
            total_steps,
            datetime.utcnow().isoformat(),
            run_id
        ))

    def get_run_status(self, run_id: str) -> Optional[str]:
        """Get status of an analysis run."""
        query = "SELECT status FROM analysis_runs WHERE run_id = ?"
        row = self._execute_with_retry(query, (run_id,), fetch_one=True)
        return row['status'] if row else None

    def get_run_details(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get full details of an analysis run."""
        query = "SELECT * FROM analysis_runs WHERE run_id = ?"
        row = self._execute_with_retry(query, (run_id,), fetch_one=True)
        return row if row else None

    def get_recent_analyses(self, limit: int = 10) -> pd.DataFrame:
        """
        Get recent analyses as DataFrame.

        Args:
            limit: Maximum number of results

        Returns:
            DataFrame with recent analyses
        """
        query = """
            SELECT
                ticker,
                analysis_type,
                filing_type,
                status,
                started_at,
                completed_at,
                created_at,
                run_id
            FROM analysis_runs
            ORDER BY started_at DESC
            LIMIT ?
        """
        return self._read_dataframe_with_retry(query, params=(limit,))

    def search_analyses(
        self,
        ticker: Optional[str] = None,
        analysis_type: Optional[str] = None,
        status: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        limit: int = 100
    ) -> pd.DataFrame:
        """
        Search analyses with filters.

        Args:
            ticker: Filter by ticker
            analysis_type: Filter by analysis type
            status: Filter by status
            date_from: Filter by start date
            date_to: Filter by end date
            limit: Maximum results

        Returns:
            DataFrame with filtered analyses
        """
        conditions = []
        params = []

        if ticker:
            conditions.append("ticker = ?")
            params.append(ticker.upper())

        if analysis_type:
            conditions.append("analysis_type = ?")
            params.append(analysis_type)

        if status:
            conditions.append("status = ?")
            params.append(status)

        if date_from:
            conditions.append("DATE(created_at) >= ?")
            params.append(date_from.isoformat())

        if date_to:
            conditions.append("DATE(created_at) <= ?")
            params.append(date_to.isoformat())

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        query = f"""
            SELECT *
            FROM analysis_runs
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT ?
        """
        params.append(limit)

        return self._read_dataframe_with_retry(query, params=tuple(params))

    def delete_analysis_run(self, run_id: str) -> None:
        """Delete an analysis run and all its results."""
        query = "DELETE FROM analysis_runs WHERE run_id = ?"
        self._execute_with_retry(query, (run_id,))

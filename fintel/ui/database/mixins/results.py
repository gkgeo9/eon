#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Analysis results database operations mixin.
"""

import json
import logging
import sqlite3
from typing import Optional, List, Dict, Any


logger = logging.getLogger(__name__)


class AnalysisResultsMixin:
    """Mixin for analysis results storage and retrieval."""

    def store_result(
        self,
        run_id: str,
        ticker: str,
        fiscal_year: int,
        filing_type: str,
        result_type: str,
        result_data: Dict[str, Any]
    ) -> None:
        """
        Store analysis result.

        Args:
            run_id: Run UUID
            ticker: Company ticker
            fiscal_year: Fiscal year
            filing_type: Filing type
            result_type: Pydantic model class name
            result_data: Result as dictionary (from model_dump())
        """
        query = """
            INSERT INTO analysis_results
            (run_id, ticker, fiscal_year, filing_type, result_type, result_json)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        self._execute_with_retry(query, (
            run_id,
            ticker.upper(),
            fiscal_year,
            filing_type,
            result_type,
            json.dumps(result_data)
        ))

    def get_analysis_results(self, run_id: str) -> List[Dict[str, Any]]:
        """
        Get all results for a run.

        Args:
            run_id: Run UUID

        Returns:
            List of result dictionaries
        """
        query = """
            SELECT fiscal_year, result_type, result_json
            FROM analysis_results
            WHERE run_id = ?
            ORDER BY fiscal_year DESC
        """
        rows = self._execute_with_retry(query, (run_id,), fetch_all=True)

        results = []
        for row in rows:
            results.append({
                'year': row['fiscal_year'],
                'type': row['result_type'],
                'data': json.loads(row['result_json'])
            })
        return results

    def get_existing_results(
        self,
        ticker: str,
        analysis_type: str,
        years: List[int],
        filing_type: str = "10-K",
        max_age_days: int = 30
    ) -> Dict[int, Dict[str, Any]]:
        """
        Check for existing completed results for specific years.

        Used for caching - skip re-analyzing years we already have recent results for.

        Args:
            ticker: Company ticker
            analysis_type: Type of analysis
            years: List of years to check
            filing_type: Filing type
            max_age_days: Maximum age of cached results in days

        Returns:
            Dictionary mapping year to result data for years with existing results
        """
        if not years:
            return {}

        placeholders = ",".join("?" * len(years))
        query = f"""
            SELECT
                r.fiscal_year,
                r.result_type,
                r.result_json,
                ar.completed_at
            FROM analysis_results r
            JOIN analysis_runs ar ON r.run_id = ar.run_id
            WHERE
                ar.ticker = ?
                AND ar.analysis_type = ?
                AND ar.filing_type = ?
                AND ar.status = 'completed'
                AND r.fiscal_year IN ({placeholders})
                AND julianday('now') - julianday(ar.completed_at) <= ?
            ORDER BY ar.completed_at DESC
        """

        params = [ticker.upper(), analysis_type, filing_type] + years + [max_age_days]

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(query, params)

                # Get most recent result per year
                results = {}
                for row in cursor.fetchall():
                    year = row['fiscal_year']
                    if year not in results:  # Keep first (most recent) result
                        results[year] = {
                            'year': year,
                            'type': row['result_type'],
                            'data': json.loads(row['result_json']),
                            'cached_at': row['completed_at']
                        }

                return results
        except Exception as e:
            logger.warning(f"Error checking for existing results: {e}")
            return {}

    def get_latest_result_for_ticker(
        self,
        ticker: str,
        analysis_type: str
    ) -> Optional[Dict[str, Any]]:
        """Get the most recent completed analysis for a ticker."""
        query = """
            SELECT ar.run_id, ar.completed_at
            FROM analysis_runs ar
            WHERE ar.ticker = ? AND ar.analysis_type = ? AND ar.status = 'completed'
            ORDER BY ar.completed_at DESC
            LIMIT 1
        """
        row = self._execute_with_retry(query, (ticker.upper(), analysis_type), fetch_one=True)

        if row:
            run_id = row['run_id']
            return {
                'run_id': run_id,
                'completed_at': row['completed_at'],
                'results': self.get_analysis_results(run_id)
            }
        return None

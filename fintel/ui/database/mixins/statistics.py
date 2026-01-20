#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Statistics database operations mixin.
"""

import pandas as pd


class StatisticsMixin:
    """Mixin for statistics and metrics queries."""

    def get_total_analyses(self) -> int:
        """Get total number of analyses."""
        query = "SELECT COUNT(*) as cnt FROM analysis_runs"
        row = self._execute_with_retry(query, fetch_one=True)
        return row['cnt'] if row else 0

    def get_running_analyses_count(self) -> int:
        """Get number of currently running analyses."""
        query = "SELECT COUNT(*) as cnt FROM analysis_runs WHERE status = 'running'"
        row = self._execute_with_retry(query, fetch_one=True)
        return row['cnt'] if row else 0

    def get_analyses_today(self) -> int:
        """Get number of analyses created today."""
        query = "SELECT COUNT(*) as cnt FROM analysis_runs WHERE DATE(created_at) = DATE('now')"
        row = self._execute_with_retry(query, fetch_one=True)
        return row['cnt'] if row else 0

    def get_unique_tickers_count(self) -> int:
        """Get number of unique tickers analyzed."""
        query = "SELECT COUNT(DISTINCT ticker) as cnt FROM analysis_runs WHERE status = 'completed'"
        row = self._execute_with_retry(query, fetch_one=True)
        return row['cnt'] if row else 0

    def get_stats_by_type(self) -> pd.DataFrame:
        """Get analysis statistics by type."""
        query = """
            SELECT
                analysis_type,
                status,
                COUNT(*) as count
            FROM analysis_runs
            GROUP BY analysis_type, status
        """
        return self._read_dataframe_with_retry(query)

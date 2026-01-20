#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
API usage tracking database operations mixin.
"""

from datetime import datetime

import pandas as pd

from fintel.core import mask_api_key


class APIUsageMixin:
    """Mixin for API usage tracking operations."""

    def record_api_usage(self, api_key: str, count: int = 1) -> None:
        """
        Record API usage for a key.

        Args:
            api_key: The API key (will be masked to last 4 chars)
            count: Number of requests to record (default: 1)
        """
        masked_key = mask_api_key(api_key)
        today = datetime.utcnow().strftime('%Y-%m-%d')

        query = """
            INSERT INTO api_usage (api_key_suffix, usage_date, request_count, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(api_key_suffix, usage_date) DO UPDATE SET
                request_count = request_count + ?,
                updated_at = CURRENT_TIMESTAMP
        """
        self._execute_with_retry(query, (masked_key, today, count, count))

    def get_api_usage_today(self, api_key: str = None) -> int:
        """
        Get API usage count for today.

        Args:
            api_key: Optional specific key (masked to last 4 chars). If None, returns total.

        Returns:
            Number of API calls today
        """
        today = datetime.utcnow().strftime('%Y-%m-%d')

        if api_key:
            masked_key = mask_api_key(api_key)
            query = "SELECT request_count FROM api_usage WHERE api_key_suffix = ? AND usage_date = ?"
            row = self._execute_with_retry(query, (masked_key, today), fetch_one=True)
            return row['request_count'] if row else 0
        else:
            query = "SELECT SUM(request_count) as total FROM api_usage WHERE usage_date = ?"
            row = self._execute_with_retry(query, (today,), fetch_one=True)
            return row['total'] if row and row['total'] else 0

    def get_api_usage_history(self, days: int = 30) -> pd.DataFrame:
        """
        Get API usage history.

        Args:
            days: Number of days to look back (default: 30)

        Returns:
            DataFrame with columns: api_key_suffix, usage_date, request_count
        """
        query = """
            SELECT api_key_suffix, usage_date, request_count
            FROM api_usage
            WHERE usage_date >= DATE('now', ?)
            ORDER BY usage_date DESC, api_key_suffix
        """
        return self._read_dataframe_with_retry(query, params=(f'-{days} days',))

    def get_api_usage_summary(self) -> pd.DataFrame:
        """
        Get API usage summary by key.

        Returns:
            DataFrame with columns: api_key_suffix, total_requests, first_used, last_used
        """
        query = """
            SELECT
                api_key_suffix,
                SUM(request_count) as total_requests,
                MIN(usage_date) as first_used,
                MAX(usage_date) as last_used,
                COUNT(DISTINCT usage_date) as days_active
            FROM api_usage
            GROUP BY api_key_suffix
            ORDER BY total_requests DESC
        """
        return self._read_dataframe_with_retry(query)

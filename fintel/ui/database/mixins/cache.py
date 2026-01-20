#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
File cache database operations mixin.
"""

import json
from datetime import datetime
from typing import Optional, List


class FileCacheMixin:
    """Mixin for file cache and filing types cache operations."""

    def cache_file(
        self,
        ticker: str,
        fiscal_year: int,
        filing_type: str,
        file_path: str,
        file_hash: Optional[str] = None,
        filing_date: Optional[str] = None
    ) -> None:
        """
        Cache downloaded file information.

        Args:
            ticker: Company ticker symbol
            fiscal_year: Fiscal year of the filing
            filing_type: Type of filing (10-K, 10-Q, 8-K, etc.)
            file_path: Path to the cached file
            file_hash: Optional SHA256 hash for integrity
            filing_date: Optional filing date (YYYY-MM-DD) for unique identification
        """
        query = """
            INSERT OR REPLACE INTO file_cache
            (ticker, fiscal_year, filing_type, file_path, file_hash, filing_date, downloaded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        self._execute_with_retry(query, (
            ticker.upper(),
            fiscal_year,
            filing_type,
            file_path,
            file_hash,
            filing_date,
            datetime.utcnow().isoformat()
        ))

    def get_cached_file(
        self,
        ticker: str,
        fiscal_year: int,
        filing_type: str
    ) -> Optional[str]:
        """Get cached file path if exists."""
        query = """
            SELECT file_path
            FROM file_cache
            WHERE ticker = ? AND fiscal_year = ? AND filing_type = ?
        """
        row = self._execute_with_retry(query, (ticker.upper(), fiscal_year, filing_type), fetch_one=True)
        return row['file_path'] if row else None

    def get_cached_file_by_date(
        self,
        ticker: str,
        filing_date: str,
        filing_type: str
    ) -> Optional[str]:
        """
        Get cached file path by filing_date.

        This is useful for event-based filings (8-K, 4, etc.) where multiple
        filings can exist in the same year.

        Args:
            ticker: Company ticker symbol
            filing_date: Filing date in YYYY-MM-DD format
            filing_type: Type of filing

        Returns:
            File path if cached, None otherwise
        """
        query = """
            SELECT file_path
            FROM file_cache
            WHERE ticker = ? AND filing_date = ? AND filing_type = ?
        """
        row = self._execute_with_retry(query, (ticker.upper(), filing_date, filing_type), fetch_one=True)
        return row['file_path'] if row else None

    def clear_file_cache(self, older_than_days: Optional[int] = None) -> int:
        """
        Clear file cache.

        Args:
            older_than_days: Clear files older than this many days (None = all)

        Returns:
            Number of records deleted
        """
        if older_than_days:
            query = """
                DELETE FROM file_cache
                WHERE julianday('now') - julianday(downloaded_at) > ?
            """
            return self._execute_with_retry(query, (older_than_days,))
        else:
            query = "DELETE FROM file_cache"
            return self._execute_with_retry(query)

    def get_cache_count(self) -> int:
        """
        Get count of cached files.

        Returns:
            Number of cached files in the database
        """
        query = "SELECT COUNT(*) as cnt FROM file_cache"
        row = self._execute_with_retry(query, fetch_one=True)
        return row['cnt'] if row else 0

    def cache_filing_types(self, ticker: str, filing_types: List[str]) -> None:
        """
        Cache available filing types for a ticker.

        Args:
            ticker: Company ticker symbol
            filing_types: List of available filing types
        """
        query = """
            INSERT OR REPLACE INTO filing_types_cache
            (ticker, filing_types, cached_at)
            VALUES (?, ?, ?)
        """
        self._execute_with_retry(query, (
            ticker.upper(),
            json.dumps(filing_types),
            datetime.utcnow().isoformat()
        ))

    def get_cached_filing_types(
        self,
        ticker: str,
        max_age_hours: int = 24
    ) -> Optional[List[str]]:
        """
        Get cached filing types for a ticker if cache is fresh.

        Args:
            ticker: Company ticker symbol
            max_age_hours: Maximum cache age in hours (default: 24)

        Returns:
            List of filing types if cache exists and is fresh, None otherwise
        """
        query = """
            SELECT filing_types, cached_at
            FROM filing_types_cache
            WHERE ticker = ?
        """
        row = self._execute_with_retry(query, (ticker.upper(),), fetch_one=True)

        if not row:
            return None

        filing_types_json, cached_at_str = row['filing_types'], row['cached_at']

        # Check if cache is still fresh
        cached_at = datetime.fromisoformat(cached_at_str)
        age_hours = (datetime.utcnow() - cached_at).total_seconds() / 3600

        if age_hours > max_age_hours:
            return None

        return json.loads(filing_types_json)

    def clear_filing_types_cache(self, ticker: Optional[str] = None) -> int:
        """
        Clear filing types cache.

        Args:
            ticker: Clear cache for specific ticker (None = all)

        Returns:
            Number of records deleted
        """
        if ticker:
            query = "DELETE FROM filing_types_cache WHERE ticker = ?"
            return self._execute_with_retry(query, (ticker.upper(),))
        else:
            query = "DELETE FROM filing_types_cache"
            return self._execute_with_retry(query)

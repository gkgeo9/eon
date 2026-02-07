#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
File cache database operations mixin.
"""

import json
from datetime import datetime
from typing import Optional, List, Dict, Any


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

    def get_latest_cached_filing_date(
        self,
        ticker: str,
        filing_type: str
    ) -> Optional[str]:
        """
        Get the most recent filing_date in cache for a ticker/filing_type.

        Args:
            ticker: Company ticker symbol
            filing_type: Type of filing (10-K, 10-Q, etc.)

        Returns:
            Filing date in YYYY-MM-DD format, or None if no cached files
        """
        query = """
            SELECT MAX(filing_date) as latest_date
            FROM file_cache
            WHERE ticker = ? AND filing_type = ? AND filing_date IS NOT NULL
        """
        row = self._execute_with_retry(query, (ticker.upper(), filing_type), fetch_one=True)
        return row['latest_date'] if row and row['latest_date'] else None

    def get_all_cached_filings(
        self,
        ticker: str,
        filing_type: str
    ) -> List[Dict]:
        """
        Get all cached filings for a ticker/filing_type.

        Args:
            ticker: Company ticker symbol
            filing_type: Type of filing (10-K, 10-Q, etc.)

        Returns:
            List of dicts with fiscal_year, filing_date, file_path, file_hash, downloaded_at
        """
        query = """
            SELECT fiscal_year, filing_date, file_path, file_hash, downloaded_at
            FROM file_cache
            WHERE ticker = ? AND filing_type = ?
            ORDER BY filing_date DESC NULLS LAST, fiscal_year DESC
        """
        return self._execute_with_retry(query, (ticker.upper(), filing_type), fetch_all=True)

    def is_filing_cached(
        self,
        ticker: str,
        filing_date: str,
        filing_type: str
    ) -> bool:
        """
        Check if a specific filing (by date) is already cached.

        Args:
            ticker: Company ticker symbol
            filing_date: Filing date in YYYY-MM-DD format
            filing_type: Type of filing

        Returns:
            True if filing is cached, False otherwise
        """
        query = """
            SELECT 1 FROM file_cache
            WHERE ticker = ? AND filing_date = ? AND filing_type = ?
            LIMIT 1
        """
        row = self._execute_with_retry(query, (ticker.upper(), filing_date, filing_type), fetch_one=True)
        return row is not None

    def clear_file_cache_entry(
        self,
        ticker: str,
        fiscal_year: int,
        filing_type: str
    ) -> int:
        """
        Remove a single cache entry.

        Useful for removing stale entries when the actual file is missing.

        Args:
            ticker: Company ticker symbol
            fiscal_year: Fiscal year of the filing
            filing_type: Type of filing

        Returns:
            Number of records deleted (0 or 1)
        """
        query = """
            DELETE FROM file_cache
            WHERE ticker = ? AND fiscal_year = ? AND filing_type = ?
        """
        return self._execute_with_retry(query, (ticker.upper(), fiscal_year, filing_type))

    def get_tickers_with_cached_files(self, filing_type: str) -> List[str]:
        """
        Get list of tickers that have cached files for a filing type.

        Args:
            filing_type: Type of filing (10-K, 10-Q, etc.)

        Returns:
            List of ticker symbols with cached files
        """
        query = """
            SELECT DISTINCT ticker FROM file_cache
            WHERE filing_type = ? AND file_path IS NOT NULL
            ORDER BY ticker
        """
        rows = self._execute_with_retry(query, (filing_type,), fetch_all=True)
        return [row['ticker'] for row in rows]

    def scan_and_cache_existing_pdfs(
        self,
        pdf_directory: str,
        filing_type: str = "10-K"
    ) -> Dict[str, int]:
        """
        Scan existing PDF files and populate the cache.

        This is useful for populating the cache with files that were downloaded
        before caching was implemented, or after a cache reset.

        Expected filename format: {TICKER}_{FILING_TYPE}_{FILING_DATE}.pdf
        Example: AAPL_10-K_2024-02-02.pdf

        Args:
            pdf_directory: Directory containing ticker subdirectories with PDFs
            filing_type: Filing type to scan for (default: 10-K)

        Returns:
            Dict with 'scanned', 'cached', 'skipped' counts
        """
        from pathlib import Path
        import re

        results = {'scanned': 0, 'cached': 0, 'skipped': 0, 'errors': 0}
        pdf_dir = Path(pdf_directory)

        if not pdf_dir.exists():
            return results

        # Pattern: TICKER_FILING-TYPE_YYYY-MM-DD.pdf
        # Handle filing types with slashes converted to underscores
        safe_filing_type = filing_type.replace("/", "_").replace(" ", "_")
        pattern = re.compile(
            rf'^([A-Z0-9]+)_{re.escape(safe_filing_type)}_(\d{{4}}-\d{{2}}-\d{{2}})\.pdf$',
            re.IGNORECASE
        )

        # Scan all ticker subdirectories
        for ticker_dir in pdf_dir.iterdir():
            if not ticker_dir.is_dir():
                continue

            ticker = ticker_dir.name.upper()

            for pdf_file in ticker_dir.glob("*.pdf"):
                results['scanned'] += 1

                # Parse filename
                match = pattern.match(pdf_file.name)
                if not match:
                    results['skipped'] += 1
                    continue

                file_ticker = match.group(1).upper()
                filing_date = match.group(2)

                if file_ticker != ticker:
                    results['skipped'] += 1
                    continue

                # Derive fiscal_year from filing_date
                # For annual filings (10-K) filed in Jan-Apr, fiscal year is previous year
                try:
                    year = int(filing_date[:4])
                    month = int(filing_date[5:7])

                    if filing_type.upper() in ('10-K', '10-K/A', '20-F', '40-F'):
                        # Annual filing: if filed Jan-Apr, it's for previous fiscal year
                        if month <= 4:
                            fiscal_year = year - 1
                        else:
                            fiscal_year = year
                    else:
                        # Quarterly or other: fiscal year matches filing year
                        fiscal_year = year

                    # Check if already cached
                    existing = self.get_cached_file(ticker, fiscal_year, filing_type)
                    if existing:
                        results['skipped'] += 1
                        continue

                    # Cache the file
                    self.cache_file(
                        ticker=ticker,
                        fiscal_year=fiscal_year,
                        filing_type=filing_type,
                        file_path=str(pdf_file),
                        filing_date=filing_date
                    )
                    results['cached'] += 1

                except Exception as e:
                    results['errors'] += 1

        return results

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

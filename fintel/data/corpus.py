#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Corpus management for SEC filings.

Provides intelligent caching and freshness detection for SEC documents.
"""

from pathlib import Path
from typing import List, Dict, Optional, Tuple, TYPE_CHECKING
from datetime import datetime, timedelta

from fintel.core import get_logger, get_config

if TYPE_CHECKING:
    from fintel.data.sources.sec import SECDownloader


class CorpusManager:
    """
    Manages a corpus of SEC filings with intelligent caching.

    Features:
    - Checks if documents already exist as PDFs
    - Detects new filings since last cache
    - Uses cached PDFs instead of re-downloading

    Example:
        corpus = CorpusManager(db, downloader)

        # Check what's new
        new_filings = corpus.check_for_new_filings("AAPL", "10-K")

        # Get corpus status
        status = corpus.get_corpus_status("AAPL", "10-K")

        # Get filings (uses cache when possible)
        pdfs, new_metadata = corpus.get_filings_smart("AAPL", "10-K", num_filings=5)
    """

    def __init__(self, db, downloader: Optional["SECDownloader"] = None):
        """
        Initialize corpus manager.

        Args:
            db: Database repository with FileCacheMixin
            downloader: SEC downloader instance (creates default if not provided)
        """
        self.db = db
        self._downloader = downloader
        self.config = get_config()
        self.logger = get_logger(f"{__name__}.CorpusManager")

    @property
    def downloader(self) -> "SECDownloader":
        """Lazy-load downloader to avoid circular imports."""
        if self._downloader is None:
            from fintel.data.sources.sec import SECDownloader
            self._downloader = SECDownloader()
        return self._downloader

    def check_for_new_filings(
        self,
        ticker: str,
        filing_type: str,
        limit: int = 10
    ) -> List[Dict]:
        """
        Check if new filings have been released since last cache.

        Args:
            ticker: Company ticker symbol
            filing_type: Filing type (10-K, 10-Q, etc.)
            limit: Max filings to check from SEC

        Returns:
            List of new filings not in cache (with metadata)
        """
        ticker = ticker.upper()

        # Get latest cached filing date
        latest_cached = self.db.get_latest_cached_filing_date(ticker, filing_type)
        self.logger.info(
            f"Latest cached {filing_type} for {ticker}: "
            f"{latest_cached or 'None (no cache)'}"
        )

        # Query SEC for available filings
        try:
            available = self.downloader.get_available_filings(ticker, filing_type, limit=limit)
        except Exception as e:
            self.logger.error(f"Failed to check SEC for {ticker}: {e}")
            return []

        # Find filings not in cache
        new_filings = []
        for filing in available:
            filing_date = filing.get('filing_date')

            if not filing_date:
                continue

            # Check if this specific filing is cached
            if not self.db.is_filing_cached(ticker, filing_date, filing_type):
                # Also check if it's newer than our latest (extra validation)
                if latest_cached is None or filing_date > latest_cached:
                    new_filings.append(filing)
                    self.logger.info(
                        f"New filing found: {ticker} {filing_type} "
                        f"dated {filing_date}"
                    )

        return new_filings

    def get_corpus_status(
        self,
        ticker: str,
        filing_type: str
    ) -> Dict:
        """
        Get comprehensive status of cached corpus for a ticker.

        Args:
            ticker: Company ticker symbol
            filing_type: Filing type (10-K, 10-Q, etc.)

        Returns:
            Dict with:
            - ticker: The ticker symbol
            - filing_type: The filing type
            - cached_count: Number of filings in cache
            - cached_filings: List of cached filing info
            - latest_cached_date: Most recent filing date in cache
            - needs_refresh: Boolean indicating if refresh recommended (>7 days)
        """
        ticker = ticker.upper()

        cached_filings = self.db.get_all_cached_filings(ticker, filing_type)
        latest_cached = self.db.get_latest_cached_filing_date(ticker, filing_type)

        # Determine if refresh is needed (cache older than 7 days)
        needs_refresh = True
        if cached_filings:
            latest_download = max(
                (f.get('downloaded_at') or '' for f in cached_filings),
                default=''
            )
            if latest_download:
                try:
                    # Handle various ISO format variations
                    download_str = latest_download.replace('Z', '+00:00')
                    if '+' not in download_str and 'T' in download_str:
                        download_date = datetime.fromisoformat(download_str)
                    else:
                        download_date = datetime.fromisoformat(download_str)
                    needs_refresh = (datetime.utcnow() - download_date.replace(tzinfo=None)) > timedelta(days=7)
                except Exception as e:
                    self.logger.warning(f"Could not parse download date: {e}")
                    needs_refresh = True

        return {
            'ticker': ticker,
            'filing_type': filing_type,
            'cached_count': len(cached_filings),
            'cached_filings': cached_filings,
            'latest_cached_date': latest_cached,
            'needs_refresh': needs_refresh
        }

    def get_filings_smart(
        self,
        ticker: str,
        filing_type: str,
        years: Optional[List[int]] = None,
        num_filings: int = 5,
        force_refresh: bool = False
    ) -> Tuple[Dict[int, Path], List[Dict]]:
        """
        Get filings using cache intelligently.

        Strategy:
        1. Check what's already cached
        2. Verify cached files still exist on disk
        3. Return cached files without downloading

        Note: This method only returns cached files. For downloading new files,
        use the analysis_service._get_or_download_filings() method.

        Args:
            ticker: Company ticker
            filing_type: Filing type
            years: Specific years to get (optional)
            num_filings: Number of filings to get
            force_refresh: Force re-download even if cached

        Returns:
            Tuple of:
            - Dict mapping year to Path for available cached files
            - List of years that are NOT cached (would need download)
        """
        ticker = ticker.upper()
        pdf_paths: Dict[int, Path] = {}
        years_not_cached: List[int] = []

        if force_refresh:
            # Return empty - all years need download
            return pdf_paths, years if years else list(range(2020, 2026))

        # Check cache
        cached = self.db.get_all_cached_filings(ticker, filing_type)

        for cache_entry in cached:
            file_path = Path(cache_entry['file_path'])
            year = cache_entry['fiscal_year']

            # Skip if not in requested years
            if years and year not in years:
                continue

            # Verify file still exists
            if file_path.exists():
                pdf_paths[year] = file_path
                self.logger.debug(f"Using cached: {ticker} {year} at {file_path}")
            else:
                # File was deleted, log warning
                self.logger.warning(f"Cached file missing: {file_path}")
                years_not_cached.append(year)

        # Determine what's missing
        if years:
            for year in years:
                if year not in pdf_paths and year not in years_not_cached:
                    years_not_cached.append(year)
        else:
            # If no specific years requested, just return what we have
            pass

        return pdf_paths, years_not_cached

    def verify_cache_integrity(
        self,
        ticker: str,
        filing_type: str,
        remove_stale: bool = False
    ) -> Dict:
        """
        Verify that all cached files actually exist on disk.

        Args:
            ticker: Company ticker symbol
            filing_type: Filing type
            remove_stale: If True, remove cache entries for missing files

        Returns:
            Dict with:
            - valid_count: Number of valid cache entries
            - stale_count: Number of stale entries (file missing)
            - stale_entries: List of stale cache entries
        """
        ticker = ticker.upper()
        cached = self.db.get_all_cached_filings(ticker, filing_type)

        valid_count = 0
        stale_entries = []

        for entry in cached:
            file_path = Path(entry['file_path'])
            if file_path.exists():
                valid_count += 1
            else:
                stale_entries.append(entry)
                if remove_stale:
                    self.db.clear_file_cache_entry(
                        ticker,
                        entry['fiscal_year'],
                        filing_type
                    )
                    self.logger.info(
                        f"Removed stale cache entry: {ticker} {entry['fiscal_year']}"
                    )

        return {
            'valid_count': valid_count,
            'stale_count': len(stale_entries),
            'stale_entries': stale_entries
        }

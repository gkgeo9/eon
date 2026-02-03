#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
End-to-end tests for running analysis using cached PDFs.

Tests that the caching system works correctly and prevents unnecessary
SEC downloads when PDFs already exist in the cache.

These tests use the real database and real cached files (like COIN's 10-Ks)
but mock the Gemini API to avoid actual AI calls.
"""

import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestCachedPDFAnalysis:
    """
    Integration tests that verify analysis can run using only cached PDFs.

    These tests:
    1. Dynamically discover cached PDFs from the database
    2. Track SEC download calls to verify they don't happen
    3. Run analysis with mocked AI to verify the flow works
    """

    @pytest.fixture
    def real_db(self):
        """
        Connect to the real Fintel database with cached files.

        Note: This uses the actual data/fintel.db with real cached PDFs.
        """
        from fintel.ui.database import DatabaseRepository
        from fintel.core import get_config

        config = get_config()
        db_path = config.get_data_path() / "fintel.db"

        if not db_path.exists():
            pytest.skip("Real database not found - run with actual data directory")

        db = DatabaseRepository(str(db_path))
        yield db

    @pytest.fixture
    def analysis_service_with_tracking(self, real_db):
        """
        Create AnalysisService with download tracking.

        Returns the service along with a tracker for download calls.
        """
        from fintel.ui.services.analysis_service import AnalysisService

        service = AnalysisService(real_db)

        # Track download calls
        download_calls = []
        original_download = service.downloader.download_with_metadata

        def track_downloads(*args, **kwargs):
            download_calls.append({'args': args, 'kwargs': kwargs})
            return original_download(*args, **kwargs)

        service.downloader.download_with_metadata = track_downloads

        return service, download_calls

    @pytest.mark.integration
    def test_discovers_cached_tickers(self, real_db):
        """Test that we can discover tickers with cached files."""
        cached_tickers = real_db.get_tickers_with_cached_files("10-K")

        # Should have at least one ticker with cached 10-Ks
        # (COIN, AAPL, or others from the batch test)
        assert len(cached_tickers) > 0, "No cached 10-K files found"

        print(f"Found {len(cached_tickers)} tickers with cached 10-Ks: {cached_tickers}")

    @pytest.mark.integration
    def test_cached_files_exist_on_disk(self, real_db):
        """Test that cached file paths actually exist on disk."""
        cached_tickers = real_db.get_tickers_with_cached_files("10-K")

        if not cached_tickers:
            pytest.skip("No cached files to test")

        ticker = cached_tickers[0]
        cached_filings = real_db.get_all_cached_filings(ticker, "10-K")

        assert len(cached_filings) > 0, f"No cached filings for {ticker}"

        # Check that files actually exist
        existing_count = 0
        for filing in cached_filings:
            file_path = Path(filing['file_path'])
            if file_path.exists():
                existing_count += 1
                print(f"  Found: {file_path.name}")

        assert existing_count > 0, f"No cached files exist on disk for {ticker}"
        print(f"Ticker {ticker}: {existing_count}/{len(cached_filings)} files exist on disk")

    @pytest.mark.integration
    def test_get_or_download_uses_cache(self, analysis_service_with_tracking, real_db):
        """
        Test that _get_or_download_filings uses cached files without downloading.

        This is the key test: verify that when we request years that are cached,
        no SEC downloads occur.
        """
        service, download_calls = analysis_service_with_tracking

        # Find a ticker with cached files
        cached_tickers = real_db.get_tickers_with_cached_files("10-K")
        if not cached_tickers:
            pytest.skip("No cached files to test")

        ticker = cached_tickers[0]
        cached_filings = real_db.get_all_cached_filings(ticker, "10-K")

        # Filter to only years where files actually exist
        available_years = []
        for filing in cached_filings:
            if Path(filing['file_path']).exists():
                available_years.append(filing['fiscal_year'])

        if not available_years:
            pytest.skip(f"No cached files exist on disk for {ticker}")

        print(f"Testing {ticker} with cached years: {available_years}")

        # Create a test run ID
        run_id = str(uuid.uuid4())
        real_db.create_analysis_run(
            run_id=run_id,
            ticker=ticker,
            analysis_type="perspective",
            filing_type="10-K",
            years=available_years[:2],
            config={}
        )

        try:
            # Request filings for years we know are cached
            pdf_paths = service._get_or_download_filings(
                ticker=ticker,
                filing_type="10-K",
                years=available_years[:2],  # Test with first 2 cached years
                run_id=run_id
            )

            # Verify we got PDF paths
            assert len(pdf_paths) > 0, "No PDF paths returned"

            # CRITICAL: Verify NO downloads occurred
            assert len(download_calls) == 0, (
                f"Expected 0 SEC downloads (using cache), but got {len(download_calls)}. "
                f"Download calls: {download_calls}"
            )

            print(f"SUCCESS: Used {len(pdf_paths)} cached PDFs, 0 downloads")

        finally:
            # Clean up test run
            pass  # Run will remain in DB but that's fine for testing

    @pytest.mark.integration
    def test_corpus_manager_uses_cache(self, real_db):
        """Test that CorpusManager correctly identifies cached files."""
        from fintel.data.corpus import CorpusManager

        cached_tickers = real_db.get_tickers_with_cached_files("10-K")
        if not cached_tickers:
            pytest.skip("No cached files to test")

        ticker = cached_tickers[0]

        # Create corpus manager with mocked downloader (to avoid SEC calls)
        mock_downloader = MagicMock()
        corpus = CorpusManager(real_db, mock_downloader)

        # Get status
        status = corpus.get_corpus_status(ticker, "10-K")

        assert status['cached_count'] > 0
        print(f"Corpus status for {ticker}: {status['cached_count']} cached files")
        print(f"Latest cached date: {status['latest_cached_date']}")

        # Get filings smart (should use cache)
        cached_filings = real_db.get_all_cached_filings(ticker, "10-K")
        years = [f['fiscal_year'] for f in cached_filings if Path(f['file_path']).exists()]

        if years:
            pdf_paths, not_cached = corpus.get_filings_smart(ticker, "10-K", years=years[:2])

            assert len(pdf_paths) > 0, "get_filings_smart didn't return cached files"
            assert len(not_cached) == 0, f"Unexpected uncached years: {not_cached}"

            print(f"get_filings_smart returned {len(pdf_paths)} cached PDFs")


class TestAnalysisServiceCacheIntegration:
    """
    Tests for AnalysisService integration with caching system.

    Uses test database with synthetic cached entries.
    """

    @pytest.fixture
    def db_with_cache(self, test_db, temp_dir):
        """Database with pre-populated cache entries and fake PDF files."""
        pdf_dir = temp_dir / "pdfs" / "TEST"
        pdf_dir.mkdir(parents=True)

        # Create fake PDFs for 3 years
        for year, date in [(2022, "2022-02-15"), (2023, "2023-02-14"), (2024, "2024-02-13")]:
            pdf_path = pdf_dir / f"TEST_10-K_{date}.pdf"
            pdf_path.write_text(f"Fake 10-K content for year {year}")

            test_db.cache_file(
                ticker="TEST",
                fiscal_year=year,
                filing_type="10-K",
                file_path=str(pdf_path),
                filing_date=date
            )

        return test_db, pdf_dir

    @pytest.fixture
    def analysis_service(self, db_with_cache):
        """Create AnalysisService with test database."""
        from fintel.ui.services.analysis_service import AnalysisService

        test_db, _ = db_with_cache
        return AnalysisService(test_db)

    @pytest.mark.unit
    def test_get_or_download_uses_cache_no_download(self, analysis_service, db_with_cache):
        """Test that _get_or_download_filings uses cache without downloading."""
        test_db, pdf_dir = db_with_cache

        # Track download calls
        download_calls = []
        original_download = analysis_service.downloader.download_with_metadata

        def track_downloads(*args, **kwargs):
            download_calls.append({'args': args, 'kwargs': kwargs})
            return original_download(*args, **kwargs)

        analysis_service.downloader.download_with_metadata = track_downloads

        # Create run
        import uuid
        run_id = str(uuid.uuid4())
        test_db.create_analysis_run(
            run_id=run_id,
            ticker="TEST",
            analysis_type="perspective",
            filing_type="10-K",
            years=[2023, 2024],
            config={"perspectives": ["buffett"]}
        )

        # Request years that are cached
        pdf_paths = analysis_service._get_or_download_filings(
            ticker="TEST",
            filing_type="10-K",
            years=[2023, 2024],
            run_id=run_id
        )

        # Should have returned both years from cache
        assert 2023 in pdf_paths
        assert 2024 in pdf_paths

        # Should NOT have downloaded anything
        assert len(download_calls) == 0

    @pytest.mark.unit
    def test_stale_cache_triggers_download(self, analysis_service, db_with_cache):
        """Test that stale cache entry (missing file) triggers re-download."""
        test_db, pdf_dir = db_with_cache

        # Delete one of the cached files to make it stale
        stale_pdf = pdf_dir / "TEST_10-K_2022-02-15.pdf"
        stale_pdf.unlink()

        # Track download calls
        download_calls = []
        original_download = analysis_service.downloader.download_with_metadata

        def track_and_fail_downloads(*args, **kwargs):
            download_calls.append({'args': args, 'kwargs': kwargs})
            # Return None to simulate failed download (for test purposes)
            return None, None

        analysis_service.downloader.download_with_metadata = track_and_fail_downloads

        # Create run
        import uuid
        run_id = str(uuid.uuid4())
        test_db.create_analysis_run(
            run_id=run_id,
            ticker="TEST",
            analysis_type="perspective",
            filing_type="10-K",
            years=[2022, 2023],
            config={"perspectives": ["buffett"]}
        )

        # Request years including the one with stale cache
        pdf_paths = analysis_service._get_or_download_filings(
            ticker="TEST",
            filing_type="10-K",
            years=[2022, 2023],
            run_id=run_id
        )

        # 2023 should be from cache
        assert 2023 in pdf_paths

        # 2022 should have triggered a download attempt (stale cache)
        assert len(download_calls) == 1

        # Stale cache entry should have been cleared
        assert test_db.get_cached_file("TEST", 2022, "10-K") is None

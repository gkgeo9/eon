#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for file caching and corpus management system.

Tests the cache query methods and CorpusManager functionality.

Note: Tests using test_db fixture may fail due to migration ordering issue.
Migration files v0011/v0012 sort alphabetically before v002-v010, causing
ALTER TABLE to fail before CREATE TABLE runs. The real database works fine.
"""

from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest




class TestFileCacheOperations:
    """Tests for new file cache query methods."""

    @pytest.fixture
    def db_with_cache(self, test_db, temp_dir):
        """Database with pre-populated cache entries and fake PDF files."""
        # Create fake PDF files
        pdf_dir = temp_dir / "pdfs" / "AAPL"
        pdf_dir.mkdir(parents=True)

        # Create cached PDFs for years 2022, 2023, 2024
        for year, date in [(2022, "2022-10-28"), (2023, "2023-11-03"), (2024, "2024-11-01")]:
            pdf_path = pdf_dir / f"AAPL_10-K_{date}.pdf"
            pdf_path.write_text("fake pdf content")

            test_db.cache_file(
                ticker="AAPL",
                fiscal_year=year,
                filing_type="10-K",
                file_path=str(pdf_path),
                filing_date=date
            )

        return test_db, pdf_dir

    @pytest.mark.unit
    def test_get_cached_file_returns_path(self, db_with_cache):
        """Test that cached file path is returned correctly."""
        test_db, pdf_dir = db_with_cache

        cached = test_db.get_cached_file("AAPL", 2023, "10-K")

        assert cached is not None
        assert "AAPL_10-K_2023-11-03.pdf" in cached

    @pytest.mark.unit
    def test_get_latest_cached_filing_date(self, db_with_cache):
        """Test retrieving most recent filing date from cache."""
        test_db, _ = db_with_cache

        latest = test_db.get_latest_cached_filing_date("AAPL", "10-K")

        assert latest == "2024-11-01"

    @pytest.mark.unit
    def test_get_latest_cached_filing_date_no_cache(self, test_db):
        """Test get_latest_cached_filing_date returns None when no cache."""
        latest = test_db.get_latest_cached_filing_date("UNKNOWN", "10-K")

        assert latest is None

    @pytest.mark.unit
    def test_get_all_cached_filings(self, db_with_cache):
        """Test retrieving all cached filings for a ticker."""
        test_db, _ = db_with_cache

        cached = test_db.get_all_cached_filings("AAPL", "10-K")

        assert len(cached) == 3
        # Should be sorted by filing_date descending
        assert cached[0]['fiscal_year'] == 2024
        assert cached[1]['fiscal_year'] == 2023
        assert cached[2]['fiscal_year'] == 2022

    @pytest.mark.unit
    def test_is_filing_cached_true(self, db_with_cache):
        """Test is_filing_cached returns True for cached filing."""
        test_db, _ = db_with_cache

        result = test_db.is_filing_cached("AAPL", "2023-11-03", "10-K")

        assert result is True

    @pytest.mark.unit
    def test_is_filing_cached_false(self, db_with_cache):
        """Test is_filing_cached returns False for non-cached filing."""
        test_db, _ = db_with_cache

        result = test_db.is_filing_cached("AAPL", "2025-11-01", "10-K")

        assert result is False

    @pytest.mark.unit
    def test_is_filing_cached_different_ticker(self, db_with_cache):
        """Test is_filing_cached returns False for different ticker."""
        test_db, _ = db_with_cache

        result = test_db.is_filing_cached("MSFT", "2023-11-03", "10-K")

        assert result is False

    @pytest.mark.unit
    def test_clear_file_cache_entry(self, db_with_cache):
        """Test clearing a single cache entry."""
        test_db, _ = db_with_cache

        # Verify entry exists
        assert test_db.get_cached_file("AAPL", 2023, "10-K") is not None

        # Clear it
        test_db.clear_file_cache_entry("AAPL", 2023, "10-K")

        # Verify it's gone
        assert test_db.get_cached_file("AAPL", 2023, "10-K") is None

        # Verify others are still there
        assert test_db.get_cached_file("AAPL", 2022, "10-K") is not None
        assert test_db.get_cached_file("AAPL", 2024, "10-K") is not None

    @pytest.mark.unit
    def test_get_tickers_with_cached_files(self, db_with_cache, test_db, temp_dir):
        """Test getting list of tickers with cached files."""
        db, _ = db_with_cache

        # Add another ticker
        msft_dir = temp_dir / "pdfs" / "MSFT"
        msft_dir.mkdir(parents=True)
        msft_pdf = msft_dir / "MSFT_10-K_2023-07-27.pdf"
        msft_pdf.write_text("fake pdf")
        db.cache_file("MSFT", 2023, "10-K", str(msft_pdf), filing_date="2023-07-27")

        tickers = db.get_tickers_with_cached_files("10-K")

        assert "AAPL" in tickers
        assert "MSFT" in tickers
        assert len(tickers) == 2


class TestFileCacheWithMissingFiles:
    """Tests for handling cached entries where files are missing."""

    @pytest.fixture
    def db_with_stale_cache(self, test_db, temp_dir):
        """Database with cache entries pointing to non-existent files."""
        # Create one real file
        pdf_dir = temp_dir / "pdfs" / "TEST"
        pdf_dir.mkdir(parents=True)

        real_pdf = pdf_dir / "TEST_10-K_2023-02-15.pdf"
        real_pdf.write_text("real pdf")

        test_db.cache_file(
            ticker="TEST",
            fiscal_year=2023,
            filing_type="10-K",
            file_path=str(real_pdf),
            filing_date="2023-02-15"
        )

        # Create a cache entry for a file that doesn't exist
        fake_path = pdf_dir / "TEST_10-K_2022-02-15.pdf"
        test_db.cache_file(
            ticker="TEST",
            fiscal_year=2022,
            filing_type="10-K",
            file_path=str(fake_path),  # File doesn't exist
            filing_date="2022-02-15"
        )

        return test_db, pdf_dir

    @pytest.mark.unit
    def test_cached_file_exists_check(self, db_with_stale_cache):
        """Test that cached file paths can be verified for existence."""
        test_db, _ = db_with_stale_cache

        # Real file
        cached_2023 = test_db.get_cached_file("TEST", 2023, "10-K")
        assert cached_2023 is not None
        assert Path(cached_2023).exists()

        # Stale entry (file doesn't exist)
        cached_2022 = test_db.get_cached_file("TEST", 2022, "10-K")
        assert cached_2022 is not None  # Cache entry exists
        assert not Path(cached_2022).exists()  # But file doesn't


class TestCorpusManager:
    """Tests for CorpusManager functionality."""

    @pytest.fixture
    def db_with_cache(self, test_db, temp_dir):
        """Database with pre-populated cache entries."""
        pdf_dir = temp_dir / "pdfs" / "AAPL"
        pdf_dir.mkdir(parents=True)

        for year, date in [(2022, "2022-10-28"), (2023, "2023-11-03")]:
            pdf_path = pdf_dir / f"AAPL_10-K_{date}.pdf"
            pdf_path.write_text("fake pdf content")

            test_db.cache_file(
                ticker="AAPL",
                fiscal_year=year,
                filing_type="10-K",
                file_path=str(pdf_path),
                filing_date=date
            )

        return test_db, pdf_dir

    @pytest.fixture
    def corpus_manager(self, db_with_cache):
        """Create CorpusManager with mocked SEC downloader."""
        from eon.data.corpus import CorpusManager

        test_db, pdf_dir = db_with_cache
        mock_downloader = MagicMock()

        return CorpusManager(test_db, mock_downloader), test_db, pdf_dir

    @pytest.mark.unit
    def test_check_for_new_filings_finds_new(self, corpus_manager):
        """Test that new filings are detected compared to cache."""
        corpus, test_db, _ = corpus_manager

        # Mock SEC API to return filings including a new one
        corpus.downloader.get_available_filings.return_value = [
            {'filing_date': '2024-11-01', 'fiscal_year': 2024, 'accession_number': 'new-1'},
            {'filing_date': '2023-11-03', 'fiscal_year': 2023, 'accession_number': 'cached-1'},
            {'filing_date': '2022-10-28', 'fiscal_year': 2022, 'accession_number': 'cached-2'},
        ]

        new_filings = corpus.check_for_new_filings("AAPL", "10-K")

        # Should only return the 2024 filing (not in cache)
        assert len(new_filings) == 1
        assert new_filings[0]['filing_date'] == '2024-11-01'
        assert new_filings[0]['fiscal_year'] == 2024

    @pytest.mark.unit
    def test_check_for_new_filings_none_new(self, corpus_manager):
        """Test no new filings reported when cache is up to date."""
        corpus, test_db, _ = corpus_manager

        # SEC returns only what we already have cached
        corpus.downloader.get_available_filings.return_value = [
            {'filing_date': '2023-11-03', 'fiscal_year': 2023},
            {'filing_date': '2022-10-28', 'fiscal_year': 2022},
        ]

        new_filings = corpus.check_for_new_filings("AAPL", "10-K")

        assert len(new_filings) == 0

    @pytest.mark.unit
    def test_get_corpus_status(self, corpus_manager):
        """Test getting corpus status."""
        corpus, test_db, _ = corpus_manager

        status = corpus.get_corpus_status("AAPL", "10-K")

        assert status['ticker'] == 'AAPL'
        assert status['filing_type'] == '10-K'
        assert status['cached_count'] == 2
        assert status['latest_cached_date'] == '2023-11-03'

    @pytest.mark.unit
    def test_get_filings_smart_uses_cache(self, corpus_manager):
        """Test that get_filings_smart returns cached files."""
        corpus, test_db, _ = corpus_manager

        pdf_paths, years_not_cached = corpus.get_filings_smart(
            "AAPL", "10-K", years=[2022, 2023]
        )

        # Both years should be in cache
        assert 2022 in pdf_paths
        assert 2023 in pdf_paths
        assert len(years_not_cached) == 0

    @pytest.mark.unit
    def test_get_filings_smart_identifies_missing(self, corpus_manager):
        """Test that get_filings_smart identifies years not in cache."""
        corpus, test_db, _ = corpus_manager

        pdf_paths, years_not_cached = corpus.get_filings_smart(
            "AAPL", "10-K", years=[2022, 2023, 2024, 2025]
        )

        # 2022 and 2023 should be in cache
        assert 2022 in pdf_paths
        assert 2023 in pdf_paths
        # 2024 and 2025 are not cached
        assert 2024 in years_not_cached
        assert 2025 in years_not_cached

    @pytest.mark.unit
    def test_verify_cache_integrity(self, corpus_manager, temp_dir):
        """Test cache integrity verification."""
        corpus, test_db, pdf_dir = corpus_manager

        # Add a stale cache entry (file doesn't exist)
        fake_path = pdf_dir / "AAPL_10-K_2021-10-29.pdf"
        test_db.cache_file("AAPL", 2021, "10-K", str(fake_path), filing_date="2021-10-29")

        result = corpus.verify_cache_integrity("AAPL", "10-K", remove_stale=False)

        assert result['valid_count'] == 2  # 2022 and 2023
        assert result['stale_count'] == 1  # 2021

    @pytest.mark.unit
    def test_verify_cache_integrity_removes_stale(self, corpus_manager, temp_dir):
        """Test that verify_cache_integrity can remove stale entries."""
        corpus, test_db, pdf_dir = corpus_manager

        # Add a stale cache entry
        fake_path = pdf_dir / "AAPL_10-K_2021-10-29.pdf"
        test_db.cache_file("AAPL", 2021, "10-K", str(fake_path), filing_date="2021-10-29")

        # Verify stale entry exists
        assert test_db.get_cached_file("AAPL", 2021, "10-K") is not None

        # Run integrity check with removal
        result = corpus.verify_cache_integrity("AAPL", "10-K", remove_stale=True)

        # Stale entry should be removed
        assert test_db.get_cached_file("AAPL", 2021, "10-K") is None
        assert result['stale_count'] == 1

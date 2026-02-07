#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Final validation test suite for EON project.
Tests all functionality including caching, multi-year, single-year, and full workflows.
"""

import sys
import time
import uuid
import sqlite3
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from eon.ui.database import DatabaseRepository
from eon.ui.services import AnalysisService


class FinalValidationSuite:
    """Final comprehensive validation for production."""

    def __init__(self):
        self.db = DatabaseRepository()
        self.service = AnalysisService(self.db)
        self.results = []

    def test(self, name, func):
        """Run a test and track result."""
        print(f"\n{'='*80}")
        print(f"TEST: {name}")
        print('='*80)
        try:
            func()
            self.results.append((name, True, None))
            print(f"\n✅ PASSED\n")
            return True
        except Exception as e:
            self.results.append((name, False, str(e)))
            print(f"\n❌ FAILED: {e}\n")
            import traceback
            traceback.print_exc()
            return False

    # ==================== CACHING TESTS ====================

    def test_file_caching_single_year(self):
        """Test file caching for single year."""
        test_id = str(uuid.uuid4())
        try:
            self.db.create_analysis_run(
                run_id=test_id, ticker='CACHE_TEST', analysis_type='fundamental',
                filing_type='10-K', years=[2024], config={}
            )

            # Cache a file (use cross-platform temp directory)
            temp_dir = tempfile.gettempdir()
            test_path = str(Path(temp_dir) / 'test_2024.pdf')
            self.db.cache_file('CACHE_TEST', 2024, '10-K', test_path)
            print(f"✓ Cached file: {test_path}")

            # Retrieve it
            cached = self.db.get_cached_file('CACHE_TEST', 2024, '10-K')
            assert cached == test_path, f"Expected {test_path}, got {cached}"
            print(f"✓ Retrieved cached file: {cached}")

        finally:
            self.db.delete_analysis_run(test_id)

    def test_file_caching_multi_year(self):
        """Test file caching for multiple years."""
        test_id = str(uuid.uuid4())
        try:
            self.db.create_analysis_run(
                run_id=test_id, ticker='CACHE_MULTI', analysis_type='fundamental',
                filing_type='10-K', years=[2024, 2023, 2022], config={}
            )

            years = [2024, 2023, 2022]
            paths = {}
            temp_dir = tempfile.gettempdir()

            print(f"Caching {len(years)} years:")
            for year in years:
                path = str(Path(temp_dir) / f'test_{year}.pdf')
                self.db.cache_file('CACHE_MULTI', year, '10-K', path)
                paths[year] = path
                print(f"  ✓ Cached {year}: {path}")

            print(f"Verifying cache retrieval:")
            for year in years:
                cached = self.db.get_cached_file('CACHE_MULTI', year, '10-K')
                assert cached == paths[year], f"Cache mismatch for {year}"
                print(f"  ✓ Retrieved {year}: {cached}")

        finally:
            self.db.delete_analysis_run(test_id)

    def test_cache_isolation(self):
        """Test that cache entries are isolated by ticker, year, and filing type."""
        test_id1 = str(uuid.uuid4())
        test_id2 = str(uuid.uuid4())
        try:
            for test_id in [test_id1, test_id2]:
                self.db.create_analysis_run(
                    run_id=test_id, ticker='ISO_TEST', analysis_type='fundamental',
                    filing_type='10-K', years=[2024], config={}
                )

            # Cache different files for different tickers (use cross-platform temp directory)
            temp_dir = tempfile.gettempdir()
            a_2024_path = str(Path(temp_dir) / 'a_2024.pdf')
            b_2024_path = str(Path(temp_dir) / 'b_2024.pdf')
            self.db.cache_file('TICKER_A', 2024, '10-K', a_2024_path)
            self.db.cache_file('TICKER_B', 2024, '10-K', b_2024_path)

            # Verify isolation
            a_cached = self.db.get_cached_file('TICKER_A', 2024, '10-K')
            b_cached = self.db.get_cached_file('TICKER_B', 2024, '10-K')

            assert a_cached == a_2024_path, f"TICKER_A mismatch"
            assert b_cached == b_2024_path, f"TICKER_B mismatch"
            print(f"✓ Cache properly isolated by ticker")

            # Test filing type isolation
            a_2024_q_path = str(Path(temp_dir) / 'a_2024_q.pdf')
            self.db.cache_file('TICKER_A', 2024, '10-Q', a_2024_q_path)
            q_cached = self.db.get_cached_file('TICKER_A', 2024, '10-Q')
            assert q_cached == a_2024_q_path
            print(f"✓ Cache properly isolated by filing type")

            # Test year isolation
            a_2023_path = str(Path(temp_dir) / 'a_2023.pdf')
            self.db.cache_file('TICKER_A', 2023, '10-K', a_2023_path)
            cached_2023 = self.db.get_cached_file('TICKER_A', 2023, '10-K')
            cached_2024 = self.db.get_cached_file('TICKER_A', 2024, '10-K')
            assert cached_2023 == a_2023_path
            assert cached_2024 == a_2024_path
            print(f"✓ Cache properly isolated by year")

        finally:
            for test_id in [test_id1, test_id2]:
                try:
                    self.db.delete_analysis_run(test_id)
                except:
                    pass

    # ==================== SINGLE YEAR ANALYSIS ====================

    def test_single_year_analysis_workflow(self):
        """Test complete single-year analysis workflow."""
        test_id = str(uuid.uuid4())
        try:
            ticker = 'SINGLE_YEAR'
            year = 2024
            filing_type = '10-K'

            print(f"Starting single-year analysis: {ticker} {year} {filing_type}")

            # Create run
            self.db.create_analysis_run(
                run_id=test_id, ticker=ticker, analysis_type='fundamental',
                filing_type=filing_type, years=[year], config={}
            )
            print(f"✓ Created run")

            # Simulate analysis lifecycle
            self.db.update_run_status(test_id, 'running')
            print(f"✓ Started (running)")

            self.db.update_run_progress(test_id, 'Downloading...', 20, 'Download', 1)
            self.db.update_run_progress(test_id, 'Converting...', 40, 'Convert', 1)
            self.db.update_run_progress(test_id, 'Analyzing...', 80, 'Analyze', 1)
            print(f"✓ Progress tracked (20% → 40% → 80%)")

            self.db.update_run_status(test_id, 'completed')
            print(f"✓ Completed")

            # Verify final state
            details = self.db.get_run_details(test_id)
            assert details['status'] == 'completed'
            assert details['ticker'] == ticker
            assert details['progress_percent'] == 80
            print(f"✓ Verified final state")

        finally:
            self.db.delete_analysis_run(test_id)

    # ==================== MULTI-YEAR ANALYSIS ====================

    def test_multi_year_analysis_workflow(self):
        """Test complete multi-year analysis workflow."""
        test_id = str(uuid.uuid4())
        try:
            ticker = 'MULTI_YEAR'
            years = [2024, 2023, 2022]
            filing_type = '10-K'

            print(f"Starting multi-year analysis: {ticker} {years} {filing_type}")

            # Create run
            self.db.create_analysis_run(
                run_id=test_id, ticker=ticker, analysis_type='excellent',
                filing_type=filing_type, years=years, config={}
            )
            print(f"✓ Created run for {len(years)} years")

            # Simulate analysis lifecycle
            self.db.update_run_status(test_id, 'running')
            print(f"✓ Started (running)")

            # Simulate per-year analysis
            progress_steps = [
                (15, 'Downloading...', 'Download', 1),
                (25, 'Converting...', 'Convert', 1),
            ]

            for percent, msg, step, count in progress_steps:
                self.db.update_run_progress(test_id, msg, percent, step, count)

            # Per-year analysis
            for idx, year in enumerate(years):
                progress = 35 + (idx * 20)
                self.db.update_run_progress(
                    test_id, f'Analyzing {year}...', progress, f'Year {year}', len(years)
                )
                time.sleep(0.05)

            self.db.update_run_progress(test_id, 'Finalizing...', 95, 'Final', 1)
            print(f"✓ Progress tracked through all stages")

            self.db.update_run_status(test_id, 'completed')
            print(f"✓ Completed")

            # Verify final state
            details = self.db.get_run_details(test_id)
            assert details['status'] == 'completed'
            assert details['ticker'] == ticker
            assert details['progress_percent'] == 95
            print(f"✓ Verified final state for {len(years)} years")

        finally:
            self.db.delete_analysis_run(test_id)

    # ==================== BATCH ANALYSIS ====================

    def test_batch_analysis_workflow(self):
        """Test batch analysis with multiple tickers."""
        test_ids = []
        try:
            tickers = ['BATCH_A', 'BATCH_B', 'BATCH_C']
            print(f"Starting batch analysis for {len(tickers)} tickers")

            for ticker in tickers:
                test_id = str(uuid.uuid4())
                self.db.create_analysis_run(
                    run_id=test_id, ticker=ticker, analysis_type='fundamental',
                    filing_type='10-K', years=[2024, 2023], config={}
                )
                test_ids.append((ticker, test_id))
                print(f"✓ Created run for {ticker}")

            # Simulate all running in parallel
            for ticker, test_id in test_ids:
                self.db.update_run_status(test_id, 'running')

            print(f"✓ All {len(tickers)} analyses running")

            # Simulate completion
            for ticker, test_id in test_ids:
                self.db.update_run_progress(test_id, 'Processing...', 75, 'Analyze', 1)
                self.db.update_run_status(test_id, 'completed')

            print(f"✓ All {len(tickers)} analyses completed")

            # Verify all in database
            results = self.db.search_analyses(status='completed')
            completed_tickers = [r['ticker'] for _, r in results.iterrows()]

            for ticker, _ in test_ids:
                assert ticker in completed_tickers, f"{ticker} not found in results"

            print(f"✓ All {len(tickers)} analyses found in database")

        finally:
            for ticker, test_id in test_ids:
                try:
                    self.db.delete_analysis_run(test_id)
                except:
                    pass

    # ==================== COPY ALL FUNCTIONALITY ====================

    def test_copy_data_between_analyses(self):
        """Test copying analysis configuration and results."""
        source_id = str(uuid.uuid4())
        try:
            # Create source analysis
            config_data = {
                'custom_model': 'gpt-4',
                'analysis_depth': 'deep',
                'include_sentiment': True
            }

            self.db.create_analysis_run(
                run_id=source_id, ticker='SOURCE', analysis_type='fundamental',
                filing_type='10-K', years=[2024, 2023], config=config_data
            )
            print(f"✓ Created source analysis")

            # Get source details
            source_details = self.db.get_run_details(source_id)
            assert source_details['ticker'] == 'SOURCE'
            print(f"✓ Retrieved source details")

            # Create new analysis with similar config
            copy_id = str(uuid.uuid4())
            self.db.create_analysis_run(
                run_id=copy_id, ticker='COPY', analysis_type='fundamental',
                filing_type='10-K', years=[2024, 2023], config=config_data
            )
            print(f"✓ Created copy analysis with same config")

            # Verify copy has same config
            copy_details = self.db.get_run_details(copy_id)
            import json
            assert json.loads(copy_details['config_json']) == config_data
            print(f"✓ Verified config copied correctly")

            # Cleanup copy
            self.db.delete_analysis_run(copy_id)

        finally:
            self.db.delete_analysis_run(source_id)

    # ==================== CLEANUP & ORPHAN FILES ====================

    def test_orphan_analysis_cleanup(self):
        """Test that orphaned analyses can be cleaned up."""
        orphan_ids = []
        try:
            print(f"Creating orphaned analyses...")

            for i in range(3):
                test_id = str(uuid.uuid4())
                self.db.create_analysis_run(
                    run_id=test_id, ticker=f'ORPHAN_{i}', analysis_type='fundamental',
                    filing_type='10-K', years=[2024], config={}
                )
                orphan_ids.append(test_id)
                self.db.update_run_status(test_id, 'failed', 'Test error')
                print(f"✓ Created orphan {i+1}")

            # Verify they exist
            failed_analyses = self.db.search_analyses(status='failed')
            orphan_tickers = [f'ORPHAN_{i}' for i in range(3)]
            found = [r['ticker'] for _, r in failed_analyses.iterrows() if r['ticker'] in orphan_tickers]
            assert len(found) >= 3, f"Expected 3 orphan analyses, found {len(found)}"
            print(f"✓ Found all orphaned analyses in database")

            # Clean them up
            for test_id in orphan_ids:
                self.db.delete_analysis_run(test_id)
            print(f"✓ Cleaned up all orphaned analyses")

            # Verify cleanup
            failed_analyses = self.db.search_analyses(status='failed')
            remaining = [r['ticker'] for _, r in failed_analyses.iterrows() if r['ticker'] in orphan_tickers]
            assert len(remaining) == 0, f"Orphans not cleaned up: {remaining}"
            print(f"✓ Verified orphans are gone")

        except:
            for test_id in orphan_ids:
                try:
                    self.db.delete_analysis_run(test_id)
                except:
                    pass
            raise

    # ==================== DATA INTEGRITY ====================

    def test_data_integrity_across_operations(self):
        """Test that data integrity is maintained across operations."""
        test_id = str(uuid.uuid4())
        try:
            print(f"Testing data integrity...")

            # Create analysis
            original_config = {'version': 1, 'test': True}
            self.db.create_analysis_run(
                run_id=test_id, ticker='INTEGRITY', analysis_type='fundamental',
                filing_type='10-K', years=[2024], config=original_config
            )

            # Perform multiple operations
            self.db.update_run_status(test_id, 'running')
            self.db.update_run_progress(test_id, 'Step 1', 25, 'Download', 1)
            self.db.update_run_progress(test_id, 'Step 2', 50, 'Convert', 1)
            self.db.update_run_progress(test_id, 'Step 3', 75, 'Analyze', 1)
            self.db.update_run_status(test_id, 'completed')

            print(f"✓ Performed {4} database operations")

            # Verify all data intact
            details = self.db.get_run_details(test_id)
            assert details['ticker'] == 'INTEGRITY'
            assert details['status'] == 'completed'
            assert details['progress_percent'] == 75
            assert details['progress_message'] == 'Step 3'
            assert details['last_activity_at'] is not None

            import json
            assert json.loads(details['config_json']) == original_config

            print(f"✓ All data integrity checks passed")

        finally:
            self.db.delete_analysis_run(test_id)

    # ==================== RUN ALL ====================

    def run_all(self):
        """Run all validation tests."""
        print("\n")
        print("╔" + "="*78 + "╗")
        print("║" + " "*78 + "║")
        print("║" + "EON FINAL VALIDATION TEST SUITE".center(78) + "║")
        print("║" + " "*78 + "║")
        print("╚" + "="*78 + "╝")

        tests = [
            # Caching
            ("Single Year File Caching", self.test_file_caching_single_year),
            ("Multi-Year File Caching", self.test_file_caching_multi_year),
            ("Cache Isolation", self.test_cache_isolation),

            # Single Year
            ("Single Year Analysis Workflow", self.test_single_year_analysis_workflow),

            # Multi Year
            ("Multi-Year Analysis Workflow", self.test_multi_year_analysis_workflow),

            # Batch
            ("Batch Analysis Workflow", self.test_batch_analysis_workflow),

            # Copy
            ("Copy Data Between Analyses", self.test_copy_data_between_analyses),

            # Cleanup
            ("Orphan Analysis Cleanup", self.test_orphan_analysis_cleanup),

            # Integrity
            ("Data Integrity Across Operations", self.test_data_integrity_across_operations),
        ]

        for test_name, test_func in tests:
            self.test(test_name, test_func)

        self.print_summary()

    def print_summary(self):
        """Print test summary."""
        print("\n" + "="*80)
        print("FINAL VALIDATION SUMMARY")
        print("="*80)

        passed = sum(1 for _, result, _ in self.results if result)
        failed = sum(1 for _, result, _ in self.results if not result)
        total = len(self.results)

        for test_name, result, error in self.results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status}  {test_name}")
            if error:
                print(f"         {error}")

        print("="*80)
        print(f"\nResults: {passed}/{total} tests passed")

        if failed > 0:
            print(f"         {failed} test(s) failed")
            return 1
        else:
            print("\n" + "🎉 " * 20)
            print("ALL VALIDATION TESTS PASSED - READY FOR GITHUB".center(80))
            print("🎉 " * 20 + "\n")
            return 0


if __name__ == '__main__':
    suite = FinalValidationSuite()
    exit_code = suite.run_all()
    sys.exit(exit_code)

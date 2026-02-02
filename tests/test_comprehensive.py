#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Comprehensive test suite for entire Fintel project.
Tests all filing types, analysis types, and core functionality.
"""

import sys
import time
import uuid
import threading
import sqlite3
import tempfile
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from fintel.ui.database import DatabaseRepository
from fintel.ui.services import AnalysisService


class TestSuite:
    """Comprehensive test suite for Fintel."""

    def __init__(self):
        self.db = DatabaseRepository()
        self.service = AnalysisService(self.db)
        self.test_results = []
        self.test_count = 0

    def run_test(self, test_name, test_func):
        """Run a single test and track results."""
        self.test_count += 1
        print(f"\n{'='*80}")
        print(f"TEST {self.test_count}: {test_name}")
        print('='*80)
        try:
            test_func()
            self.test_results.append((test_name, True, None))
            print(f"\n✅ PASSED: {test_name}\n")
            return True
        except AssertionError as e:
            self.test_results.append((test_name, False, str(e)))
            print(f"\n❌ FAILED: {test_name}")
            print(f"   Error: {e}\n")
            return False
        except Exception as e:
            self.test_results.append((test_name, False, str(e)))
            print(f"\n❌ CRASHED: {test_name}")
            print(f"   Error: {e}\n")
            import traceback
            traceback.print_exc()
            return False

    # ==================== DATABASE TESTS ====================

    def test_database_schema(self):
        """Test that all required database columns exist."""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.execute("PRAGMA table_info(analysis_runs)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        conn.close()

        required = [
            'run_id', 'ticker', 'status', 'created_at', 'completed_at',
            'error_message', 'progress_message', 'progress_percent',
            'current_step', 'total_steps', 'last_activity_at'
        ]

        print(f"Checking {len(required)} required columns:")
        for col in required:
            assert col in columns, f"Missing column: {col}"
            print(f"  ✓ {col:25} ({columns[col]})")

    def test_run_creation(self):
        """Test creating analysis runs."""
        test_id = str(uuid.uuid4())
        try:
            self.db.create_analysis_run(
                run_id=test_id,
                ticker='TEST',
                analysis_type='fundamental',
                filing_type='10-K',
                years=[2024],
                config={'test': True}
            )
            print(f"✓ Created run: {test_id}")

            details = self.db.get_run_details(test_id)
            assert details['ticker'] == 'TEST'
            assert details['status'] == 'pending'
            assert details['analysis_type'] == 'fundamental'
            print(f"✓ Retrieved run details: status={details['status']}")
        finally:
            self.db.delete_analysis_run(test_id)

    def test_status_transitions(self):
        """Test all status transitions."""
        test_id = str(uuid.uuid4())
        try:
            self.db.create_analysis_run(
                run_id=test_id, ticker='TEST', analysis_type='fundamental',
                filing_type='10-K', years=[2024], config={}
            )

            # Test pending -> running
            self.db.update_run_status(test_id, 'running')
            status = self.db.get_run_status(test_id)
            assert status == 'running', f"Expected 'running', got '{status}'"
            print("✓ pending → running")

            # Test running -> completed
            self.db.update_run_status(test_id, 'completed')
            status = self.db.get_run_status(test_id)
            assert status == 'completed', f"Expected 'completed', got '{status}'"
            print("✓ running → completed")

            # Test with error
            test_id2 = str(uuid.uuid4())
            self.db.create_analysis_run(
                run_id=test_id2, ticker='TEST2', analysis_type='fundamental',
                filing_type='10-K', years=[2024], config={}
            )
            self.db.update_run_status(test_id2, 'failed', 'Test error message')
            status = self.db.get_run_status(test_id2)
            assert status == 'failed'
            details = self.db.get_run_details(test_id2)
            assert details['error_message'] == 'Test error message'
            print("✓ pending → failed (with error message)")
            self.db.delete_analysis_run(test_id2)

        finally:
            self.db.delete_analysis_run(test_id)

    def test_last_activity_at_updates(self):
        """Test that last_activity_at is properly tracked."""
        test_id = str(uuid.uuid4())
        try:
            self.db.create_analysis_run(
                run_id=test_id, ticker='TEST', analysis_type='fundamental',
                filing_type='10-K', years=[2024], config={}
            )

            # Initially NULL
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.execute(
                'SELECT last_activity_at FROM analysis_runs WHERE run_id = ?',
                (test_id,)
            )
            initial = cursor.fetchone()[0]
            assert initial is None, f"Expected NULL, got {initial}"
            print("✓ Initial last_activity_at is NULL")

            # Set on running
            self.db.update_run_status(test_id, 'running')
            cursor = conn.execute(
                'SELECT last_activity_at FROM analysis_runs WHERE run_id = ?',
                (test_id,)
            )
            after_running = cursor.fetchone()[0]
            assert after_running is not None, "Expected last_activity_at to be set"
            print(f"✓ Set on status→running: {after_running}")

            # Updated on progress
            time.sleep(0.1)
            self.db.update_run_progress(test_id, 'Testing', 50, 'Step', 1)
            cursor = conn.execute(
                'SELECT last_activity_at FROM analysis_runs WHERE run_id = ?',
                (test_id,)
            )
            after_progress = cursor.fetchone()[0]
            assert after_progress > after_running, "Expected last_activity_at to be updated"
            print(f"✓ Updated on progress: {after_progress}")

            # Set on completed
            self.db.update_run_status(test_id, 'completed')
            cursor = conn.execute(
                'SELECT last_activity_at, completed_at FROM analysis_runs WHERE run_id = ?',
                (test_id,)
            )
            activity, completed = cursor.fetchone()
            assert activity is not None and completed is not None
            print(f"✓ Set on completion: activity={activity}, completed={completed}")

            conn.close()
        finally:
            self.db.delete_analysis_run(test_id)

    # ==================== FILING TYPE TESTS ====================

    def test_filing_type_detection(self):
        """Test detection of all filing types."""
        annual_list = ['10-K', '10-Q', '20-F', 'N-CSR', 'N-CSRS', '40-F', 'ARS']
        quarterly_list = ['10-Q', '6-K']

        test_cases = [
            ('10-K', 'annual'),
            ('10-Q', 'quarterly'),
            ('20-F', 'annual'),
            ('6-K', 'quarterly'),
            ('8-K', 'event'),
            ('4', 'event'),
            ('DEF 14A', 'event'),
            ('S-1', 'event'),
            ('424B5', 'event'),
        ]

        print(f"Testing {len(test_cases)} filing types:")
        for filing_type, expected in test_cases:
            is_annual = filing_type.upper() in annual_list
            is_quarterly = filing_type.upper() in quarterly_list

            if not is_annual and not is_quarterly:
                detected = 'event'
            elif is_quarterly:
                detected = 'quarterly'
            else:
                detected = 'annual'

            assert detected == expected, f"{filing_type}: expected {expected}, got {detected}"
            print(f"  ✓ {filing_type:10} → {detected}")

    def test_all_filing_types_in_database(self):
        """Test creating runs with all filing types."""
        filing_types = [
            # Annual
            '10-K', '20-F', 'N-CSR', '40-F',
            # Quarterly
            '10-Q', '6-K',
            # Event-based
            '8-K', '4', 'DEF 14A', 'S-1', '424B5'
        ]

        created_ids = []
        try:
            print(f"Creating runs for {len(filing_types)} filing types:")
            for filing_type in filing_types:
                test_id = str(uuid.uuid4())
                self.db.create_analysis_run(
                    run_id=test_id,
                    ticker='TEST',
                    analysis_type='fundamental',
                    filing_type=filing_type,
                    years=[2024],
                    config={'filing_type': filing_type}
                )
                created_ids.append(test_id)
                print(f"  ✓ {filing_type}")

            # Verify all were created
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.execute(
                'SELECT COUNT(*) FROM analysis_runs WHERE ticker = ? AND analysis_type = ?',
                ('TEST', 'fundamental')
            )
            count = cursor.fetchone()[0]
            assert count >= len(filing_types), f"Expected {len(filing_types)} rows, got {count}"
            conn.close()
            print(f"✓ All {len(filing_types)} filing types created successfully")

        finally:
            for test_id in created_ids:
                try:
                    self.db.delete_analysis_run(test_id)
                except:
                    pass

    # ==================== ANALYSIS TYPE TESTS ====================

    def test_all_analysis_types(self):
        """Test creating runs with all analysis types."""
        analysis_types = [
            'fundamental', 'excellent', 'objective', 'buffett',
            'taleb', 'contrarian', 'scanner', 'multi'
        ]

        created_ids = []
        try:
            print(f"Testing {len(analysis_types)} analysis types:")
            for analysis_type in analysis_types:
                test_id = str(uuid.uuid4())
                self.db.create_analysis_run(
                    run_id=test_id,
                    ticker='TEST',
                    analysis_type=analysis_type,
                    filing_type='10-K',
                    years=[2024],
                    config={'analysis_type': analysis_type}
                )
                created_ids.append(test_id)

                # Verify
                details = self.db.get_run_details(test_id)
                assert details['analysis_type'] == analysis_type
                print(f"  ✓ {analysis_type}")

        finally:
            for test_id in created_ids:
                try:
                    self.db.delete_analysis_run(test_id)
                except:
                    pass

    # ==================== PROGRESS TRACKING TESTS ====================

    def test_progress_tracking(self):
        """Test progress tracking throughout analysis."""
        test_id = str(uuid.uuid4())
        try:
            self.db.create_analysis_run(
                run_id=test_id, ticker='TEST', analysis_type='fundamental',
                filing_type='10-K', years=[2024, 2023, 2022], config={}
            )
            self.db.update_run_status(test_id, 'running')

            progress_updates = [
                (15, 'Downloading filings...', 'Download', 1),
                (30, 'Converting to PDF...', 'Convert', 1),
                (50, 'Analyzing 2024...', 'Analyze', '2024'),
                (65, 'Analyzing 2023...', 'Analyze', '2023'),
                (80, 'Analyzing 2022...', 'Analyze', '2022'),
                (95, 'Generating report...', 'Report', 1),
            ]

            print(f"Simulating {len(progress_updates)} progress updates:")
            for percent, msg, step, step_count in progress_updates:
                time.sleep(0.05)
                self.db.update_run_progress(test_id, msg, percent, step, step_count)
                details = self.db.get_run_details(test_id)
                assert details['progress_percent'] == percent
                assert details['progress_message'] == msg
                print(f"  ✓ {percent:3}% - {msg}")

            # Verify final state
            details = self.db.get_run_details(test_id)
            assert details['progress_percent'] == 95
            assert details['progress_message'] == 'Generating report...'
            print(f"✓ All progress updates tracked correctly")

        finally:
            self.db.delete_analysis_run(test_id)

    # ==================== SEARCH & FILTER TESTS ====================

    def test_search_and_filtering(self):
        """Test searching and filtering analyses."""
        created_ids = []
        try:
            # Create diverse test data
            configs = [
                ('AAPL', 'fundamental', '10-K'),
                ('AAPL', 'excellent', '10-Q'),
                ('MSFT', 'fundamental', '10-K'),
                ('MSFT', 'contrarian', '8-K'),
                ('GOOGL', 'fundamental', '10-K'),
            ]

            print(f"Creating {len(configs)} test analyses:")
            for ticker, analysis_type, filing_type in configs:
                test_id = str(uuid.uuid4())
                self.db.create_analysis_run(
                    run_id=test_id,
                    ticker=ticker,
                    analysis_type=analysis_type,
                    filing_type=filing_type,
                    years=[2024],
                    config={}
                )
                # Set status to completed for some
                if ticker == 'AAPL':
                    self.db.update_run_status(test_id, 'completed')
                elif ticker == 'MSFT':
                    self.db.update_run_status(test_id, 'running')

                created_ids.append(test_id)
                print(f"  ✓ {ticker} - {analysis_type} - {filing_type}")

            # Test filtering by ticker
            results = self.db.search_analyses(ticker='AAPL')
            assert len(results) >= 2, f"Expected >=2 AAPL analyses, got {len(results)}"
            print(f"✓ Filter by ticker='AAPL': {len(results)} results")

            # Test filtering by analysis type
            results = self.db.search_analyses(analysis_type='fundamental')
            assert len(results) >= 3, f"Expected >=3 fundamental analyses, got {len(results)}"
            print(f"✓ Filter by analysis_type='fundamental': {len(results)} results")

            # Test filtering by status
            results = self.db.search_analyses(status='completed')
            assert len(results) >= 2, f"Expected >=2 completed, got {len(results)}"
            print(f"✓ Filter by status='completed': {len(results)} results")

            # Test combined filters
            results = self.db.search_analyses(ticker='MSFT', status='running')
            assert len(results) >= 1, f"Expected >=1 MSFT running, got {len(results)}"
            print(f"✓ Combined filters (MSFT + running): {len(results)} results")

        finally:
            for test_id in created_ids:
                try:
                    self.db.delete_analysis_run(test_id)
                except:
                    pass

    # ==================== THREAD SAFETY TESTS ====================

    def test_thread_result_containers(self):
        """Test thread-safe result containers."""
        print("Testing thread result containers:")

        # Test 1: Single thread success
        def mock_success(result_container):
            time.sleep(0.05)
            result_container['run_id'] = 'test-id-1'
            result_container['error'] = None

        container1 = {}
        thread1 = threading.Thread(target=mock_success, args=(container1,), daemon=True)
        thread1.start()

        # Wait with polling
        waited = 0
        while waited < 5 and 'run_id' not in container1:
            time.sleep(0.1)
            waited += 0.1

        assert container1.get('run_id') == 'test-id-1'
        print("  ✓ Single thread success")

        # Test 2: Multiple threads
        def mock_analysis(idx, container_list, container_lock):
            time.sleep(0.05 * idx)
            with container_lock:
                container_list.append(f'run-{idx}')

        container_list = []
        container_lock = threading.Lock()
        threads = []

        for i in range(5):
            thread = threading.Thread(
                target=mock_analysis,
                args=(i, container_list, container_lock),
                daemon=True
            )
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join(timeout=2)

        assert len(container_list) == 5, f"Expected 5 results, got {len(container_list)}"
        print(f"  ✓ Multiple threads: {len(container_list)} results collected")

        # Test 3: Error handling
        def mock_error(result_container):
            time.sleep(0.05)
            result_container['error'] = 'Test error'
            result_container['run_id'] = None

        container3 = {}
        thread3 = threading.Thread(target=mock_error, args=(container3,), daemon=True)
        thread3.start()
        thread3.join(timeout=2)

        assert container3.get('error') == 'Test error'
        print("  ✓ Error handling")

    # ==================== CACHED FILES TESTS ====================

    def test_file_caching(self):
        """Test file caching functionality."""
        test_id = str(uuid.uuid4())
        try:
            self.db.create_analysis_run(
                run_id=test_id, ticker='TEST', analysis_type='fundamental',
                filing_type='10-K', years=[2024], config={}
            )

            # Cache a file (use cross-platform temp directory)
            temp_dir = tempfile.gettempdir()
            test_path = str(Path(temp_dir) / 'test_filing_2024.pdf')
            self.db.cache_file('TEST', 2024, '10-K', test_path)
            print(f"✓ Cached file: {test_path}")

            # Retrieve cached file
            cached = self.db.get_cached_file('TEST', 2024, '10-K')
            assert cached == test_path, f"Expected {test_path}, got {cached}"
            print(f"✓ Retrieved cached file: {cached}")

            # Cache for different year
            test_path2 = str(Path(temp_dir) / 'test_filing_2023.pdf')
            self.db.cache_file('TEST', 2023, '10-K', test_path2)

            # Verify separate cache
            cached1 = self.db.get_cached_file('TEST', 2024, '10-K')
            cached2 = self.db.get_cached_file('TEST', 2023, '10-K')
            assert cached1 != cached2
            print(f"✓ Multiple cache entries: 2024={cached1}, 2023={cached2}")

        finally:
            self.db.delete_analysis_run(test_id)

    # ==================== FULL LIFECYCLE TEST ====================

    def test_full_analysis_lifecycle(self):
        """Test complete analysis lifecycle."""
        test_id = str(uuid.uuid4())
        try:
            ticker = 'COMPREHENSIVE'
            analysis_type = 'excellent'
            filing_type = '10-K'
            years = [2024, 2023, 2022]

            print(f"Simulating full lifecycle for {ticker}:")

            # 1. Create run
            self.db.create_analysis_run(
                run_id=test_id,
                ticker=ticker,
                analysis_type=analysis_type,
                filing_type=filing_type,
                years=years,
                config={'test': True}
            )
            print(f"  1. ✓ Created run (status=pending)")

            # 2. Start analysis
            self.db.update_run_status(test_id, 'running')
            print(f"  2. ✓ Started analysis (status=running)")

            # 3. Download phase
            self.db.update_run_progress(
                test_id, f'Downloading {filing_type} for {ticker}...', 10, 'Download', 1
            )
            time.sleep(0.05)
            print(f"  3. ✓ Downloading files (10%)")

            # 4. Conversion phase
            self.db.update_run_progress(
                test_id, 'Converting HTML to PDF...', 25, 'Convert', len(years)
            )
            time.sleep(0.05)
            print(f"  4. ✓ Converting to PDF (25%)")

            # 5. Analysis per year
            for idx, year in enumerate(years):
                progress = 40 + (idx * 15)
                self.db.update_run_progress(
                    test_id,
                    f'Analyzing {ticker} {year}...',
                    progress,
                    f'Year {year}',
                    len(years)
                )
                time.sleep(0.05)
            print(f"  5. ✓ Analyzed {len(years)} years (40-85%)")

            # 6. Finalization
            self.db.update_run_progress(
                test_id, 'Generating final report...', 95, 'Report', 1
            )
            time.sleep(0.05)
            print(f"  6. ✓ Finalizing report (95%)")

            # 7. Completion
            self.db.update_run_status(test_id, 'completed')
            print(f"  7. ✓ Completed analysis (status=completed)")

            # 8. Verification
            details = self.db.get_run_details(test_id)
            assert details['status'] == 'completed'
            assert details['progress_percent'] == 95
            assert details['ticker'] == ticker
            assert details['last_activity_at'] is not None
            print(f"  8. ✓ Verified final state")

            # 9. Search verification
            results = self.db.search_analyses(ticker=ticker, status='completed')
            assert len(results) >= 1
            print(f"  9. ✓ Found in search results")

        finally:
            self.db.delete_analysis_run(test_id)

    # ==================== RUN ALL TESTS ====================

    def run_all(self):
        """Run all tests."""
        print("\n")
        print("╔" + "="*78 + "╗")
        print("║" + " "*78 + "║")
        print("║" + "COMPREHENSIVE FINTEL TEST SUITE".center(78) + "║")
        print("║" + " "*78 + "║")
        print("╚" + "="*78 + "╝")

        tests = [
            # Database tests
            ("Database Schema Verification", self.test_database_schema),
            ("Run Creation", self.test_run_creation),
            ("Status Transitions", self.test_status_transitions),
            ("Last Activity Tracking", self.test_last_activity_at_updates),

            # Filing type tests
            ("Filing Type Detection", self.test_filing_type_detection),
            ("All Filing Types in Database", self.test_all_filing_types_in_database),

            # Analysis type tests
            ("All Analysis Types", self.test_all_analysis_types),

            # Progress tests
            ("Progress Tracking", self.test_progress_tracking),

            # Search & filter tests
            ("Search and Filtering", self.test_search_and_filtering),

            # Thread tests
            ("Thread Result Containers", self.test_thread_result_containers),

            # Caching tests
            ("File Caching", self.test_file_caching),

            # Full lifecycle test
            ("Full Analysis Lifecycle", self.test_full_analysis_lifecycle),
        ]

        for test_name, test_func in tests:
            self.run_test(test_name, test_func)

        # Print summary
        self.print_summary()

    def print_summary(self):
        """Print test summary."""
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)

        passed = sum(1 for _, result, _ in self.test_results if result)
        failed = sum(1 for _, result, _ in self.test_results if not result)
        total = len(self.test_results)

        for test_name, result, error in self.test_results:
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
            print("\n🎉 ALL TESTS PASSED! 🎉\n")
            return 0


if __name__ == '__main__':
    suite = TestSuite()
    exit_code = suite.run_all()
    sys.exit(exit_code)

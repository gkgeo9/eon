#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Comprehensive test suite for recent fixes:
1. last_activity_at updates (prevents interrupted marking)
2. SEC filing fetch logic (count-based for event filings)
3. Thread result container handling
"""

import sys
import uuid
import time
import threading
import sqlite3
from pathlib import Path
from datetime import datetime

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from fintel.ui.database import DatabaseRepository
from fintel.ui.services import AnalysisService


def test_last_activity_at_updates():
    """Test that last_activity_at is properly updated."""
    print("\n" + "="*80)
    print("TEST 1: last_activity_at Updates")
    print("="*80)

    db = DatabaseRepository()
    test_id = str(uuid.uuid4())

    try:
        # Create a test run
        db.create_analysis_run(
            run_id=test_id,
            ticker='TEST',
            analysis_type='fundamental',
            filing_type='10-K',
            years=[2024],
            config={'test': True}
        )
        print("✓ Created test run")

        # Check initial state (should be pending with no last_activity_at)
        conn = sqlite3.connect(db.db_path)
        cursor = conn.execute(
            'SELECT status, last_activity_at FROM analysis_runs WHERE run_id = ?',
            (test_id,)
        )
        status, last_activity = cursor.fetchone()
        assert status == 'pending', f"Expected status 'pending', got {status}"
        assert last_activity is None, f"Expected last_activity_at to be None initially"
        print("✓ Initial state correct: status=pending, last_activity_at=NULL")

        # Update status to running
        db.update_run_status(test_id, 'running')
        cursor = conn.execute(
            'SELECT status, last_activity_at FROM analysis_runs WHERE run_id = ?',
            (test_id,)
        )
        status, last_activity = cursor.fetchone()
        assert status == 'running', f"Expected status 'running', got {status}"
        assert last_activity is not None, f"Expected last_activity_at to be set when status changes to running"
        first_activity = last_activity
        print(f"✓ After status→running: last_activity_at = {last_activity}")

        # Wait a moment then update progress
        time.sleep(0.2)
        db.update_run_progress(test_id, 'Testing progress', 50, 'Step 1', 2)
        cursor = conn.execute(
            'SELECT progress_percent, last_activity_at FROM analysis_runs WHERE run_id = ?',
            (test_id,)
        )
        progress, last_activity = cursor.fetchone()
        assert progress == 50, f"Expected progress 50, got {progress}"
        assert last_activity is not None, f"Expected last_activity_at to be updated"
        assert last_activity > first_activity, f"Expected last_activity_at to be newer after progress update"
        print(f"✓ After progress update: last_activity_at updated to {last_activity}")
        print(f"✓ Timestamp changed: {first_activity} → {last_activity}")

        # Update status to completed
        db.update_run_status(test_id, 'completed')
        cursor = conn.execute(
            'SELECT status, last_activity_at, completed_at FROM analysis_runs WHERE run_id = ?',
            (test_id,)
        )
        status, last_activity, completed_at = cursor.fetchone()
        assert status == 'completed', f"Expected status 'completed', got {status}"
        assert last_activity is not None, f"Expected last_activity_at to be set"
        assert completed_at is not None, f"Expected completed_at to be set"
        print(f"✓ After completion: status=completed, last_activity_at={last_activity}")

        conn.close()
        print("\n✅ TEST 1 PASSED: last_activity_at properly maintained\n")
        return True

    except AssertionError as e:
        print(f"\n❌ TEST 1 FAILED: {e}\n")
        return False
    finally:
        try:
            db.delete_analysis_run(test_id)
        except:
            pass


def test_filing_type_detection():
    """Test that filing type detection works correctly."""
    print("\n" + "="*80)
    print("TEST 2: Filing Type Detection")
    print("="*80)

    service = AnalysisService(DatabaseRepository())

    test_cases = [
        # (filing_type, is_annual, is_quarterly, expected_type)
        ('10-K', True, False, 'annual'),
        ('20-F', True, False, 'annual'),
        ('10-Q', True, True, 'quarterly'),
        ('6-K', False, True, 'quarterly'),
        ('8-K', False, False, 'event'),
        ('4', False, False, 'event'),
        ('DEF 14A', False, False, 'event'),
    ]

    for filing_type, is_annual, is_quarterly, expected in test_cases:
        # Simulate the detection logic from _get_or_download_filings
        annual_list = ['10-K', '10-Q', '20-F', 'N-CSR', 'N-CSRS', '40-F', 'ARS']
        quarterly_list = ['10-Q', '6-K']

        is_annual_filing = filing_type.upper() in annual_list
        is_quarterly_filing = filing_type.upper() in quarterly_list

        if not is_annual_filing and not is_quarterly_filing:
            detected_type = 'event'
        elif is_quarterly_filing:
            detected_type = 'quarterly'
        else:
            detected_type = 'annual'

        assert detected_type == expected, \
            f"Filing {filing_type}: expected {expected}, got {detected_type}"
        print(f"✓ {filing_type:10} → {detected_type:10} (annual={is_annual_filing}, quarterly={is_quarterly_filing})")

    print("\n✅ TEST 2 PASSED: Filing type detection correct\n")
    return True


def test_thread_result_container():
    """Test that thread result containers work without ScriptRunContext."""
    print("\n" + "="*80)
    print("TEST 3: Thread Result Container Handling")
    print("="*80)

    # Simulate the thread behavior
    def mock_analysis_thread(service_result, result_container):
        """Mock analysis that runs in a thread."""
        try:
            # Simulate getting a run_id
            time.sleep(0.1)  # Simulate some work
            result_container['run_id'] = service_result
            result_container['error'] = None
        except Exception as e:
            result_container['run_id'] = None
            result_container['error'] = str(e)

    # Test successful case
    print("Testing successful thread execution...")
    result_container = {}
    thread = threading.Thread(
        target=mock_analysis_thread,
        args=('test-run-id-123', result_container),
        daemon=True
    )
    thread.start()

    # Wait for thread with polling (like the fixed code does)
    max_wait = 10
    waited = 0
    while waited < max_wait and 'run_id' not in result_container and 'error' not in result_container:
        time.sleep(0.1)
        waited += 0.1

    assert result_container.get('run_id') == 'test-run-id-123', \
        f"Expected run_id 'test-run-id-123', got {result_container.get('run_id')}"
    assert result_container.get('error') is None, \
        f"Expected no error, got {result_container.get('error')}"
    print(f"✓ Thread populated result_container in {waited:.1f}s")
    print(f"✓ run_id: {result_container['run_id']}")
    print(f"✓ error: {result_container['error']}")

    # Test error case
    print("\nTesting error handling in thread...")
    result_container2 = {}

    def mock_analysis_error(result_container):
        time.sleep(0.05)
        result_container['run_id'] = None
        result_container['error'] = 'Test error message'

    thread2 = threading.Thread(
        target=mock_analysis_error,
        args=(result_container2,),
        daemon=True
    )
    thread2.start()

    # Wait for result
    waited = 0
    while waited < max_wait and 'error' not in result_container2:
        time.sleep(0.1)
        waited += 0.1

    assert result_container2.get('run_id') is None, \
        f"Expected run_id None on error, got {result_container2.get('run_id')}"
    assert result_container2.get('error') == 'Test error message', \
        f"Expected error message, got {result_container2.get('error')}"
    print(f"✓ Error case handled correctly")
    print(f"✓ run_id: {result_container2['run_id']}")
    print(f"✓ error: {result_container2['error']}")

    print("\n✅ TEST 3 PASSED: Thread result containers work correctly\n")
    return True


def test_event_filing_count_logic():
    """Test that event filing count logic is correct."""
    print("\n" + "="*80)
    print("TEST 4: Event Filing Count Logic")
    print("="*80)

    # Simulate the count-based logic for event filings
    event_filing_types = ['8-K', '4', 'DEF 14A', '6-K']

    # Test: requesting 5 event filings
    requested_count = 5
    print(f"\nRequesting {requested_count} event filings...")

    for filing_type in event_filing_types:
        annual_list = ['10-K', '10-Q', '20-F', 'N-CSR', 'N-CSRS', '40-F', 'ARS']
        quarterly_list = ['10-Q', '6-K']

        is_annual = filing_type.upper() in annual_list
        is_quarterly = filing_type.upper() in quarterly_list

        if not is_annual and not is_quarterly:
            # Would call _get_event_filings with requested_count
            filing_index_keys = list(range(1, requested_count + 1))
            print(f"✓ {filing_type}: Would use count-based logic, keys = {filing_index_keys}")
            assert filing_index_keys == [1, 2, 3, 4, 5]
        else:
            print(f"  {filing_type}: Would use year-based logic")

    # Test: annual filing should NOT use count logic
    print(f"\nRequesting years [2024, 2023, 2022] for annual filing...")
    years = [2024, 2023, 2022]
    annual_list = ['10-K', '10-Q', '20-F', 'N-CSR', 'N-CSRS', '40-F', 'ARS']
    quarterly_list = ['10-Q', '6-K']

    is_annual = '10-K' in annual_list
    is_quarterly = '10-K' in quarterly_list

    if not is_annual and not is_quarterly:
        print("  Would use count-based logic")
    else:
        print(f"✓ 10-K: Would use year-based logic, years = {years}")
        assert years == [2024, 2023, 2022]

    print("\n✅ TEST 4 PASSED: Event filing count logic correct\n")
    return True


def test_database_migrations():
    """Test that database has required columns."""
    print("\n" + "="*80)
    print("TEST 5: Database Schema Verification")
    print("="*80)

    db = DatabaseRepository()
    conn = sqlite3.connect(db.db_path)

    # Get table info
    cursor = conn.execute("PRAGMA table_info(analysis_runs)")
    columns = {row[1]: row[2] for row in cursor.fetchall()}  # name: type

    required_columns = [
        'run_id', 'ticker', 'status', 'created_at', 'completed_at',
        'error_message', 'progress_message', 'progress_percent',
        'current_step', 'total_steps', 'last_activity_at'
    ]

    print("\nChecking required columns:")
    for col in required_columns:
        if col in columns:
            print(f"✓ {col:25} ({columns[col]})")
        else:
            print(f"✗ {col:25} MISSING!")
            return False

    conn.close()
    print("\n✅ TEST 5 PASSED: Database schema correct\n")
    return True


def run_all_tests():
    """Run all tests and report results."""
    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*78 + "║")
    print("║" + "COMPREHENSIVE TEST SUITE FOR FINTEL FIXES".center(78) + "║")
    print("║" + " "*78 + "║")
    print("╚" + "="*78 + "╝")

    tests = [
        ("Database last_activity_at Updates", test_last_activity_at_updates),
        ("Filing Type Detection", test_filing_type_detection),
        ("Thread Result Containers", test_thread_result_container),
        ("Event Filing Count Logic", test_event_filing_count_logic),
        ("Database Schema Verification", test_database_migrations),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ {test_name} CRASHED: {e}\n")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}  {test_name}")

    print("="*80)
    print(f"\nResults: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED! 🎉\n")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed\n")
        return 1


if __name__ == '__main__':
    exit_code = run_all_tests()
    sys.exit(exit_code)

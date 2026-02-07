#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Comprehensive tests for the three new features:
1. Universal file naming with filing_date
2. Cancellation token system
3. Batch queue service
"""

import os
import sys
import tempfile
import threading
import time
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# ============================================================================
# Feature 1: File Naming Tests
# ============================================================================

def test_converter_filing_date_extraction():
    """Test that converter correctly extracts filing_date from metadata."""
    from eon.data.sources.sec.converter import SECConverter

    # Test metadata matching
    metadata = [
        {'accession_number': '0000320193-24-000081', 'filing_date': '2024-10-31'},
        {'accession_number': '0000320193-24-000045', 'filing_date': '2024-05-02'},
    ]

    # Test with matching accession number (with dashes)
    result = SECConverter._get_filing_date_from_metadata('0000320193-24-000081', metadata)
    assert result == '2024-10-31', f"Expected '2024-10-31', got '{result}'"

    # Test with normalized format (without dashes)
    result = SECConverter._get_filing_date_from_metadata('000032019324000045', metadata)
    assert result == '2024-05-02', f"Expected '2024-05-02', got '{result}'"

    # Test with no match
    result = SECConverter._get_filing_date_from_metadata('9999999999999999', metadata)
    assert result is None, f"Expected None, got '{result}'"

    # Test with empty metadata
    result = SECConverter._get_filing_date_from_metadata('0000320193-24-000081', [])
    assert result is None, f"Expected None for empty metadata, got '{result}'"

    # Test with None metadata
    result = SECConverter._get_filing_date_from_metadata('0000320193-24-000081', None)
    assert result is None, f"Expected None for None metadata, got '{result}'"

    print("✓ Converter filing_date extraction tests passed")


def test_filename_generation_patterns():
    """Test that filenames are generated correctly for different scenarios."""
    # We'll test the logic without actually running the converter

    def generate_filename(ticker: str, filing_type: str, filing_date: str = None,
                         year: int = None, accession_suffix: str = None) -> str:
        """Simulate the filename generation logic from converter."""
        safe_filing_type = filing_type.replace(" ", "_")

        if filing_date:
            return f"{ticker}_{safe_filing_type}_{filing_date}.pdf"
        else:
            return f"{ticker}_{safe_filing_type}_{year}_{accession_suffix}.pdf"

    # Test with filing_date (the normal case now)
    assert generate_filename("AAPL", "10-K", "2024-10-31") == "AAPL_10-K_2024-10-31.pdf"
    assert generate_filename("TSLA", "8-K", "2024-03-15") == "TSLA_8-K_2024-03-15.pdf"
    assert generate_filename("MSFT", "10-Q", "2024-07-31") == "MSFT_10-Q_2024-07-31.pdf"
    assert generate_filename("GOOGL", "DEF 14A", "2024-04-15") == "GOOGL_DEF_14A_2024-04-15.pdf"

    # Test fallback (no filing_date)
    assert generate_filename("AAPL", "10-K", year=2024, accession_suffix="000081") == "AAPL_10-K_2024_000081.pdf"

    print("✓ Filename generation pattern tests passed")


def test_downloader_with_metadata():
    """Test that downloader correctly returns metadata with downloads."""
    from eon.data.sources.sec.downloader import SECDownloader

    # Check that the method exists and has correct signature
    downloader = SECDownloader()
    assert hasattr(downloader, 'download_with_metadata'), "Missing download_with_metadata method"

    # Check method signature
    import inspect
    sig = inspect.signature(downloader.download_with_metadata)
    params = list(sig.parameters.keys())
    assert 'ticker' in params, "Missing 'ticker' parameter"
    assert 'num_filings' in params, "Missing 'num_filings' parameter"
    assert 'filing_type' in params, "Missing 'filing_type' parameter"

    print("✓ Downloader with_metadata method exists and has correct signature")


# ============================================================================
# Feature 2: Cancellation Token Tests
# ============================================================================

def test_cancellation_token_basic():
    """Test basic cancellation token functionality."""
    from eon.ui.services.cancellation import CancellationToken, AnalysisCancelledException

    token = CancellationToken("test-run-1")

    # Token should not be cancelled initially
    assert not token.is_cancelled(), "Token should not be cancelled initially"

    # Cancel the token
    token.cancel()
    assert token.is_cancelled(), "Token should be cancelled after cancel()"

    # raise_if_cancelled should raise exception
    try:
        token.raise_if_cancelled()
        assert False, "Should have raised AnalysisCancelledException"
    except AnalysisCancelledException as e:
        assert e.run_id == "test-run-1", f"Wrong run_id in exception: {e.run_id}"

    print("✓ Cancellation token basic tests passed")


def test_cancellation_token_thread_safety():
    """Test that cancellation token is thread-safe."""
    from eon.ui.services.cancellation import CancellationToken

    token = CancellationToken("test-run-2")
    results = {'cancelled_count': 0, 'not_cancelled_count': 0}

    def check_cancelled():
        for _ in range(100):
            if token.is_cancelled():
                results['cancelled_count'] += 1
            else:
                results['not_cancelled_count'] += 1
            time.sleep(0.001)

    # Start multiple threads checking the token
    threads = [threading.Thread(target=check_cancelled) for _ in range(5)]
    for t in threads:
        t.start()

    # Cancel after a short delay
    time.sleep(0.05)
    token.cancel()

    for t in threads:
        t.join()

    # Both counts should be non-zero (token was checked before and after cancel)
    assert results['not_cancelled_count'] > 0, "Should have some not-cancelled checks"
    assert results['cancelled_count'] > 0, "Should have some cancelled checks"

    print("✓ Cancellation token thread safety tests passed")


def test_cancellation_registry():
    """Test the cancellation registry singleton."""
    from eon.ui.services.cancellation import get_cancellation_registry, CancellationRegistry

    registry = get_cancellation_registry()
    assert isinstance(registry, CancellationRegistry), "Should return CancellationRegistry instance"

    # Same instance should be returned
    registry2 = get_cancellation_registry()
    assert registry is registry2, "Should return same singleton instance"

    # Create and manage tokens
    token1 = registry.create_token("run-1")
    token2 = registry.create_token("run-2")

    assert not token1.is_cancelled()
    assert not token2.is_cancelled()

    # Get token by run_id
    retrieved = registry.get_token("run-1")
    assert retrieved is token1, "Should retrieve same token"

    # Cancel via registry
    registry.cancel_run("run-1", timeout=1.0)
    assert token1.is_cancelled(), "Token should be cancelled via registry"
    assert not token2.is_cancelled(), "Other tokens should not be affected"

    # Cleanup
    registry.cleanup_token("run-1")
    registry.cleanup_token("run-2")

    assert registry.get_token("run-1") is None, "Token should be removed after cleanup"

    print("✓ Cancellation registry tests passed")


def test_cancellation_with_thread_tracking():
    """Test that cancellation can track and wait for threads."""
    from eon.ui.services.cancellation import get_cancellation_registry

    registry = get_cancellation_registry()
    token = registry.create_token("run-thread-test")

    thread_finished = {'value': False}

    def worker():
        try:
            for i in range(10):
                token.raise_if_cancelled()
                time.sleep(0.1)
            thread_finished['value'] = True
        except Exception:
            pass

    thread = threading.Thread(target=worker)
    token.set_thread(thread)
    thread.start()

    # Let it run a bit
    time.sleep(0.2)

    # Cancel and wait
    result = registry.cancel_run("run-thread-test", timeout=2.0)

    # Thread should have stopped
    assert not thread.is_alive(), "Thread should have stopped after cancellation"
    assert not thread_finished['value'], "Thread should not have completed normally"

    registry.cleanup_token("run-thread-test")

    print("✓ Cancellation with thread tracking tests passed")


# ============================================================================
# Feature 3: Batch Queue Tests
# ============================================================================

def test_batch_job_config():
    """Test BatchJobConfig dataclass."""
    from eon.ui.services.batch_queue import BatchJobConfig

    config = BatchJobConfig(
        name="Test Batch",
        tickers=["AAPL", "MSFT", "GOOGL"],
        analysis_type="fundamental",
        filing_type="10-K",
        num_years=5
    )

    assert config.name == "Test Batch"
    assert len(config.tickers) == 3
    assert config.analysis_type == "fundamental"
    assert config.filing_type == "10-K"
    assert config.num_years == 5

    print("✓ BatchJobConfig tests passed")


def test_batch_queue_database_schema():
    """Test that batch queue tables are created correctly."""
    # Read and execute migration
    migration_path = Path(__file__).parent.parent / "eon/ui/database/migrations/v008_batch_queue.sql"

    with open(migration_path) as f:
        migration_sql = f.read()

    # Create in-memory database and run migration
    conn = sqlite3.connect(":memory:")
    conn.executescript(migration_sql)

    # Check tables exist
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}

    assert 'batch_jobs' in tables, "batch_jobs table should exist"
    assert 'batch_items' in tables, "batch_items table should exist"
    assert 'queue_state' in tables, "queue_state table should exist"
    assert 'queue_daily_stats' in tables, "queue_daily_stats table should exist"

    # Check batch_jobs columns
    cursor = conn.execute("PRAGMA table_info(batch_jobs)")
    columns = {row[1] for row in cursor.fetchall()}
    required_columns = {'batch_id', 'name', 'total_tickers', 'completed_tickers',
                        'failed_tickers', 'status', 'analysis_type', 'filing_type'}
    assert required_columns.issubset(columns), f"Missing columns in batch_jobs: {required_columns - columns}"

    # Check queue_state singleton is initialized
    cursor = conn.execute("SELECT * FROM queue_state WHERE id = 1")
    row = cursor.fetchone()
    assert row is not None, "queue_state singleton should be initialized"

    conn.close()

    print("✓ Batch queue database schema tests passed")


def test_batch_queue_service_creation():
    """Test BatchQueueService initialization."""
    from eon.ui.services.batch_queue import BatchQueueService, BatchJobConfig

    # Create mock database
    mock_db = Mock()
    mock_db.execute = Mock(return_value=Mock(fetchone=Mock(return_value=None)))
    mock_db.get_connection = Mock(return_value=Mock(__enter__=Mock(), __exit__=Mock()))

    # Service should be createable
    service = BatchQueueService(mock_db)
    assert service is not None
    assert service.db is mock_db

    print("✓ BatchQueueService creation tests passed")


def test_batch_queue_job_creation():
    """Test creating batch jobs by testing the SQL operations directly."""
    from eon.ui.services.batch_queue import BatchJobConfig
    import uuid
    import json

    # Create a temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    try:
        # Initialize database with migration
        conn = sqlite3.connect(db_path)
        migration_path = Path(__file__).parent.parent / "eon/ui/database/migrations/v008_batch_queue.sql"
        with open(migration_path) as f:
            conn.executescript(f.read())

        # Simulate what BatchQueueService.create_batch_job does
        config = BatchJobConfig(
            name="Test S&P Analysis",
            tickers=["AAPL", "MSFT", "GOOGL", "AMZN", "META"],
            analysis_type="fundamental",
            filing_type="10-K",
            num_years=3
        )

        batch_id = str(uuid.uuid4())

        # Insert batch job
        conn.execute("""
            INSERT INTO batch_jobs
            (batch_id, name, total_tickers, analysis_type, filing_type, num_years, config_json, priority)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            batch_id,
            config.name,
            len(config.tickers),
            config.analysis_type,
            config.filing_type,
            config.num_years,
            json.dumps({'custom_prompt': None, 'max_retries': 2}),
            0
        ))

        # Insert batch items
        for ticker in config.tickers:
            conn.execute("""
                INSERT INTO batch_items (batch_id, ticker, company_name, status)
                VALUES (?, ?, ?, 'pending')
            """, (batch_id, ticker, None))

        conn.commit()

        # Verify batch was created
        cursor = conn.execute("SELECT * FROM batch_jobs WHERE batch_id = ?", (batch_id,))
        row = cursor.fetchone()
        assert row is not None, "Batch job should exist in database"

        # Verify items were created
        cursor = conn.execute("SELECT COUNT(*) FROM batch_items WHERE batch_id = ?", (batch_id,))
        count = cursor.fetchone()[0]
        assert count == 5, f"Should have 5 batch items, got {count}"

        # Verify status
        cursor = conn.execute("SELECT status FROM batch_jobs WHERE batch_id = ?", (batch_id,))
        status = cursor.fetchone()[0]
        assert status == 'pending', f"Status should be 'pending', got '{status}'"

        conn.close()

        print("✓ Batch queue job creation tests passed")

    finally:
        os.unlink(db_path)


def test_batch_queue_status_tracking():
    """Test batch status and progress tracking by testing SQL directly."""
    from eon.ui.services.batch_queue import BatchJobConfig
    import uuid
    import json

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    try:
        # Initialize database
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        migration_path = Path(__file__).parent.parent / "eon/ui/database/migrations/v008_batch_queue.sql"
        with open(migration_path) as f:
            conn.executescript(f.read())

        # Create a batch job manually
        batch_id = str(uuid.uuid4())
        conn.execute("""
            INSERT INTO batch_jobs
            (batch_id, name, total_tickers, analysis_type, filing_type, num_years, config_json, priority)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (batch_id, "Status Test", 2, "fundamental", "10-K", 5, "{}", 0))

        for ticker in ["AAPL", "MSFT"]:
            conn.execute("""
                INSERT INTO batch_items (batch_id, ticker, status)
                VALUES (?, ?, 'pending')
            """, (batch_id, ticker))

        conn.commit()

        # Test status query (simulating get_batch_status)
        cursor = conn.execute("""
            SELECT
                batch_id, name, total_tickers, completed_tickers, failed_tickers,
                skipped_tickers, status, analysis_type, filing_type, num_years,
                created_at, started_at, completed_at, estimated_completion, error_message
            FROM batch_jobs
            WHERE batch_id = ?
        """, (batch_id,))
        row = cursor.fetchone()
        assert row is not None, "Should return status row"
        assert row['total_tickers'] == 2, f"Expected 2 tickers, got {row['total_tickers']}"
        assert row['completed_tickers'] == 0
        assert row['status'] == 'pending'

        # Test updating status
        conn.execute("UPDATE batch_jobs SET status = 'running' WHERE batch_id = ?", (batch_id,))
        conn.commit()

        cursor = conn.execute("SELECT status FROM batch_jobs WHERE batch_id = ?", (batch_id,))
        new_status = cursor.fetchone()[0]
        assert new_status == 'running', f"Status should be 'running', got '{new_status}'"

        # Test completing an item
        conn.execute("""
            UPDATE batch_items SET status = 'completed', completed_at = CURRENT_TIMESTAMP
            WHERE batch_id = ? AND ticker = 'AAPL'
        """, (batch_id,))
        conn.execute("""
            UPDATE batch_jobs SET completed_tickers = completed_tickers + 1
            WHERE batch_id = ?
        """, (batch_id,))
        conn.commit()

        cursor = conn.execute("SELECT completed_tickers FROM batch_jobs WHERE batch_id = ?", (batch_id,))
        completed = cursor.fetchone()[0]
        assert completed == 1, f"Expected 1 completed, got {completed}"

        # Test get all batches query
        cursor = conn.execute("""
            SELECT
                batch_id, name, status, total_tickers, completed_tickers, failed_tickers,
                CASE
                    WHEN total_tickers > 0
                    THEN ROUND((completed_tickers * 100.0) / total_tickers, 1)
                    ELSE 0
                END as progress_percent
            FROM batch_jobs
            ORDER BY created_at DESC
        """)
        batches = [dict(r) for r in cursor.fetchall()]
        assert len(batches) >= 1, "Should have at least one batch"
        assert batches[0]['progress_percent'] == 50.0, f"Progress should be 50%, got {batches[0]['progress_percent']}"

        conn.close()

        print("✓ Batch queue status tracking tests passed")

    finally:
        os.unlink(db_path)


# ============================================================================
# Feature 4: Database Migration Tests
# ============================================================================

def test_filing_date_cache_migration():
    """Test v007 migration for filing_date column."""
    migration_path = Path(__file__).parent.parent / "eon/ui/database/migrations/v007_filing_date_cache.sql"

    with open(migration_path) as f:
        migration_sql = f.read()

    # Create in-memory database with file_cache table
    conn = sqlite3.connect(":memory:")
    conn.execute("""
        CREATE TABLE file_cache (
            id INTEGER PRIMARY KEY,
            ticker TEXT,
            fiscal_year INTEGER,
            filing_type TEXT,
            file_path TEXT
        )
    """)

    # Run migration
    conn.executescript(migration_sql)

    # Check filing_date column exists
    cursor = conn.execute("PRAGMA table_info(file_cache)")
    columns = {row[1] for row in cursor.fetchall()}
    assert 'filing_date' in columns, "filing_date column should exist after migration"

    # Check index exists
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_cache_ticker_filing_date'")
    row = cursor.fetchone()
    assert row is not None, "idx_cache_ticker_filing_date index should exist"

    conn.close()

    print("✓ Filing date cache migration tests passed")


# ============================================================================
# Integration Tests
# ============================================================================

def test_services_exports():
    """Test that all new classes are properly exported from services module."""
    from eon.ui.services import (
        AnalysisService,
        CancellationToken,
        CancellationRegistry,
        AnalysisCancelledException,
        get_cancellation_registry,
        BatchQueueService,
        BatchJobConfig,
    )

    # All imports should work
    assert CancellationToken is not None
    assert CancellationRegistry is not None
    assert AnalysisCancelledException is not None
    assert get_cancellation_registry is not None
    assert BatchQueueService is not None
    assert BatchJobConfig is not None

    print("✓ Services exports tests passed")


def test_ui_pages_import():
    """Test that UI pages can be imported without errors."""
    import importlib.util

    pages = [
        ("Analysis History", Path(__file__).parent.parent / "pages/2_📈_Analysis_History.py"),
        ("Batch Queue", Path(__file__).parent.parent / "pages/5_🌙_Batch_Queue.py"),
    ]

    for name, page_path in pages:
        if page_path.exists():
            # Just check the file is valid Python syntax
            with open(page_path) as f:
                source = f.read()

            try:
                compile(source, str(page_path), 'exec')
                print(f"  ✓ {name} page syntax is valid")
            except SyntaxError as e:
                raise AssertionError(f"{name} page has syntax error: {e}")

    print("✓ UI pages import tests passed")


# ============================================================================
# Run All Tests
# ============================================================================

def run_all_tests():
    """Run all tests and report results."""
    print("=" * 60)
    print("Running Comprehensive Tests for New Features")
    print("=" * 60)
    print()

    tests = [
        # Feature 1: File Naming
        ("Feature 1: Converter filing_date extraction", test_converter_filing_date_extraction),
        ("Feature 1: Filename generation patterns", test_filename_generation_patterns),
        ("Feature 1: Downloader with_metadata method", test_downloader_with_metadata),
        ("Feature 1: Filing date cache migration", test_filing_date_cache_migration),

        # Feature 2: Cancellation
        ("Feature 2: Cancellation token basic", test_cancellation_token_basic),
        ("Feature 2: Cancellation token thread safety", test_cancellation_token_thread_safety),
        ("Feature 2: Cancellation registry", test_cancellation_registry),
        ("Feature 2: Cancellation with thread tracking", test_cancellation_with_thread_tracking),

        # Feature 3: Batch Queue
        ("Feature 3: BatchJobConfig", test_batch_job_config),
        ("Feature 3: Batch queue database schema", test_batch_queue_database_schema),
        ("Feature 3: BatchQueueService creation", test_batch_queue_service_creation),
        ("Feature 3: Batch queue job creation", test_batch_queue_job_creation),
        ("Feature 3: Batch queue status tracking", test_batch_queue_status_tracking),

        # Integration
        ("Integration: Services exports", test_services_exports),
        ("Integration: UI pages syntax", test_ui_pages_import),
    ]

    passed = 0
    failed = 0
    errors = []

    for name, test_func in tests:
        try:
            print(f"\nRunning: {name}")
            test_func()
            passed += 1
        except Exception as e:
            failed += 1
            errors.append((name, str(e)))
            print(f"  ✗ FAILED: {e}")

    print()
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    if errors:
        print("\nFailed tests:")
        for name, error in errors:
            print(f"  - {name}: {error}")
        return 1
    else:
        print("\nAll tests passed!")
        return 0


if __name__ == "__main__":
    sys.exit(run_all_tests())

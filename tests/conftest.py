#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Shared test fixtures for EON tests.

Provides reusable fixtures for:
- Temporary directories and databases
- Mock API key management
- Mock Gemini providers
- Test batch configurations
"""

import os
import sys
import shutil
import tempfile
import threading
from pathlib import Path
from typing import Generator, List, Dict, Any
from unittest.mock import MagicMock, patch

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


# =============================================================================
# Temporary Directory Fixtures
# =============================================================================

@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory that's cleaned up after the test."""
    dir_path = tempfile.mkdtemp()
    yield Path(dir_path)
    shutil.rmtree(dir_path, ignore_errors=True)


@pytest.fixture
def temp_usage_dir(temp_dir: Path) -> Path:
    """Temporary directory for API usage tracking files."""
    usage_dir = temp_dir / "api_usage"
    usage_dir.mkdir(parents=True, exist_ok=True)
    return usage_dir


@pytest.fixture
def temp_db_path(temp_dir: Path) -> Path:
    """Temporary SQLite database path."""
    return temp_dir / "test_eon.db"


# =============================================================================
# API Key Fixtures
# =============================================================================

@pytest.fixture
def sample_api_keys() -> List[str]:
    """Sample API keys for testing (5 keys)."""
    return [f"test_api_key_{i}" for i in range(5)]


@pytest.fixture
def many_api_keys() -> List[str]:
    """Larger set of API keys for stress testing (25 keys)."""
    return [f"test_api_key_{i}" for i in range(25)]


# =============================================================================
# Usage Tracker Fixtures
# =============================================================================

@pytest.fixture
def mock_usage_tracker(temp_usage_dir: Path):
    """Create an APIUsageTracker with temporary storage."""
    from eon.ai.usage_tracker import APIUsageTracker
    return APIUsageTracker(usage_dir=temp_usage_dir)


@pytest.fixture
def mock_api_key_manager(sample_api_keys: List[str], mock_usage_tracker):
    """Create an APIKeyManager with mock tracker."""
    from eon.ai.key_manager import APIKeyManager
    return APIKeyManager(api_keys=sample_api_keys, tracker=mock_usage_tracker)


# =============================================================================
# Database Fixtures
# =============================================================================

@pytest.fixture
def test_db(temp_db_path: Path):
    """Create a test DatabaseRepository with migrations applied."""
    from eon.ui.database import DatabaseRepository

    # Create and initialize database
    db = DatabaseRepository(str(temp_db_path))

    yield db

    # Cleanup - close connection if method exists
    if hasattr(db, 'close'):
        db.close()
    elif hasattr(db, 'connection'):
        db.connection.close()


@pytest.fixture
def db_with_batch(test_db):
    """Database with a pre-created batch job for testing."""
    from eon.ui.services.batch_queue import BatchQueueService, BatchJobConfig

    service = BatchQueueService(test_db)
    batch_id = service.create_batch_job(BatchJobConfig(
        name="Test Batch",
        tickers=["AAPL", "MSFT", "GOOG"],
        analysis_type="fundamental",
        filing_type="10-K",
        num_years=1,
        max_retries=2
    ))

    return test_db, batch_id, service


# =============================================================================
# Batch Queue Fixtures
# =============================================================================

@pytest.fixture
def batch_queue_service(test_db):
    """Create a BatchQueueService for testing."""
    from eon.ui.services.batch_queue import BatchQueueService
    return BatchQueueService(test_db)


@pytest.fixture
def sample_batch_config():
    """Sample batch configuration for testing."""
    from eon.ui.services.batch_queue import BatchJobConfig
    return BatchJobConfig(
        name="Test Batch",
        tickers=["AAPL", "MSFT"],
        analysis_type="fundamental",
        filing_type="10-K",
        num_years=1,
        max_retries=2
    )


# =============================================================================
# Mock Provider Fixtures
# =============================================================================

@pytest.fixture
def mock_gemini_provider():
    """Mock GeminiProvider that returns fake analysis results."""
    provider = MagicMock()

    # Create a mock result that has model_dump method
    mock_result = MagicMock()
    mock_result.model_dump.return_value = {
        "summary": "Test analysis summary",
        "key_findings": ["Finding 1", "Finding 2"],
        "score": 75
    }
    provider.generate_with_retry.return_value = mock_result

    return provider


@pytest.fixture
def mock_analysis_service(test_db, mock_gemini_provider):
    """Mock AnalysisService that doesn't make real API calls."""
    from eon.ui.services.analysis_service import AnalysisService

    service = AnalysisService(test_db)

    # Patch the provider creation to return our mock
    with patch.object(service, '_create_provider', return_value=mock_gemini_provider):
        yield service


# =============================================================================
# Threading Test Fixtures
# =============================================================================

@pytest.fixture
def thread_safe_list():
    """Thread-safe list for collecting results from multiple threads."""
    class ThreadSafeList:
        def __init__(self):
            self._list = []
            self._lock = threading.Lock()

        def append(self, item):
            with self._lock:
                self._list.append(item)

        def remove(self, item):
            with self._lock:
                self._list.remove(item)

        def __contains__(self, item):
            with self._lock:
                return item in self._list

        def __len__(self):
            with self._lock:
                return len(self._list)

        def to_list(self):
            with self._lock:
                return list(self._list)

    return ThreadSafeList()


@pytest.fixture
def thread_error_collector():
    """Collect errors from multiple threads for assertion."""
    class ErrorCollector:
        def __init__(self):
            self._errors = []
            self._lock = threading.Lock()

        def add(self, error: str):
            with self._lock:
                self._errors.append(error)

        def has_errors(self) -> bool:
            with self._lock:
                return len(self._errors) > 0

        def get_errors(self) -> List[str]:
            with self._lock:
                return list(self._errors)

        def assert_no_errors(self):
            errors = self.get_errors()
            assert len(errors) == 0, f"Thread errors occurred: {errors}"

    return ErrorCollector()


# =============================================================================
# Pytest Markers
# =============================================================================

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "unit: Unit tests (fast, no external dependencies)"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests (may use database)"
    )
    config.addinivalue_line(
        "markers", "stress: Stress tests (slow, high concurrency)"
    )
    config.addinivalue_line(
        "markers", "slow: Tests that take > 5 seconds"
    )

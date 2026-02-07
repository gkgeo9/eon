#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Database repository for EON UI - handles all database operations.

This class uses mixins to organize functionality by domain while
maintaining a single public interface.

Improvements for batch processing reliability:
- Enhanced retry logic with exponential backoff and jitter
- SQLITE_BUSY specific handling
- Database backup support
- Context manager support for proper cleanup
"""

import sqlite3
import logging
import random
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

from .mixins import (
    AnalysisRunsMixin,
    AnalysisResultsMixin,
    CustomPromptsMixin,
    FileCacheMixin,
    UserSettingsMixin,
    ResumeMixin,
    StatisticsMixin,
    APIUsageMixin,
    CIKCacheMixin,
    SynthesisMixin,
)

logger = logging.getLogger(__name__)


class DatabaseRepository(
    AnalysisRunsMixin,
    AnalysisResultsMixin,
    CustomPromptsMixin,
    FileCacheMixin,
    UserSettingsMixin,
    ResumeMixin,
    StatisticsMixin,
    APIUsageMixin,
    CIKCacheMixin,
    SynthesisMixin,
):
    """
    Data access layer for Streamlit UI.
    Handles all database operations with proper error handling and retry logic.

    Functionality is organized into mixins:
    - AnalysisRunsMixin: CRUD for analysis runs
    - AnalysisResultsMixin: Storage/retrieval of analysis results
    - CustomPromptsMixin: Custom prompt management
    - FileCacheMixin: Downloaded file and filing type caching
    - UserSettingsMixin: User preferences
    - ResumeMixin: Run resumption and interruption handling
    - StatisticsMixin: Analytics and metrics queries
    - APIUsageMixin: API usage tracking
    - CIKCacheMixin: CIK to company mapping cache
    - SynthesisMixin: Synthesis job checkpointing
    """

    def __init__(self, db_path: str = "data/eon.db"):
        """
        Initialize database repository.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._closed = False
        self._init_database()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensure cleanup."""
        self.close()
        return False

    def close(self):
        """
        Close the repository and release resources.

        This method should be called when done with the repository,
        especially in long-running batch processes.
        """
        if not self._closed:
            self._closed = True
            # Perform a final WAL checkpoint to ensure all data is written
            try:
                with sqlite3.connect(self.db_path, timeout=10.0) as conn:
                    conn.execute("PRAGMA wal_checkpoint(PASSIVE)")
            except Exception as e:
                logger.warning(f"Error during repository close: {e}")

    def _init_database(self):
        """Initialize database schema from migration scripts."""
        # Ensure data directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        migrations_dir = Path(__file__).parent / "migrations"

        with sqlite3.connect(self.db_path) as conn:
            # Enable WAL mode for better concurrency
            conn.execute("PRAGMA journal_mode=WAL")

            # Apply migrations in order
            migration_files = sorted(migrations_dir.glob("v*.sql"))
            for migration_file in migration_files:
                try:
                    with open(migration_file, 'r') as f:
                        conn.executescript(f.read())
                except sqlite3.OperationalError as e:
                    # Ignore "duplicate column" errors (migration already applied)
                    if "duplicate column" not in str(e).lower():
                        raise
            conn.commit()

    def _execute_with_retry(
        self,
        query: str,
        params: tuple = (),
        max_retries: int = 10,
        fetch_one: bool = False,
        fetch_all: bool = False
    ):
        """
        Execute query with retry logic for database locks.

        Uses exponential backoff with jitter to handle concurrent access.
        Specifically handles SQLITE_BUSY errors which are common in batch processing.

        Args:
            query: SQL query string
            params: Query parameters
            max_retries: Maximum number of retry attempts (default: 10)
            fetch_one: If True, return the first row as a dict (or None)
            fetch_all: If True, return all rows as a list of dicts

        Returns:
            If fetch_one: dict or None
            If fetch_all: list of dicts
            Otherwise: lastrowid for INSERT, rowcount for UPDATE/DELETE

        Raises:
            sqlite3.OperationalError: If all retries fail
        """
        last_error = None

        for attempt in range(max_retries):
            try:
                with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                    # Enable WAL mode for better concurrency
                    conn.execute("PRAGMA journal_mode=WAL")
                    # Busy timeout in milliseconds (30 seconds)
                    conn.execute("PRAGMA busy_timeout=30000")
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute(query, params)
                    conn.commit()

                    # Fetch data while connection is still open
                    if fetch_one:
                        row = cursor.fetchone()
                        return dict(row) if row else None
                    elif fetch_all:
                        rows = cursor.fetchall()
                        return [dict(row) for row in rows]
                    else:
                        # For INSERT/UPDATE/DELETE, return useful metadata
                        return cursor.lastrowid if cursor.lastrowid else cursor.rowcount

            except sqlite3.OperationalError as e:
                last_error = e
                error_str = str(e).lower()

                # Check for retryable errors (locked, busy)
                is_retryable = any(keyword in error_str for keyword in [
                    "locked", "busy", "database is locked", "database is busy"
                ])

                if is_retryable and attempt < max_retries - 1:
                    # Exponential backoff with jitter: base * 2^attempt * (0.5 to 1.5)
                    base_wait = 0.1 * (2 ** attempt)
                    jitter = random.uniform(0.5, 1.5)
                    wait_time = min(base_wait * jitter, 30.0)  # Cap at 30 seconds

                    logger.warning(
                        f"Database busy/locked, retry {attempt + 1}/{max_retries} "
                        f"in {wait_time:.2f}s: {e}"
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(
                        f"Database operation failed after {attempt + 1} attempts: {e}"
                    )
                    raise

        # Should not reach here, but raise last error if we do
        if last_error:
            raise last_error

    def maintenance(self) -> dict:
        """
        Perform database maintenance operations.

        This should be called periodically during long-running operations
        (e.g., during daily rate limit reset waits) to keep the database healthy.

        Operations performed:
        - WAL checkpoint (flush WAL to main database)
        - Analyze (update query planner statistics)
        - Integrity check (optional, skipped if too slow)

        Returns:
            Dictionary with maintenance results and database stats
        """
        results = {
            'db_path': self.db_path,
            'size_before_mb': 0,
            'size_after_mb': 0,
            'wal_checkpoint': False,
            'analyze': False,
            'errors': []
        }

        try:
            # Get database size before maintenance
            db_file = Path(self.db_path)
            if db_file.exists():
                results['size_before_mb'] = db_file.stat().st_size / (1024 * 1024)

            with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                # Checkpoint WAL to reduce file size
                try:
                    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                    results['wal_checkpoint'] = True
                    logger.info("WAL checkpoint completed")
                except Exception as e:
                    results['errors'].append(f"WAL checkpoint failed: {e}")
                    logger.warning(f"WAL checkpoint failed: {e}")

                # Update query planner statistics
                try:
                    conn.execute("ANALYZE")
                    results['analyze'] = True
                    logger.info("ANALYZE completed")
                except Exception as e:
                    results['errors'].append(f"ANALYZE failed: {e}")
                    logger.warning(f"ANALYZE failed: {e}")

                conn.commit()

            # Get database size after maintenance
            if db_file.exists():
                results['size_after_mb'] = db_file.stat().st_size / (1024 * 1024)

            logger.info(
                f"Database maintenance complete: "
                f"{results['size_before_mb']:.1f}MB -> {results['size_after_mb']:.1f}MB"
            )

        except Exception as e:
            results['errors'].append(f"Maintenance failed: {e}")
            logger.error(f"Database maintenance failed: {e}")

        return results

    def backup(self, backup_dir: Optional[str] = None) -> Optional[str]:
        """
        Create a backup of the database.

        Uses SQLite's built-in backup API for safe, consistent backups
        even while the database is being written to.

        Args:
            backup_dir: Directory for backup file (default: same as database)

        Returns:
            Path to backup file, or None if backup failed
        """
        try:
            db_file = Path(self.db_path)
            if not db_file.exists():
                logger.warning(f"Database file does not exist: {self.db_path}")
                return None

            # Determine backup directory
            if backup_dir:
                backup_path = Path(backup_dir)
            else:
                backup_path = db_file.parent / "backups"

            backup_path.mkdir(parents=True, exist_ok=True)

            # Create backup filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = backup_path / f"eon_backup_{timestamp}.db"

            # Use SQLite's backup API for consistency
            with sqlite3.connect(self.db_path, timeout=30.0) as source_conn:
                # Perform WAL checkpoint first to ensure all data is in main file
                source_conn.execute("PRAGMA wal_checkpoint(FULL)")

                with sqlite3.connect(str(backup_file)) as dest_conn:
                    source_conn.backup(dest_conn)

            # Verify backup
            backup_size = backup_file.stat().st_size
            source_size = db_file.stat().st_size

            logger.info(
                f"Database backup created: {backup_file} "
                f"({backup_size / (1024 * 1024):.1f}MB)"
            )

            # Clean up old backups (keep last 5)
            self._cleanup_old_backups(backup_path, keep=5)

            return str(backup_file)

        except Exception as e:
            logger.error(f"Database backup failed: {e}")
            return None

    def _cleanup_old_backups(self, backup_dir: Path, keep: int = 5):
        """
        Remove old backup files, keeping only the most recent ones.

        Args:
            backup_dir: Directory containing backup files
            keep: Number of backups to keep
        """
        try:
            backups = sorted(
                backup_dir.glob("eon_backup_*.db"),
                key=lambda f: f.stat().st_mtime,
                reverse=True
            )

            for old_backup in backups[keep:]:
                old_backup.unlink()
                logger.debug(f"Removed old backup: {old_backup}")

        except Exception as e:
            logger.warning(f"Error cleaning up old backups: {e}")

    def _read_dataframe_with_retry(
        self,
        query: str,
        params: tuple = (),
        max_retries: int = 10
    ) -> pd.DataFrame:
        """
        Read a DataFrame from database with retry logic for database locks.

        Uses exponential backoff with jitter for reliable concurrent reads.

        Args:
            query: SQL query string
            params: Query parameters (optional)
            max_retries: Maximum number of retry attempts (default: 10)

        Returns:
            DataFrame with query results

        Raises:
            sqlite3.OperationalError: If all retries fail
        """
        last_error = None

        for attempt in range(max_retries):
            try:
                with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                    conn.execute("PRAGMA journal_mode=WAL")
                    conn.execute("PRAGMA busy_timeout=30000")
                    if params:
                        return pd.read_sql(query, conn, params=params)
                    else:
                        return pd.read_sql(query, conn)

            except sqlite3.OperationalError as e:
                last_error = e
                error_str = str(e).lower()

                is_retryable = any(keyword in error_str for keyword in [
                    "locked", "busy", "database is locked", "database is busy"
                ])

                if is_retryable and attempt < max_retries - 1:
                    base_wait = 0.1 * (2 ** attempt)
                    jitter = random.uniform(0.5, 1.5)
                    wait_time = min(base_wait * jitter, 30.0)

                    logger.warning(
                        f"Database busy/locked (read), retry {attempt + 1}/{max_retries} "
                        f"in {wait_time:.2f}s"
                    )
                    time.sleep(wait_time)
                else:
                    raise

        # Should not reach here, but return empty DataFrame as fallback
        logger.error(f"All read retries failed: {last_error}")
        return pd.DataFrame()

    # ==================== Raw Query Helpers (for DB Viewer) ====================

    def _execute_query(self, query: str, params: tuple = ()) -> pd.DataFrame:
        """
        Execute a SELECT query and return results as DataFrame.

        Args:
            query: SQL SELECT query
            params: Optional query parameters

        Returns:
            DataFrame with query results
        """
        return self._read_dataframe_with_retry(query, params=params)

    def _execute_update(self, query: str, params: tuple = ()) -> int:
        """
        Execute an UPDATE/DELETE/INSERT query.

        Args:
            query: SQL query
            params: Optional query parameters

        Returns:
            Number of rows affected
        """
        return self._execute_with_retry(query, params)

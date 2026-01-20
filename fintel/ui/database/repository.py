#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Database repository for Fintel UI - handles all database operations.

This class uses mixins to organize functionality by domain while
maintaining a single public interface.
"""

import sqlite3
import logging
import time
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

    def __init__(self, db_path: str = "data/fintel.db"):
        """
        Initialize database repository.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._init_database()

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
        max_retries: int = 5,
        fetch_one: bool = False,
        fetch_all: bool = False
    ):
        """
        Execute query with retry logic for database locks.

        Args:
            query: SQL query string
            params: Query parameters
            max_retries: Maximum number of retry attempts (default: 5)
            fetch_one: If True, return the first row as a dict (or None)
            fetch_all: If True, return all rows as a list of dicts

        Returns:
            If fetch_one: dict or None
            If fetch_all: list of dicts
            Otherwise: lastrowid for INSERT, rowcount for UPDATE/DELETE

        Raises:
            sqlite3.OperationalError: If all retries fail
        """
        for attempt in range(max_retries):
            try:
                with sqlite3.connect(self.db_path, timeout=10.0) as conn:
                    # Enable WAL mode for better concurrency
                    conn.execute("PRAGMA journal_mode=WAL")
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
                if "locked" in str(e) and attempt < max_retries - 1:
                    wait_time = 0.5 * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"Database locked, retry {attempt + 1}/{max_retries} in {wait_time}s")
                    time.sleep(wait_time)
                else:
                    raise

    def _read_dataframe_with_retry(
        self,
        query: str,
        params: tuple = (),
        max_retries: int = 5
    ) -> pd.DataFrame:
        """
        Read a DataFrame from database with retry logic for database locks.

        Args:
            query: SQL query string
            params: Query parameters (optional)
            max_retries: Maximum number of retry attempts (default: 5)

        Returns:
            DataFrame with query results

        Raises:
            sqlite3.OperationalError: If all retries fail
        """
        for attempt in range(max_retries):
            try:
                with sqlite3.connect(self.db_path, timeout=10.0) as conn:
                    conn.execute("PRAGMA journal_mode=WAL")
                    if params:
                        return pd.read_sql(query, conn, params=params)
                    else:
                        return pd.read_sql(query, conn)
            except sqlite3.OperationalError as e:
                if "locked" in str(e) and attempt < max_retries - 1:
                    wait_time = 0.5 * (2 ** attempt)
                    logger.warning(f"Database locked (read), retry {attempt + 1}/{max_retries} in {wait_time}s")
                    time.sleep(wait_time)
                else:
                    raise

        # Should not reach here, but return empty DataFrame as fallback
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

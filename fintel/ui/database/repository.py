#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Database repository for Fintel UI - handles all database operations.
"""

import sqlite3
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, date
import pandas as pd


class DatabaseRepository:
    """
    Data access layer for Streamlit UI.
    Handles all database operations with proper error handling and retry logic.
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

    def _execute_with_retry(self, query: str, params: tuple = (), max_retries: int = 3):
        """
        Execute query with retry logic for database locks.

        Args:
            query: SQL query string
            params: Query parameters
            max_retries: Maximum number of retry attempts

        Returns:
            Cursor object

        Raises:
            sqlite3.OperationalError: If all retries fail
        """
        import time

        for attempt in range(max_retries):
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute(query, params)
                    conn.commit()
                    return cursor
            except sqlite3.OperationalError as e:
                if "locked" in str(e) and attempt < max_retries - 1:
                    time.sleep(0.5 * (2 ** attempt))  # Exponential backoff
                else:
                    raise

    # ==================== Analysis Runs ====================

    def create_analysis_run(
        self,
        run_id: str,
        ticker: str,
        analysis_type: str,
        filing_type: str,
        years: List[int],
        config: Dict[str, Any],
        company_name: Optional[str] = None
    ) -> None:
        """
        Create new analysis run record.

        Args:
            run_id: Unique UUID for this run
            ticker: Company ticker symbol
            analysis_type: Type of analysis (fundamental, buffett, etc.)
            filing_type: Filing type (10-K, 10-Q, etc.)
            years: List of years to analyze
            config: Analysis configuration as dict
            company_name: Optional company name
        """
        query = """
            INSERT INTO analysis_runs
            (run_id, ticker, company_name, analysis_type, filing_type, years_analyzed, config_json, started_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        self._execute_with_retry(query, (
            run_id,
            ticker.upper(),
            company_name,
            analysis_type,
            filing_type,
            json.dumps(years),
            json.dumps(config),
            datetime.now().isoformat()
        ))

    def update_run_status(
        self,
        run_id: str,
        status: str,
        error_message: Optional[str] = None
    ) -> None:
        """
        Update analysis run status.

        Args:
            run_id: Run UUID
            status: New status (pending, running, completed, failed)
            error_message: Optional error message if failed
        """
        if status == 'completed':
            query = """
                UPDATE analysis_runs
                SET status = ?, completed_at = ?, error_message = ?
                WHERE run_id = ?
            """
            self._execute_with_retry(query, (status, datetime.now().isoformat(), error_message, run_id))
        else:
            query = """
                UPDATE analysis_runs
                SET status = ?, error_message = ?
                WHERE run_id = ?
            """
            self._execute_with_retry(query, (status, error_message, run_id))

    def update_run_progress(
        self,
        run_id: str,
        progress_message: str,
        progress_percent: Optional[int] = None,
        current_step: Optional[str] = None,
        total_steps: Optional[int] = None
    ) -> None:
        """
        Update progress tracking for an analysis run.

        Args:
            run_id: Run UUID
            progress_message: Human-readable progress message
            progress_percent: Optional progress percentage (0-100)
            current_step: Optional current step description
            total_steps: Optional total number of steps
        """
        query = """
            UPDATE analysis_runs
            SET progress_message = ?,
                progress_percent = ?,
                current_step = ?,
                total_steps = ?
            WHERE run_id = ?
        """
        self._execute_with_retry(query, (
            progress_message,
            progress_percent,
            current_step,
            total_steps,
            run_id
        ))

    def get_run_status(self, run_id: str) -> Optional[str]:
        """Get status of an analysis run."""
        query = "SELECT status FROM analysis_runs WHERE run_id = ?"
        cursor = self._execute_with_retry(query, (run_id,))
        row = cursor.fetchone()
        return row['status'] if row else None

    def get_run_details(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get full details of an analysis run."""
        query = "SELECT * FROM analysis_runs WHERE run_id = ?"
        cursor = self._execute_with_retry(query, (run_id,))
        row = cursor.fetchone()

        if row:
            return dict(row)
        return None

    def get_recent_analyses(self, limit: int = 10) -> pd.DataFrame:
        """
        Get recent analyses as DataFrame.

        Args:
            limit: Maximum number of results

        Returns:
            DataFrame with recent analyses
        """
        query = """
            SELECT
                ticker,
                analysis_type,
                filing_type,
                status,
                started_at,
                completed_at,
                run_id
            FROM analysis_runs
            ORDER BY started_at DESC
            LIMIT ?
        """
        with sqlite3.connect(self.db_path) as conn:
            return pd.read_sql(query, conn, params=(limit,))

    def search_analyses(
        self,
        ticker: Optional[str] = None,
        analysis_type: Optional[str] = None,
        status: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        limit: int = 100
    ) -> pd.DataFrame:
        """
        Search analyses with filters.

        Args:
            ticker: Filter by ticker
            analysis_type: Filter by analysis type
            status: Filter by status
            date_from: Filter by start date
            date_to: Filter by end date
            limit: Maximum results

        Returns:
            DataFrame with filtered analyses
        """
        conditions = []
        params = []

        if ticker:
            conditions.append("ticker = ?")
            params.append(ticker.upper())

        if analysis_type:
            conditions.append("analysis_type = ?")
            params.append(analysis_type)

        if status:
            conditions.append("status = ?")
            params.append(status)

        if date_from:
            conditions.append("DATE(created_at) >= ?")
            params.append(date_from.isoformat())

        if date_to:
            conditions.append("DATE(created_at) <= ?")
            params.append(date_to.isoformat())

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        query = f"""
            SELECT *
            FROM analysis_runs
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT ?
        """
        params.append(limit)

        with sqlite3.connect(self.db_path) as conn:
            return pd.read_sql(query, conn, params=params)

    def delete_analysis_run(self, run_id: str) -> None:
        """Delete an analysis run and all its results."""
        query = "DELETE FROM analysis_runs WHERE run_id = ?"
        self._execute_with_retry(query, (run_id,))

    # ==================== Analysis Results ====================

    def store_result(
        self,
        run_id: str,
        ticker: str,
        fiscal_year: int,
        filing_type: str,
        result_type: str,
        result_data: Dict[str, Any]
    ) -> None:
        """
        Store analysis result.

        Args:
            run_id: Run UUID
            ticker: Company ticker
            fiscal_year: Fiscal year
            filing_type: Filing type
            result_type: Pydantic model class name
            result_data: Result as dictionary (from model_dump())
        """
        query = """
            INSERT INTO analysis_results
            (run_id, ticker, fiscal_year, filing_type, result_type, result_json)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        self._execute_with_retry(query, (
            run_id,
            ticker.upper(),
            fiscal_year,
            filing_type,
            result_type,
            json.dumps(result_data)
        ))

    def get_analysis_results(self, run_id: str) -> List[Dict[str, Any]]:
        """
        Get all results for a run.

        Args:
            run_id: Run UUID

        Returns:
            List of result dictionaries
        """
        query = """
            SELECT fiscal_year, result_type, result_json
            FROM analysis_results
            WHERE run_id = ?
            ORDER BY fiscal_year DESC
        """
        cursor = self._execute_with_retry(query, (run_id,))

        results = []
        for row in cursor.fetchall():
            results.append({
                'year': row[0],
                'type': row[1],
                'data': json.loads(row[2])
            })
        return results

    def get_latest_result_for_ticker(
        self,
        ticker: str,
        analysis_type: str
    ) -> Optional[Dict[str, Any]]:
        """Get the most recent completed analysis for a ticker."""
        query = """
            SELECT ar.run_id, ar.completed_at
            FROM analysis_runs ar
            WHERE ar.ticker = ? AND ar.analysis_type = ? AND ar.status = 'completed'
            ORDER BY ar.completed_at DESC
            LIMIT 1
        """
        cursor = self._execute_with_retry(query, (ticker.upper(), analysis_type))
        row = cursor.fetchone()

        if row:
            run_id = row[0]
            return {
                'run_id': run_id,
                'completed_at': row[1],
                'results': self.get_analysis_results(run_id)
            }
        return None

    # ==================== Custom Prompts ====================

    def save_prompt(
        self,
        name: str,
        description: str,
        template: str,
        analysis_type: str
    ) -> int:
        """
        Save custom prompt to database.

        Args:
            name: Prompt name (unique)
            description: Prompt description
            template: Prompt template with placeholders
            analysis_type: Analysis type this prompt is for

        Returns:
            Prompt ID

        Raises:
            sqlite3.IntegrityError: If name already exists
        """
        query = """
            INSERT INTO custom_prompts (name, description, prompt_template, analysis_type)
            VALUES (?, ?, ?, ?)
        """
        cursor = self._execute_with_retry(query, (name, description, template, analysis_type))
        return cursor.lastrowid

    def get_prompts_by_type(self, analysis_type: str) -> List[Dict[str, Any]]:
        """Get all active prompts for an analysis type."""
        query = """
            SELECT id, name, description, prompt_template, created_at
            FROM custom_prompts
            WHERE analysis_type = ? AND is_active = 1
            ORDER BY created_at DESC
        """
        cursor = self._execute_with_retry(query, (analysis_type,))

        prompts = []
        for row in cursor.fetchall():
            prompts.append({
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'template': row[3],
                'created_at': row[4]
            })
        return prompts

    def get_prompt_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get prompt by name."""
        query = "SELECT * FROM custom_prompts WHERE name = ? AND is_active = 1"
        cursor = self._execute_with_retry(query, (name,))
        row = cursor.fetchone()

        if row:
            return dict(row)
        return None

    def update_prompt(self, prompt_id: int, **fields) -> None:
        """Update prompt fields."""
        allowed_fields = ['name', 'description', 'prompt_template', 'analysis_type']
        updates = []
        params = []

        for field, value in fields.items():
            if field in allowed_fields:
                updates.append(f"{field} = ?")
                params.append(value)

        if updates:
            updates.append("updated_at = ?")
            params.append(datetime.now().isoformat())
            params.append(prompt_id)

            query = f"UPDATE custom_prompts SET {', '.join(updates)} WHERE id = ?"
            self._execute_with_retry(query, tuple(params))

    def delete_prompt(self, prompt_id: int) -> None:
        """Soft delete a prompt (set is_active = 0)."""
        query = "UPDATE custom_prompts SET is_active = 0 WHERE id = ?"
        self._execute_with_retry(query, (prompt_id,))

    # ==================== File Cache ====================

    def cache_file(
        self,
        ticker: str,
        fiscal_year: int,
        filing_type: str,
        file_path: str,
        file_hash: Optional[str] = None
    ) -> None:
        """Cache downloaded file information."""
        query = """
            INSERT OR REPLACE INTO file_cache
            (ticker, fiscal_year, filing_type, file_path, file_hash, downloaded_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        self._execute_with_retry(query, (
            ticker.upper(),
            fiscal_year,
            filing_type,
            file_path,
            file_hash,
            datetime.now().isoformat()
        ))

    def get_cached_file(
        self,
        ticker: str,
        fiscal_year: int,
        filing_type: str
    ) -> Optional[str]:
        """Get cached file path if exists."""
        query = """
            SELECT file_path
            FROM file_cache
            WHERE ticker = ? AND fiscal_year = ? AND filing_type = ?
        """
        cursor = self._execute_with_retry(query, (ticker.upper(), fiscal_year, filing_type))
        row = cursor.fetchone()
        return row[0] if row else None

    def clear_file_cache(self, older_than_days: Optional[int] = None) -> int:
        """
        Clear file cache.

        Args:
            older_than_days: Clear files older than this many days (None = all)

        Returns:
            Number of records deleted
        """
        if older_than_days:
            query = """
                DELETE FROM file_cache
                WHERE julianday('now') - julianday(downloaded_at) > ?
            """
            cursor = self._execute_with_retry(query, (older_than_days,))
        else:
            query = "DELETE FROM file_cache"
            cursor = self._execute_with_retry(query)

        return cursor.rowcount

    # ==================== User Settings ====================

    def set_setting(self, key: str, value: str) -> None:
        """Set user setting."""
        query = """
            INSERT OR REPLACE INTO user_settings (key, value, updated_at)
            VALUES (?, ?, ?)
        """
        self._execute_with_retry(query, (key, value, datetime.now().isoformat()))

    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get user setting."""
        query = "SELECT value FROM user_settings WHERE key = ?"
        cursor = self._execute_with_retry(query, (key,))
        row = cursor.fetchone()
        return row[0] if row else default

    # ==================== Statistics ====================

    def get_total_analyses(self) -> int:
        """Get total number of analyses."""
        query = "SELECT COUNT(*) FROM analysis_runs"
        cursor = self._execute_with_retry(query)
        return cursor.fetchone()[0]

    def get_running_analyses_count(self) -> int:
        """Get number of currently running analyses."""
        query = "SELECT COUNT(*) FROM analysis_runs WHERE status = 'running'"
        cursor = self._execute_with_retry(query)
        return cursor.fetchone()[0]

    def get_analyses_today(self) -> int:
        """Get number of analyses created today."""
        query = "SELECT COUNT(*) FROM analysis_runs WHERE DATE(created_at) = DATE('now')"
        cursor = self._execute_with_retry(query)
        return cursor.fetchone()[0]

    def get_unique_tickers_count(self) -> int:
        """Get number of unique tickers analyzed."""
        query = "SELECT COUNT(DISTINCT ticker) FROM analysis_runs WHERE status = 'completed'"
        cursor = self._execute_with_retry(query)
        return cursor.fetchone()[0]

    def get_stats_by_type(self) -> pd.DataFrame:
        """Get analysis statistics by type."""
        query = """
            SELECT
                analysis_type,
                status,
                COUNT(*) as count
            FROM analysis_runs
            GROUP BY analysis_type, status
        """
        with sqlite3.connect(self.db_path) as conn:
            return pd.read_sql(query, conn)

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
        with sqlite3.connect(self.db_path) as conn:
            return pd.read_sql(query, conn, params=params)

    def _execute_update(self, query: str, params: tuple = ()) -> int:
        """
        Execute an UPDATE/DELETE/INSERT query.

        Args:
            query: SQL query
            params: Optional query parameters

        Returns:
            Number of rows affected
        """
        cursor = self._execute_with_retry(query, params)
        return cursor.rowcount

    # ==================== User Settings ====================

    def get_setting(self, key: str, default: Any = None) -> Any:
        """
        Get a user setting value.

        Args:
            key: Setting key
            default: Default value if not found

        Returns:
            Setting value or default
        """
        query = "SELECT value FROM user_settings WHERE key = ?"
        cursor = self._execute_with_retry(query, (key,))
        row = cursor.fetchone()
        return row[0] if row else default

    def save_setting(self, key: str, value: str) -> None:
        """
        Save a user setting.

        Args:
            key: Setting key
            value: Setting value
        """
        query = """
            INSERT INTO user_settings (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = CURRENT_TIMESTAMP
        """
        self._execute_with_retry(query, (key, str(value)))

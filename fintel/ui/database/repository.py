#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Database repository for Fintel UI - handles all database operations.
"""

import sqlite3
import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, date
import pandas as pd

logger = logging.getLogger(__name__)


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

    def _execute_with_retry(self, query: str, params: tuple = (), max_retries: int = 5):
        """
        Execute query with retry logic for database locks.

        Args:
            query: SQL query string
            params: Query parameters
            max_retries: Maximum number of retry attempts (default: 5, increased from 3)

        Returns:
            Cursor object

        Raises:
            sqlite3.OperationalError: If all retries fail
        """
        import time

        for attempt in range(max_retries):
            try:
                with sqlite3.connect(self.db_path, timeout=10.0) as conn:  # Add 10s timeout
                    # Enable WAL mode for better concurrency
                    conn.execute("PRAGMA journal_mode=WAL")
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute(query, params)
                    conn.commit()
                    return cursor
            except sqlite3.OperationalError as e:
                if "locked" in str(e) and attempt < max_retries - 1:
                    wait_time = 0.5 * (2 ** attempt)  # Exponential backoff: 0.5s, 1s, 2s, 4s, 8s
                    logger.warning(f"Database locked, retry {attempt + 1}/{max_retries} in {wait_time}s")
                    time.sleep(wait_time)
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
            datetime.utcnow().isoformat()
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
        now = datetime.utcnow().isoformat()
        if status == 'completed':
            query = """
                UPDATE analysis_runs
                SET status = ?, completed_at = ?, error_message = ?, last_activity_at = ?
                WHERE run_id = ?
            """
            self._execute_with_retry(query, (status, now, error_message, now, run_id))
        elif status == 'running':
            # Set last_activity_at when transitioning to running
            query = """
                UPDATE analysis_runs
                SET status = ?, error_message = ?, last_activity_at = ?
                WHERE run_id = ?
            """
            self._execute_with_retry(query, (status, error_message, now, run_id))
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
                total_steps = ?,
                last_activity_at = ?
            WHERE run_id = ?
        """
        self._execute_with_retry(query, (
            progress_message,
            progress_percent,
            current_step,
            total_steps,
            datetime.utcnow().isoformat(),
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
                created_at,
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

    def get_existing_results(
        self,
        ticker: str,
        analysis_type: str,
        years: List[int],
        filing_type: str = "10-K",
        max_age_days: int = 30
    ) -> Dict[int, Dict[str, Any]]:
        """
        Check for existing completed results for specific years.

        Used for caching - skip re-analyzing years we already have recent results for.

        Args:
            ticker: Company ticker
            analysis_type: Type of analysis
            years: List of years to check
            filing_type: Filing type
            max_age_days: Maximum age of cached results in days

        Returns:
            Dictionary mapping year to result data for years with existing results
        """
        if not years:
            return {}

        placeholders = ",".join("?" * len(years))
        query = f"""
            SELECT
                r.fiscal_year,
                r.result_type,
                r.result_json,
                ar.completed_at
            FROM analysis_results r
            JOIN analysis_runs ar ON r.run_id = ar.run_id
            WHERE
                ar.ticker = ?
                AND ar.analysis_type = ?
                AND ar.filing_type = ?
                AND ar.status = 'completed'
                AND r.fiscal_year IN ({placeholders})
                AND julianday('now') - julianday(ar.completed_at) <= ?
            ORDER BY ar.completed_at DESC
        """

        params = [ticker.upper(), analysis_type, filing_type] + years + [max_age_days]

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(query, params)

                # Get most recent result per year
                results = {}
                for row in cursor.fetchall():
                    year = row['fiscal_year']
                    if year not in results:  # Keep first (most recent) result
                        results[year] = {
                            'year': year,
                            'type': row['result_type'],
                            'data': json.loads(row['result_json']),
                            'cached_at': row['completed_at']
                        }

                return results
        except Exception as e:
            logger.warning(f"Error checking for existing results: {e}")
            return {}

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
            params.append(datetime.utcnow().isoformat())
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
            datetime.utcnow().isoformat()
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

    def get_cache_count(self) -> int:
        """
        Get count of cached files.

        Returns:
            Number of cached files in the database
        """
        query = "SELECT COUNT(*) FROM file_cache"
        cursor = self._execute_with_retry(query)
        return cursor.fetchone()[0]

    def cache_filing_types(self, ticker: str, filing_types: List[str]) -> None:
        """
        Cache available filing types for a ticker.

        Args:
            ticker: Company ticker symbol
            filing_types: List of available filing types
        """
        query = """
            INSERT OR REPLACE INTO filing_types_cache
            (ticker, filing_types, cached_at)
            VALUES (?, ?, ?)
        """
        self._execute_with_retry(query, (
            ticker.upper(),
            json.dumps(filing_types),
            datetime.utcnow().isoformat()
        ))

    def get_cached_filing_types(
        self,
        ticker: str,
        max_age_hours: int = 24
    ) -> Optional[List[str]]:
        """
        Get cached filing types for a ticker if cache is fresh.

        Args:
            ticker: Company ticker symbol
            max_age_hours: Maximum cache age in hours (default: 24)

        Returns:
            List of filing types if cache exists and is fresh, None otherwise
        """
        query = """
            SELECT filing_types, cached_at
            FROM filing_types_cache
            WHERE ticker = ?
        """
        cursor = self._execute_with_retry(query, (ticker.upper(),))
        row = cursor.fetchone()

        if not row:
            return None

        filing_types_json, cached_at_str = row[0], row[1]

        # Check if cache is still fresh
        cached_at = datetime.fromisoformat(cached_at_str)
        age_hours = (datetime.utcnow() - cached_at).total_seconds() / 3600

        if age_hours > max_age_hours:
            return None

        return json.loads(filing_types_json)

    def clear_filing_types_cache(self, ticker: Optional[str] = None) -> int:
        """
        Clear filing types cache.

        Args:
            ticker: Clear cache for specific ticker (None = all)

        Returns:
            Number of records deleted
        """
        if ticker:
            query = "DELETE FROM filing_types_cache WHERE ticker = ?"
            cursor = self._execute_with_retry(query, (ticker.upper(),))
        else:
            query = "DELETE FROM filing_types_cache"
            cursor = self._execute_with_retry(query)

        return cursor.rowcount

    # ==================== User Settings ====================

    def set_setting(self, key: str, value: str) -> None:
        """Set user setting."""
        query = """
            INSERT OR REPLACE INTO user_settings (key, value, updated_at)
            VALUES (?, ?, ?)
        """
        self._execute_with_retry(query, (key, value, datetime.utcnow().isoformat()))

    # ==================== Resume Functionality ====================

    def update_last_activity(self, run_id: str) -> None:
        """Update the last activity timestamp for a run."""
        query = """
            UPDATE analysis_runs
            SET last_activity_at = ?
            WHERE run_id = ?
        """
        self._execute_with_retry(query, (datetime.utcnow().isoformat(), run_id))

    def mark_year_completed(self, run_id: str, year: int) -> None:
        """
        Mark a year as completed within a multi-year analysis run.

        Args:
            run_id: Run UUID
            year: The year that was completed
        """
        # Get current completed years
        query = "SELECT completed_years FROM analysis_runs WHERE run_id = ?"
        cursor = self._execute_with_retry(query, (run_id,))
        row = cursor.fetchone()

        if row:
            completed = json.loads(row[0]) if row[0] else []
            if year not in completed:
                completed.append(year)
                completed.sort(reverse=True)

            # Update with new list
            update_query = """
                UPDATE analysis_runs
                SET completed_years = ?, last_activity_at = ?
                WHERE run_id = ?
            """
            self._execute_with_retry(update_query, (
                json.dumps(completed),
                datetime.utcnow().isoformat(),
                run_id
            ))

    def get_completed_years(self, run_id: str) -> List[int]:
        """Get list of years already completed for a run."""
        query = "SELECT completed_years FROM analysis_runs WHERE run_id = ?"
        cursor = self._execute_with_retry(query, (run_id,))
        row = cursor.fetchone()

        if row and row[0]:
            return json.loads(row[0])
        return []

    def get_interrupted_runs(self, stale_minutes: int = 10) -> List[Dict[str, Any]]:
        """
        Get runs that appear to be interrupted (running but no recent activity).

        Args:
            stale_minutes: Consider run stale if no activity for this many minutes

        Returns:
            List of interrupted run details
        """
        query = """
            SELECT
                run_id,
                ticker,
                company_name,
                analysis_type,
                filing_type,
                years_analyzed,
                completed_years,
                started_at,
                last_activity_at,
                progress_message,
                progress_percent,
                current_step,
                total_steps
            FROM analysis_runs
            WHERE status = 'running'
            AND (
                last_activity_at IS NULL
                OR (julianday('now') - julianday(last_activity_at)) * 24 * 60 > ?
            )
            ORDER BY started_at DESC
        """

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(query, (stale_minutes,))

                runs = []
                for row in cursor.fetchall():
                    years_analyzed = json.loads(row['years_analyzed']) if row['years_analyzed'] else []
                    completed_years = json.loads(row['completed_years']) if row['completed_years'] else []
                    remaining_years = [y for y in years_analyzed if y not in completed_years]

                    runs.append({
                        'run_id': row['run_id'],
                        'ticker': row['ticker'],
                        'company_name': row['company_name'],
                        'analysis_type': row['analysis_type'],
                        'filing_type': row['filing_type'],
                        'years_analyzed': years_analyzed,
                        'completed_years': completed_years,
                        'remaining_years': remaining_years,
                        'started_at': row['started_at'],
                        'last_activity_at': row['last_activity_at'],
                        'progress_message': row['progress_message'],
                        'progress_percent': row['progress_percent'] or 0,
                        'current_step': row['current_step'],
                        'total_steps': row['total_steps'] or 0,
                    })

                return runs

        except Exception as e:
            logger.warning(f"Error getting interrupted runs: {e}")
            return []

    def mark_run_as_interrupted(self, run_id: str) -> None:
        """Mark a running run as interrupted (for manual cleanup)."""
        query = """
            UPDATE analysis_runs
            SET status = 'interrupted', error_message = 'Analysis was interrupted and can be resumed'
            WHERE run_id = ? AND status = 'running'
        """
        self._execute_with_retry(query, (run_id,))

    def prepare_for_resume(self, run_id: str) -> bool:
        """
        Prepare a run for resumption by resetting its status.

        Args:
            run_id: Run UUID

        Returns:
            True if run can be resumed, False otherwise
        """
        # Check if run exists and has remaining work
        query = """
            SELECT status, years_analyzed, completed_years
            FROM analysis_runs
            WHERE run_id = ?
        """
        cursor = self._execute_with_retry(query, (run_id,))
        row = cursor.fetchone()

        if not row:
            return False

        status = row[0]
        years = json.loads(row[1]) if row[1] else []
        completed = json.loads(row[2]) if row[2] else []

        # Only resume if there's remaining work
        remaining = [y for y in years if y not in completed]
        if not remaining:
            return False

        # Reset status to running
        if status in ('interrupted', 'failed', 'running'):
            update_query = """
                UPDATE analysis_runs
                SET status = 'running',
                    error_message = NULL,
                    last_activity_at = ?
                WHERE run_id = ?
            """
            self._execute_with_retry(update_query, (datetime.utcnow().isoformat(), run_id))
            return True

        return False

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

    # ==================== API Usage Tracking ====================

    def record_api_usage(self, api_key: str, count: int = 1) -> None:
        """
        Record API usage for a key.

        Args:
            api_key: The API key (will be masked to last 4 chars)
            count: Number of requests to record (default: 1)
        """
        key_suffix = api_key[-4:] if len(api_key) >= 4 else "****"
        today = datetime.utcnow().strftime('%Y-%m-%d')

        query = """
            INSERT INTO api_usage (api_key_suffix, usage_date, request_count, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(api_key_suffix, usage_date) DO UPDATE SET
                request_count = request_count + ?,
                updated_at = CURRENT_TIMESTAMP
        """
        self._execute_with_retry(query, (key_suffix, today, count, count))

    def get_api_usage_today(self, api_key: str = None) -> int:
        """
        Get API usage count for today.

        Args:
            api_key: Optional specific key (masked to last 4 chars). If None, returns total.

        Returns:
            Number of API calls today
        """
        today = datetime.utcnow().strftime('%Y-%m-%d')

        if api_key:
            key_suffix = api_key[-4:] if len(api_key) >= 4 else "****"
            query = "SELECT request_count FROM api_usage WHERE api_key_suffix = ? AND usage_date = ?"
            cursor = self._execute_with_retry(query, (key_suffix, today))
            row = cursor.fetchone()
            return row[0] if row else 0
        else:
            query = "SELECT SUM(request_count) FROM api_usage WHERE usage_date = ?"
            cursor = self._execute_with_retry(query, (today,))
            row = cursor.fetchone()
            return row[0] if row and row[0] else 0

    def get_api_usage_history(self, days: int = 30) -> pd.DataFrame:
        """
        Get API usage history.

        Args:
            days: Number of days to look back (default: 30)

        Returns:
            DataFrame with columns: api_key_suffix, usage_date, request_count
        """
        query = """
            SELECT api_key_suffix, usage_date, request_count
            FROM api_usage
            WHERE usage_date >= DATE('now', ?)
            ORDER BY usage_date DESC, api_key_suffix
        """
        with sqlite3.connect(self.db_path) as conn:
            return pd.read_sql(query, conn, params=(f'-{days} days',))

    def get_api_usage_summary(self) -> pd.DataFrame:
        """
        Get API usage summary by key.

        Returns:
            DataFrame with columns: api_key_suffix, total_requests, first_used, last_used
        """
        query = """
            SELECT
                api_key_suffix,
                SUM(request_count) as total_requests,
                MIN(usage_date) as first_used,
                MAX(usage_date) as last_used,
                COUNT(DISTINCT usage_date) as days_active
            FROM api_usage
            GROUP BY api_key_suffix
            ORDER BY total_requests DESC
        """
        with sqlite3.connect(self.db_path) as conn:
            return pd.read_sql(query, conn)

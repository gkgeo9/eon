"""
Load analysis results from the EON database for backtesting.
"""

import json
import logging
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .signals import CompositeSignal, extract_signal

logger = logging.getLogger(__name__)

# Default database path
DEFAULT_DB_PATH = Path("data/eon.db")


def load_all_multi_analysis_signals(
    db_path: Optional[Path] = None,
    max_fiscal_year: int = 2024,
    min_fiscal_year: int = 0,
    batch_name: Optional[str] = None,
) -> List[CompositeSignal]:
    """
    Load all SimplifiedAnalysis results from the database and extract signals.

    Only loads results for fiscal years between min_fiscal_year and max_fiscal_year
    (inclusive) so we can measure forward returns without look-ahead bias.

    Args:
        db_path: Path to eon.db. Defaults to data/eon.db.
        max_fiscal_year: Maximum fiscal year to include (exclusive of 2025+).
        min_fiscal_year: Minimum fiscal year to include (0 = no lower bound).
        batch_name: If provided, only load from this specific batch.

    Returns:
        List of CompositeSignal objects.
    """
    db_path = db_path or DEFAULT_DB_PATH

    if not db_path.exists():
        logger.error(f"Database not found at {db_path}")
        return []

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    try:
        if batch_name:
            signals = _load_from_batch(conn, batch_name, max_fiscal_year, min_fiscal_year)
        else:
            signals = _load_all(conn, max_fiscal_year, min_fiscal_year)
    finally:
        conn.close()

    year_range = f"{min_fiscal_year}-{max_fiscal_year}" if min_fiscal_year else f"<= {max_fiscal_year}"
    logger.info(
        f"Loaded {len(signals)} signals (fiscal years {year_range})"
    )
    return signals


def _load_from_batch(
    conn: sqlite3.Connection,
    batch_name: str,
    max_fiscal_year: int,
    min_fiscal_year: int = 0,
) -> List[CompositeSignal]:
    """Load signals from a specific batch."""
    cursor = conn.cursor()

    # Find the batch
    cursor.execute(
        "SELECT batch_id FROM batch_jobs WHERE name = ?",
        (batch_name,),
    )
    row = cursor.fetchone()
    if not row:
        logger.warning(f"Batch '{batch_name}' not found")
        return []

    batch_id = row["batch_id"]

    cursor.execute(
        """
        SELECT ar.ticker, ar.fiscal_year, ar.result_json
        FROM analysis_results ar
        JOIN batch_items bi ON ar.run_id = bi.run_id
        WHERE bi.batch_id = ?
          AND ar.result_type = 'SimplifiedAnalysis'
          AND ar.fiscal_year <= ?
          AND ar.fiscal_year >= ?
        ORDER BY ar.ticker, ar.fiscal_year
        """,
        (batch_id, max_fiscal_year, min_fiscal_year),
    )

    return _rows_to_signals(cursor.fetchall())


def _load_all(
    conn: sqlite3.Connection,
    max_fiscal_year: int,
    min_fiscal_year: int = 0,
) -> List[CompositeSignal]:
    """Load all SimplifiedAnalysis signals from the database."""
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT ar.ticker, ar.fiscal_year, ar.result_json
        FROM analysis_results ar
        JOIN analysis_runs runs ON ar.run_id = runs.run_id
        WHERE ar.result_type = 'SimplifiedAnalysis'
          AND ar.fiscal_year <= ?
          AND ar.fiscal_year >= ?
          AND runs.status = 'completed'
        ORDER BY ar.ticker, ar.fiscal_year
        """,
        (max_fiscal_year, min_fiscal_year),
    )

    return _rows_to_signals(cursor.fetchall())


def _rows_to_signals(rows: list) -> List[CompositeSignal]:
    """Convert database rows to CompositeSignal objects."""
    signals = []
    for row in rows:
        try:
            data = json.loads(row["result_json"])
            signal = extract_signal(
                ticker=row["ticker"],
                fiscal_year=row["fiscal_year"],
                result_data=data,
            )
            signals.append(signal)
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(
                f"Failed to parse result for {row['ticker']} "
                f"FY{row['fiscal_year']}: {e}"
            )
    return signals


def get_unique_tickers(signals: List[CompositeSignal]) -> List[str]:
    """Get sorted list of unique tickers from signals."""
    return sorted(set(s.ticker for s in signals))


def get_signal_summary(signals: List[CompositeSignal]) -> Dict[str, int]:
    """Get counts by signal strength."""
    from .signals import SignalStrength

    summary = {s.value: 0 for s in SignalStrength}
    for signal in signals:
        summary[signal.strength.value] += 1
    return summary

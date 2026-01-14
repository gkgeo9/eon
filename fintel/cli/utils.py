"""
CLI utility functions shared across commands.

Provides common functionality for ticker file reading and validation.
"""

from pathlib import Path
from typing import List

from fintel.core import get_logger

logger = get_logger(__name__)


def read_ticker_file(ticker_path: Path) -> List[str]:
    """
    Read ticker symbols from a file (CSV or text).

    Supports CSV files with common column names (ticker, symbol, stock, company)
    and plain text files with one ticker per line.

    Args:
        ticker_path: Path to ticker file

    Returns:
        List of unique ticker symbols (uppercase, duplicates removed)

    Raises:
        ValueError: If file cannot be read or contains no valid tickers
    """
    tickers = []

    try:
        if ticker_path.suffix.lower() == ".csv":
            import pandas as pd
            df = pd.read_csv(ticker_path)

            # Look for ticker column by common names
            ticker_col = None
            for col in df.columns:
                if col.lower() in ["ticker", "symbol", "stock", "company"]:
                    ticker_col = col
                    break

            if ticker_col:
                tickers = df[ticker_col].dropna().astype(str).str.upper().tolist()
                logger.debug(f"Found ticker column '{ticker_col}' with {len(tickers)} entries")
            else:
                # Fall back to first column with warning
                logger.warning(
                    f"No recognized ticker column found in {ticker_path}. "
                    f"Using first column '{df.columns[0]}'. "
                    f"Expected columns: ticker, symbol, stock, or company."
                )
                tickers = df.iloc[:, 0].dropna().astype(str).str.upper().tolist()
        else:
            # Text file, one ticker per line
            with open(ticker_path, "r") as f:
                tickers = [line.strip().upper() for line in f if line.strip()]

        # Remove duplicates while preserving order
        seen = set()
        unique_tickers = []
        for ticker in tickers:
            # Basic validation: ticker should be 1-5 alphanumeric characters
            if ticker and ticker not in seen:
                if ticker.isalnum() and 1 <= len(ticker) <= 5:
                    seen.add(ticker)
                    unique_tickers.append(ticker)
                else:
                    logger.warning(f"Skipping invalid ticker format: '{ticker}'")

        duplicates_removed = len(tickers) - len(unique_tickers)
        if duplicates_removed > 0:
            logger.info(f"Removed {duplicates_removed} duplicate tickers")

        return unique_tickers

    except Exception as e:
        logger.error(f"Error reading ticker file {ticker_path}: {e}")
        raise ValueError(f"Failed to read ticker file: {e}") from e

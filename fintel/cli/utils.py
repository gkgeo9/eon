"""
CLI utility functions shared across commands.

Provides common functionality for ticker file reading, validation,
and custom Click parameter types.
"""

import click
from pathlib import Path
from typing import List

from fintel.core import get_logger
from fintel.core.analysis_types import CLI_ANALYSIS_CHOICES

logger = get_logger(__name__)


class AnalysisTypeParam(click.ParamType):
    """
    Custom Click parameter type that accepts both built-in analysis types
    and ``custom:<workflow_id>`` values.

    Built-in types are validated against CLI_ANALYSIS_CHOICES.
    Custom workflow IDs (``custom:*``) are validated against the
    auto-discovered workflow registry.
    """

    name = "analysis_type"

    def get_metavar(self, param):
        choices_str = "|".join(CLI_ANALYSIS_CHOICES)
        return f"[{choices_str}|custom:<id>]"

    def convert(self, value, param, ctx):
        # Accept built-in types (case-insensitive)
        lower = value.lower()
        if lower in CLI_ANALYSIS_CHOICES:
            return lower

        # Accept custom:<workflow_id>
        if lower.startswith("custom:"):
            workflow_id = value.split(":", 1)[1]  # preserve original case for ID
            if not workflow_id:
                self.fail(
                    "Missing workflow ID after 'custom:'. "
                    "Use 'fintel workflows' to list available IDs.",
                    param, ctx,
                )

            # Validate the workflow actually exists
            from custom_workflows import get_workflow
            if get_workflow(workflow_id) is None:
                self.fail(
                    f"Unknown custom workflow: '{workflow_id}'. "
                    f"Run 'fintel workflows' to see available workflows.",
                    param, ctx,
                )
            return f"custom:{workflow_id}"

        self.fail(
            f"Invalid analysis type: '{value}'. "
            f"Valid built-in types: {', '.join(CLI_ANALYSIS_CHOICES)}. "
            f"For custom workflows use: custom:<workflow_id> "
            f"(run 'fintel workflows' to list them).",
            param, ctx,
        )


# Singleton instance for use in Click options
ANALYSIS_TYPE = AnalysisTypeParam()


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

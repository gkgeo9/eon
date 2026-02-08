#!/usr/bin/env python3
"""
CLI entry point for the EON backtester.

Usage:
    python -m experimental.backtester.run_backtest [OPTIONS]

Examples:
    # Backtest all signals from database
    python -m experimental.backtester.run_backtest

    # Backtest a specific batch
    python -m experimental.backtester.run_backtest --batch high_put_call_ratio

    # Custom fiscal year range and output
    python -m experimental.backtester.run_backtest --min-year 2015 --max-year 2023 --output data/bt

    # With AlphaVantage fallback
    python -m experimental.backtester.run_backtest --av-key YOUR_KEY
"""

import argparse
import logging
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="Backtest EON multi-perspective analysis signals for alpha.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Signal Strength Groups:
  ALL_PRIORITY      All 3 perspectives (Buffett, Taleb, Contrarian) signal PRIORITY
  MAJORITY_PRIORITY 2+ perspectives signal PRIORITY
  ANY_PRIORITY      At least 1 perspective signals PRIORITY
  NO_SIGNAL         No perspectives signal PRIORITY (control group)

Holding Periods (trading days):
  1M = 21 days, 3M = 63 days, 6M = 126 days, 1Y = 252 days, 2Y = 504 days, 5Y = 1260 days

The backtester compares forward stock returns against SPY (S&P 500) to
determine whether STRONG signals generate true alpha.
        """,
    )

    parser.add_argument(
        "--db",
        type=Path,
        default=None,
        help="Path to eon.db (default: data/eon.db)",
    )
    parser.add_argument(
        "--batch",
        type=str,
        default=None,
        help="Only backtest signals from this batch name",
    )
    parser.add_argument(
        "--min-year",
        type=int,
        default=0,
        help="Min fiscal year to include (default: 0 = no lower bound)",
    )
    parser.add_argument(
        "--max-year",
        type=int,
        default=2024,
        help="Max fiscal year to include (default: 2024, excludes 2025+)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/backtest_results"),
        help="Output directory for CSV results (default: data/backtest_results)",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=None,
        help="Price data cache directory (default: data/price_cache)",
    )
    parser.add_argument(
        "--av-key",
        type=str,
        default=None,
        help="AlphaVantage API key for price data fallback",
    )
    parser.add_argument(
        "--periods",
        type=str,
        default="21,63,126,252,504,1260",
        help="Comma-separated holding periods in trading days (default: 21,63,126,252,504,1260)",
    )
    parser.add_argument(
        "--no-export",
        action="store_true",
        help="Skip CSV export, only print report",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Setup logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # Parse holding periods
    holding_periods = [int(p.strip()) for p in args.periods.split(",")]

    print("=" * 70)
    print("EON BACKTESTER - Multi-Perspective Signal Alpha Analysis")
    print("=" * 70)
    print(f"  Database:        {args.db or 'data/eon.db'}")
    print(f"  Batch filter:    {args.batch or 'all batches'}")
    min_yr_display = str(args.min_year) if args.min_year else "earliest"
    print(f"  Fiscal years:    {min_yr_display} - {args.max_year}")
    print(f"  Holding periods: {', '.join(str(p) + 'd' for p in holding_periods)}")
    print(f"  Output:          {args.output}")
    print(f"  AlphaVantage:    {'configured' if args.av_key else 'not configured'}")

    # Import here to allow --help without dependencies
    from .backtester import Backtester

    bt = Backtester(
        db_path=args.db,
        cache_dir=args.cache_dir,
        alphavantage_key=args.av_key,
        max_fiscal_year=args.max_year,
        min_fiscal_year=args.min_year,
        holding_periods=holding_periods,
        batch_name=args.batch,
    )

    results = bt.run()

    if not args.no_export and results:
        bt.export(output_dir=args.output)

    if not results:
        print("\nNo results generated. Check that the database has analysis data.")
        sys.exit(1)

    print("\nBacktest complete.")


if __name__ == "__main__":
    main()

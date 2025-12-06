#!/usr/bin/env python3
"""
Example: Batch processing multiple companies in parallel.

This script demonstrates how to process multiple companies in parallel
using the ParallelProcessor for maximum efficiency.
"""

from pathlib import Path
from fintel.core import get_config
from fintel.processing import ParallelProcessor


def main():
    """Process multiple tech companies in parallel."""

    config = get_config()

    # Define companies to analyze
    tickers = ["AAPL", "MSFT", "GOOGL", "NVDA", "TSLA"]
    num_filings = 10
    num_workers = min(5, len(config.google_api_keys))

    print(f"🚀 Batch Processing {len(tickers)} Companies")
    print("=" * 60)
    print(f"  Tickers: {', '.join(tickers)}")
    print(f"  Filings per company: {num_filings}")
    print(f"  Parallel workers: {num_workers}")
    print("=" * 60)

    # Create parallel processor
    processor = ParallelProcessor(
        api_keys=config.google_api_keys[:num_workers],
        session_id="example_batch"
    )

    # Process batch
    print("\n⏳ Starting parallel processing...")
    print("Note: This will take a while due to rate limiting (65s per API call)")

    results = processor.process_batch(
        tickers=tickers,
        num_filings=num_filings,
        output_dir=config.data_dir / "batch_results"
    )

    # Display results
    print("\n" + "=" * 60)
    print("📊 Batch Processing Results")
    print("=" * 60)

    successful = 0
    failed = 0

    for ticker, result in results.items():
        if result.get("success"):
            status = "✓"
            successful += 1
        else:
            status = "✗"
            failed += 1

        filings = result.get("filings_processed", 0)
        error = result.get("error", "")

        print(f"{status} {ticker}: {filings} filings processed {error}")

    print(f"\n📈 Summary: {successful} successful, {failed} failed")
    print(f"✓ Results saved to: {config.data_dir}/batch_results")


if __name__ == "__main__":
    main()

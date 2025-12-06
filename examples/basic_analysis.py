#!/usr/bin/env python3
"""
Example: Basic single-company fundamental analysis.

This script demonstrates how to analyze a single company's 10-K filings
using the Fintel platform.
"""

from pathlib import Path
from fintel.core import get_config
from fintel.data.sources.sec import SECDownloader, SECConverter
from fintel.analysis.fundamental import FundamentalAnalyzer, TenKAnalysis
from fintel.ai import APIKeyManager, RateLimiter


def main():
    """Run basic analysis for Apple (AAPL)."""

    # Configuration
    config = get_config()
    ticker = "AAPL"
    num_years = 5

    print(f"🔍 Analyzing {ticker} - {num_years} years of 10-K filings")
    print("=" * 60)

    # Step 1: Download 10-K filings
    print(f"\n📥 Step 1: Downloading {num_years} 10-K filings...")
    downloader = SECDownloader(
        company_name="Fintel Example",
        user_email="user@example.com"
    )
    filing_path = downloader.download(ticker, num_filings=num_years)
    print(f"✓ Downloaded to: {filing_path}")

    # Step 2: Convert HTML to PDF
    print("\n📄 Step 2: Converting HTML to PDF...")
    with SECConverter() as converter:
        pdf_paths = converter.convert_batch(ticker, filing_path)
    print(f"✓ Converted {len(pdf_paths)} filings to PDF")

    # Step 3: Analyze with AI
    print("\n🤖 Step 3: Analyzing with AI (this will take a while)...")

    # Initialize AI components
    key_mgr = APIKeyManager(config.google_api_keys)
    rate_limiter = RateLimiter(sleep_after_request=config.sleep_after_request)

    analyzer = FundamentalAnalyzer(
        api_key_manager=key_mgr,
        rate_limiter=rate_limiter
    )

    # Analyze each filing
    results = []
    for i, pdf_path in enumerate(sorted(pdf_paths)[:num_years]):
        year = 2024 - i

        print(f"  Analyzing {year}...")
        result = analyzer.analyze_filing(
            pdf_path=pdf_path,
            ticker=ticker,
            year=year,
            schema=TenKAnalysis,
            output_dir=config.data_dir / "processed" / ticker
        )

        if result:
            results.append((year, result))
            print(f"  ✓ {year} complete")
        else:
            print(f"  ✗ {year} failed")

    # Display summary
    print("\n" + "=" * 60)
    print(f"📊 Analysis Summary for {ticker}")
    print("=" * 60)

    for year, result in results:
        print(f"\n{year}:")
        print(f"  Business Model: {result.business_model[:100]}...")
        print(f"  Revenue: {result.financial_highlights.revenue}")
        print(f"  Key Strategies: {', '.join(result.key_strategies[:2])}")

    print(f"\n✓ Complete! Results saved to: {config.data_dir}/processed/{ticker}")


if __name__ == "__main__":
    main()

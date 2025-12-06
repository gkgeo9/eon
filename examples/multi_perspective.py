#!/usr/bin/env python3
"""
Example: Multi-perspective analysis (Buffett, Taleb, Contrarian).

This script demonstrates how to analyze a company through three different
investment lenses to get a comprehensive view.
"""

from pathlib import Path
from fintel.core import get_config
from fintel.data.sources.sec import SECDownloader, SECConverter
from fintel.analysis.perspectives import PerspectiveAnalyzer
from fintel.ai import APIKeyManager, RateLimiter


def main():
    """Analyze Netflix through multiple perspectives."""

    config = get_config()
    ticker = "NFLX"
    year = 2024

    print(f"🔍 Multi-Perspective Analysis: {ticker} ({year})")
    print("=" * 60)
    print("  Perspectives: Buffett (Value), Taleb (Antifragility), Contrarian")
    print("=" * 60)

    # Download and convert (similar to basic_analysis.py)
    print(f"\n📥 Downloading 10-K filing for {ticker}...")
    downloader = SECDownloader(
        company_name="Fintel Example",
        user_email="user@example.com"
    )
    filing_path = downloader.download(ticker, num_filings=1)

    print("\n📄 Converting to PDF...")
    with SECConverter() as converter:
        pdf_paths = converter.convert_batch(ticker, filing_path)

    if not pdf_paths:
        print("✗ No PDFs available. Exiting.")
        return

    pdf_path = pdf_paths[0]

    # Perform multi-perspective analysis
    print("\n🤖 Analyzing through 3 perspectives...")

    key_mgr = APIKeyManager(config.google_api_keys)
    rate_limiter = RateLimiter(sleep_after_request=config.sleep_after_request)

    analyzer = PerspectiveAnalyzer(
        api_key_manager=key_mgr,
        rate_limiter=rate_limiter
    )

    result = analyzer.analyze_multi_perspective(
        pdf_path=pdf_path,
        ticker=ticker,
        year=year,
        output_dir=config.data_dir / "perspectives" / ticker
    )

    if not result:
        print("✗ Analysis failed")
        return

    # Display results
    print("\n" + "=" * 60)
    print(f"📊 Multi-Perspective Analysis for {ticker}")
    print("=" * 60)

    print("\n🔵 Buffett (Value Investing) Perspective:")
    print(f"  Verdict: {result.buffett.buffett_verdict}")
    print(f"  Economic Moat: {result.buffett.economic_moat_score}/10")
    print(f"  ROIC Quality: {result.buffett.roic_quality_score}/10")
    print(f"  Pricing Power: {result.buffett.pricing_power_score}/10")
    print(f"  Key Insight: {result.buffett.key_insights[0] if result.buffett.key_insights else 'N/A'}")

    print("\n🟠 Taleb (Antifragility) Perspective:")
    print(f"  Verdict: {result.taleb.taleb_verdict}")
    print(f"  Fragility Assessment: {result.taleb.fragility_assessment}")
    print(f"  Optionality: {result.taleb.optionality}")
    print(f"  Key Insight: {result.taleb.key_insights[0] if result.taleb.key_insights else 'N/A'}")

    print("\n🟢 Contrarian Perspective:")
    print(f"  Verdict: {result.contrarian.contrarian_verdict}")
    print(f"  Consensus View: {result.contrarian.market_consensus}")
    print(f"  Alternative Thesis: {result.contrarian.alternative_thesis}")
    print(f"  Key Insight: {result.contrarian.key_insights[0] if result.contrarian.key_insights else 'N/A'}")

    print(f"\n🎯 Final Synthesized Verdict:")
    print(f"  {result.final_verdict}")

    print(f"\n✓ Complete! Results saved to: {config.data_dir}/perspectives/{ticker}")


if __name__ == "__main__":
    main()

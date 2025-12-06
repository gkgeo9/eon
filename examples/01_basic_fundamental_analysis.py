#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Example 1: Basic Fundamental Analysis

Download, convert to PDF, and analyze a single 10-K filing.
"""

import json
from pathlib import Path
from fintel.data.sources.sec import SECDownloader, SECConverter
from fintel.analysis.fundamental import FundamentalAnalyzer
from fintel.core import get_logger, get_config
from utils import init_components

# Setup
logger = get_logger(__name__)
config = get_config()

# Initialize AI components
api_key_manager, rate_limiter = init_components(sleep_seconds=0)

# Initialize analyzer
analyzer = FundamentalAnalyzer(
    api_key_manager=api_key_manager,
    rate_limiter=rate_limiter
)

# Example: Analyze Apple's latest 10-K
ticker = "AAPL"
year = 2023  # Use 2023 since 2024 may not be available yet

logger.info(f"Analyzing {ticker} {year} 10-K")

# Step 1: Download 10-K HTML from SEC Edgar
downloader = SECDownloader(
    company_name=config.sec_company_name,
    user_email=config.sec_user_email,
    base_path=Path("data/filings")
)
filing_dir = downloader.download(ticker=ticker, num_filings=1)

if not filing_dir:
    logger.error("Failed to download filing")
    exit(1)

logger.info(f"Downloaded to {filing_dir}")

# Step 2: Convert HTML to PDF
converter = SECConverter()
pdf_files = converter.convert(ticker=ticker, input_path=filing_dir, output_path=Path("data/pdfs"))

if not pdf_files:
    logger.error("Failed to convert HTML to PDF")
    exit(1)

pdf_info = pdf_files[0]  # Get the first (most recent) PDF
pdf_path = pdf_info['pdf_path']
logger.info(f"Converted to {pdf_path}")

# Step 3: Analyze with AI
result = analyzer.analyze_filing(
    pdf_path=pdf_path,
    ticker=ticker,
    year=year
)

if not result:
    logger.error("Analysis failed")
    exit(1)

# Step 4: Save results
output_dir = Path("output") / ticker
output_dir.mkdir(parents=True, exist_ok=True)
output_file = output_dir / f"{ticker}_{year}_analysis.json"

with open(output_file, 'w') as f:
    json.dump(result.model_dump(), f, indent=2)

logger.info(f"Saved analysis to {output_file}")

# Display key insights
print(f"\n{'='*80}")
print(f"FUNDAMENTAL ANALYSIS: {ticker} ({year})")
print(f"{'='*80}")
print(f"\nBusiness Model:\n{result.business_model[:500]}...")
print(f"\nRevenue Streams: {len(result.revenue_streams)}")
for stream in result.revenue_streams[:3]:
    print(f"  - {stream.source}: {stream.significance}")

print(f"\nCompetitive Advantages: {len(result.competitive_advantages)}")
for adv in result.competitive_advantages[:3]:
    print(f"  - {adv.advantage}")

print(f"\nKey Risks: {len(result.key_risks)}")
for risk in result.key_risks[:3]:
    print(f"  - {risk.risk_factor}")

print(f"\nSaved to: {output_file}")
print(f"{'='*80}\n")

# Clean up
converter.close()

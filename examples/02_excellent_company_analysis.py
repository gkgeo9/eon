#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Example 2: Excellent Company Analysis

Analyze a KNOWN SUCCESSFUL company to identify success factors.

This uses the SUCCESS-FOCUSED prompt that assumes the company was successful.
Use this for top performers, compounders, companies you want to learn from.
"""

from pathlib import Path
from fintel.analysis.fundamental.success_factors import ExcellentCompanyAnalyzer
from fintel.analysis.comparative.benchmarking import BenchmarkComparator
from fintel.ai import APIKeyManager, RateLimiter
from fintel.core import get_logger

# Setup
logger = get_logger(__name__)

# Initialize AI components
api_key_manager = APIKeyManager()
rate_limiter = RateLimiter(max_requests_per_minute=15)

# Initialize analyzers
excellent_analyzer = ExcellentCompanyAnalyzer(
    api_key_manager=api_key_manager,
    rate_limiter=rate_limiter
)

comparator = BenchmarkComparator(
    baseline_path=Path("top_50_meta_analysis.json"),
    api_key_manager=api_key_manager,
    rate_limiter=rate_limiter
)

# Example: Analyze Apple (known excellent company)
ticker = "AAPL"

logger.info(f"Analyzing success factors for {ticker} (excellent company)")

# Step 1: Analyze multi-year success factors
# Assumes you already have analyses in: analyzed_10k/AAPL/AAPL_YEAR_analysis.json
analyses_dir = Path("analyzed_10k") / ticker
output_dir = Path("excellent_company_factors")
output_dir.mkdir(parents=True, exist_ok=True)

success_factors = excellent_analyzer.analyze_from_directory(
    ticker=ticker,
    analyses_dir=analyses_dir,
    output_dir=output_dir
)

print(f"\n{'='*80}")
print(f"SUCCESS FACTORS: {ticker}")
print(f"{'='*80}")
print(f"\nUnique Attributes:")
for i, attr in enumerate(success_factors.unique_attributes, 1):
    print(f"{i}. {attr}")

print(f"\nKey Success Factors:")
for factor in success_factors.success_factors[:5]:
    print(f"\n  Factor: {factor.factor}")
    print(f"  Importance: {factor.importance}")

# Step 2: Compare against top 50 baseline
logger.info(f"Comparing {ticker} against top 50 baseline")

comparison_path = output_dir / f"{ticker}_comparison.json"
comparison = comparator.compare_against_baseline(
    success_factors=success_factors,
    output_file=comparison_path
)

# Print summary
comparator.print_summary(comparison)

logger.info(f"Analysis complete. Results saved to {output_dir}")
